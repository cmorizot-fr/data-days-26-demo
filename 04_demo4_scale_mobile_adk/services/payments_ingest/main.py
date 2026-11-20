"""Démo #4 · ingestion temps réel des paiements SEPA dans AlloyDB.

Pub/Sub (sepa-payments-alloydb-ops-sub, mode push + jeton OIDC) -> Cloud Run (ce service)
-> AlloyDB `hexagone.live_movements`.

- Authentification : le service Cloud Run est privé (--no-allow-unauthenticated). Seul le
  compte de service de push Pub/Sub a `roles/run.invoker` ; Cloud Run vérifie le jeton OIDC
  avant que la requête n'arrive ici.
- Base : AlloyDB Language Connector (mTLS) + authentification IAM, aucun mot de passe.
  L'utilisateur IAM n'a que SELECT/INSERT/UPDATE sur live_movements.
- Idempotence : clé primaire end_to_end_id. Un retry réseau (~3,4 % du flux) incrémente
  duplicate_count au lieu de créer une ligne.
- Message invalide : acquitté (204) et journalisé sans données personnelles, pour ne pas
  bloquer la souscription (qui n'a pas de DLQ). Erreur base : 500, Pub/Sub redélivre.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import asyncpg
from fastapi import FastAPI, Request, Response
from google.cloud.alloydbconnector import AsyncConnector, IPTypes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("payments_ingest")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Variable d'environnement manquante : {name}")
    return value


INSTANCE_URI = _required_env("ALLOYDB_INSTANCE_URI")
DB_NAME = os.environ.get("ALLOYDB_DB", "hexagone")
DB_IAM_USER = _required_env("ALLOYDB_IAM_USER")  # ex. hexagone-d4-ingest@data-days-demo.iam
IP_TYPE = IPTypes.PRIVATE if os.environ.get("ALLOYDB_IP_TYPE") == "PRIVATE" else IPTypes.PUBLIC
MAX_BODY_BYTES = 64 * 1024

ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")
BIC_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")
STATUSES = {"ACSC", "PDNG", "RJCT"}
SCHEME_RE = re.compile(r"^[A-Z_]{2,32}$")

UPSERT_SQL = """
INSERT INTO live_movements (
    end_to_end_id, event_id, customer_id, account_id, execution_ts, booking_date,
    payment_scheme, tx_status, status_reason_code, amount_eur, signed_amount_eur,
    counterparty_name, counterparty_bic, label, pubsub_message_id, publish_time)
VALUES ($1, $2, $3, $4, $5, ($5 AT TIME ZONE 'Europe/Paris')::date,
        $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
ON CONFLICT (end_to_end_id) DO UPDATE SET
    duplicate_count    = live_movements.duplicate_count + 1,
    tx_status          = CASE WHEN live_movements.tx_status = 'ACSC'
                              THEN 'ACSC' ELSE EXCLUDED.tx_status END,
    status_reason_code = CASE WHEN live_movements.tx_status = 'ACSC'
                              THEN live_movements.status_reason_code
                              ELSE EXCLUDED.status_reason_code END,
    updated_at         = now()
RETURNING (xmax = 0) AS inserted
"""


class InvalidMessage(ValueError):
    """Message Pub/Sub non conforme au contrat pacs.008 attendu."""


def _text(value: Any, field: str, *, pattern: re.Pattern[str] | None = None,
          max_len: int = 140, required: bool = True) -> str | None:
    if value is None or value == "":
        if required:
            raise InvalidMessage(f"champ manquant : {field}")
        return None
    if not isinstance(value, str) or len(value) > max_len:
        raise InvalidMessage(f"champ invalide : {field}")
    if pattern is not None and not pattern.fullmatch(value):
        raise InvalidMessage(f"format invalide : {field}")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidMessage(f"date invalide : {field}") from exc
    if ts.tzinfo is None:
        raise InvalidMessage(f"fuseau manquant : {field}")
    return ts


def parse_payment(payload: dict[str, Any]) -> tuple[Any, ...]:
    """Valide le message pacs.008 (STRUCT imbriqués) et retourne les paramètres SQL."""
    header = payload.get("header") or {}
    settlement = payload.get("settlement") or {}
    amount = payload.get("instructed_amount") or {}
    debtor = payload.get("debtor") or {}
    creditor = payload.get("creditor") or {}
    remittance = payload.get("remittance") or {}

    scheme = _text(settlement.get("payment_scheme"), "payment_scheme", pattern=SCHEME_RE)
    status = _text(settlement.get("tx_status"), "tx_status")
    if status not in STATUSES:
        raise InvalidMessage("tx_status hors liste")
    if amount.get("currency", "EUR") != "EUR":
        raise InvalidMessage("devise non EUR")
    try:
        amount_eur = Decimal(str(amount.get("amount_eur"))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidMessage("montant invalide") from exc
    if amount_eur < 0 or amount_eur > Decimal("1000000"):
        raise InvalidMessage("montant hors bornes")
    # Même règle de signe que le modèle dbt stg_sepa_payments.
    signed = amount_eur if scheme.endswith("INBOUND") else -amount_eur

    return (
        _text(header.get("end_to_end_id"), "end_to_end_id", pattern=ID_RE),
        _text(header.get("event_id"), "event_id", pattern=ID_RE),
        _text(debtor.get("customer_id"), "customer_id", pattern=ID_RE),
        _text(debtor.get("account_id"), "account_id", pattern=ID_RE),
        _timestamp(header.get("execution_ts"), "execution_ts"),
        scheme,
        status,
        _text(settlement.get("status_reason_code"), "status_reason_code", max_len=16, required=False),
        amount_eur,
        signed,
        _text(creditor.get("name"), "creditor.name", required=False),
        _text(creditor.get("agent_bic"), "creditor.agent_bic", pattern=BIC_RE, required=False),
        _text(remittance.get("unstructured_info"), "remittance", required=False),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    connector = AsyncConnector(refresh_strategy="lazy")

    async def _connect(instance_connection_name: str, **_: Any) -> asyncpg.Connection:
        return await connector.connect(
            instance_connection_name, "asyncpg",
            user=DB_IAM_USER, db=DB_NAME, enable_iam_auth=True, ip_type=IP_TYPE,
        )

    app.state.pool = await asyncpg.create_pool(
        INSTANCE_URI, connect=_connect, min_size=1, max_size=5, command_timeout=5,
    )
    log.info("Pool AlloyDB prêt (%s, base %s)", IP_TYPE, DB_NAME)
    try:
        yield
    finally:
        await app.state.pool.close()
        await connector.close()


app = FastAPI(title="hexagone-d4-payments-ingest", docs_url=None, redoc_url=None,
              openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/pubsub/push", status_code=204)
async def pubsub_push(request: Request) -> Response:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        log.warning("Message ignoré : corps trop volumineux (%d octets)", len(body))
        return Response(status_code=204)
    try:
        envelope = json.loads(body)
        message = envelope["message"]
        payload = json.loads(base64.b64decode(message["data"], validate=True))
        message_id = _text(message.get("messageId") or message.get("message_id"),
                           "messageId", pattern=ID_RE)
        publish_raw = message.get("publishTime") or message.get("publish_time")
        publish_time = _timestamp(publish_raw, "publishTime") if publish_raw else None
        params = parse_payment(payload)
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        # Pas de contenu du message dans les logs (IBAN, noms) : seulement la raison.
        log.warning("Message ignoré : %s", type(exc).__name__ if not isinstance(exc, InvalidMessage) else exc)
        return Response(status_code=204)

    started = time.perf_counter()
    async with request.app.state.pool.acquire() as conn:
        inserted = await conn.fetchval(UPSERT_SQL, *params, message_id, publish_time)
    log.info("live_movements %s %s en %.1f ms", params[0],
             "insert" if inserted else "retry ignoré", (time.perf_counter() - started) * 1000)
    return Response(status_code=204)
