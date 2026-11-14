"""
Moulinette temps réel Cloud Pub/Sub — Flux Paiements ISO 20022 (pacs.008) & Ajouts d'IBAN.

Émet dans Cloud Pub/Sub (`data-days-demo`) des événements JSON structurés ISO 20022
100 % cohérents avec le référentiel partagé `shared_universe.py` (mêmes clients, IBAN,
agences, BIC néobanques et client témoin Lucas Martin `CUST00002026` / `ACC00002026`),
tout en reproduisant fidèlement le bruit technique RAW :
  - ~3,4 % de doublons de retry réseau sur `end_to_end_id`
  - ~8,1 % de statuts non compensés (`RJCT` / `PDNG`) à côté des `ACSC`
  - Concentration des fuites SEPA Instant vers néobanques chez les 18-32 ans

Exemples d'utilisation :
  # Pré-charger une rafale de 500 messages réalistes dans les files Pub/Sub :
  uv run python 00_data_generator/stream_payments_pubsub.py --burst 500

  # Lancer un flux continu temps réel pendant une démo (ex. 15 msg/s pendant 60s) :
  uv run python 00_data_generator/stream_payments_pubsub.py --rate 15 --duration 60

  # Émettre les événements temps réel Jour J du client témoin Lucas Martin (Démo #4) :
  uv run python 00_data_generator/stream_payments_pubsub.py --witness-live
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone

import google.auth
import numpy as np
import requests
from google.auth.transport.requests import AuthorizedSession

from shared_universe import (
    BANK_BIC,
    DEMO_SEED,
    NEOBANK_DESTINATIONS,
    WITNESS_ACC_ID,
    WITNESS_CUST_ID,
    build_or_load_universe,
)

DEFAULT_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "data-days-demo")
DEFAULT_REGION = os.getenv("GCP_REGION", "europe-west1")
TOPIC_PAYMENTS = "sepa-payments-pacs008-topic"
TOPIC_IBAN = "iban-beneficiary-events-topic"

MERCHANT_COUNTERPARTIES = [
    ("CARREFOUR CITY PARIS", "BNPAFRPPXXX", "CARD_CONTACTLESS", 850, 9500),
    ("MONOPRIX OPERA", "SOGEFRPPXXX", "CARD_CONTACTLESS", 1200, 11000),
    ("SNCF VOYAGES", "CMCIFRPPXXX", "CARD_ECOMMERCE", 2500, 14500),
    ("EDF ENERGIE", "AGRIFRPPXXX", "SEPA_SDD", 4500, 13000),
    ("STRMFLIX DIGITAL", "BOFAIE3XXXX", "SEPA_SDD", 1599, 1999),
    ("PHARMACIE CENTRALE", "CEPAFRPPXXX", "CARD_CONTACTLESS", 600, 4800),
]

REJECT_REASONS = [
    ("RJCT", "AM04", "InsufficientFunds"),
    ("RJCT", "AM02", "NotAllowedAmountLimitExceeded"),
    ("RJCT", "AC04", "ClosedAccountNumber"),
    ("PDNG", "AB05", "TimeoutCreditorAgentSettlementPending"),
]


def build_pacs008_payload(
    *,
    event_id: str,
    end_to_end_id: str,
    execution_ts: str,
    customer_id: str,
    debtor_account_id: str,
    debtor_iban: str,
    guichet_code_5: str,
    creditor_name: str,
    creditor_bic: str,
    creditor_iban: str,
    payment_scheme: str,
    tx_status: str,
    status_reason_code: str | None,
    amount_cents: int,
    retry_attempt: int,
    remittance_info: str,
) -> dict:
    """Construit un message JSON inspiré d'ISO 20022 pacs.008.001.08 / pain.002."""
    amount_eur = round(amount_cents / 100.0, 2)
    return {
        "schema_version": "iso20022.pacs.008.001.08",
        "event_id": event_id,
        "end_to_end_id": end_to_end_id,
        "execution_ts": execution_ts,
        "settlement_method": "CLRG_RT1_INST" if payment_scheme == "SCT_INST" else "CLRG_STEP2",
        "payment_scheme": payment_scheme,
        "tx_status": tx_status,
        "status_reason_code": status_reason_code,
        "retry_attempt": retry_attempt,
        "amount_cents": int(amount_cents),
        "amount_eur": f"{amount_eur:.2f}",
        "currency": "EUR",
        "debtor": {
            "customer_id": customer_id,
            "account_id": debtor_account_id,
            "iban": debtor_iban,
            "agent_bic": BANK_BIC,
            "branch_guichet": guichet_code_5,
        },
        "creditor": {
            "name": creditor_name,
            "iban": creditor_iban,
            "agent_bic": creditor_bic,
        },
        "remittance_info": remittance_info,
    }


def generate_live_event_batch(
    rng: np.random.Generator,
    universe: dict,
    batch_size: int,
    seq_start: int,
) -> tuple[list[dict], list[dict]]:
    """Génère un lot cohérent d'événements paiements (+ ajouts d'IBAN associés)."""
    accounts_df = universe["accounts"]
    customers_df = universe["customers"]

    # On pioche dans les 80 000 comptes courants (incluant les 650 comptes récents AWS !)
    cc_df = accounts_df.filter(accounts_df["account_type"] == "CC_CHQ")
    acc_ids = cc_df["account_id"].to_numpy()
    cust_ids = cc_df["customer_id"].to_numpy()
    ibans = cc_df["iban"].to_numpy()
    guichets = cc_df["guichet_code_5"].to_numpy()
    ages = customers_df["age"].to_numpy()

    young_indices = np.flatnonzero((ages >= 18) & (ages <= 32))
    all_indices = np.arange(len(acc_ids))

    payment_msgs: list[dict] = []
    iban_msgs: list[dict] = []

    now_dt = datetime.now(timezone.utc)
    seq = seq_start

    while len(payment_msgs) < batch_size:
        seq += 1
        u_type = float(rng.random())

        # 28 % des flux live illustrent les virements SEPA Instant vers néobanques (68 % jeunes 18-32)
        if u_type < 0.28:
            if float(rng.random()) < 0.68:
                idx = int(rng.choice(young_indices))
            else:
                idx = int(rng.choice(all_indices))

            neo_bic, neo_label = NEOBANK_DESTINATIONS[
                int(rng.choice(len(NEOBANK_DESTINATIONS), p=[0.38, 0.32, 0.14, 0.10, 0.06]))
            ]
            payment_scheme = "SCT_INST"
            creditor_name = f"TITULAIRE EXTERNE {neo_bic[:6]}"
            creditor_bic = neo_bic
            creditor_iban = f"LT6032500{idx + 1:011d}" if neo_bic.startswith("REVOLT") else f"DE8950010517{idx + 1:010d}"
            amount_cents = int(rng.integers(20_000, 185_000))
            remittance = neo_label

            # 1 fois sur 4, on émet aussi l'événement préalable d'ajout de bénéficiaire IBAN dans le topic dédié
            if float(rng.random()) < 0.25:
                iban_msgs.append({
                    "event_id": f"IBAN-{uuid.uuid4().hex[:16].upper()}",
                    "event_ts": now_dt.isoformat(),
                    "customer_id": str(cust_ids[idx]),
                    "account_id": str(acc_ids[idx]),
                    "beneficiary_iban": creditor_iban,
                    "beneficiary_bic": creditor_bic,
                    "beneficiary_label": f"Mon compte {neo_bic[:6]}",
                    "channel": "MOBILE_APP_IOS_ANDROID",
                    "sca_strong_auth_status": "VERIFIED_BIOMETRIC",
                })
        else:
            idx = int(rng.choice(all_indices))
            m_name, m_bic, scheme, min_c, max_c = MERCHANT_COUNTERPARTIES[
                int(rng.integers(0, len(MERCHANT_COUNTERPARTIES)))
            ]
            payment_scheme = scheme
            creditor_name = m_name
            creditor_bic = m_bic
            creditor_iban = f"FR763000400892{idx + 1:09d}44"
            amount_cents = int(rng.integers(min_c, max_c + 1))
            remittance = f"PAIEMENT {m_name}"

        # Statut : ~8,1 % RJCT / PDNG sur le flux brut
        u_status = float(rng.random())
        if u_status < 0.081:
            st_code, rsn_code, _ = REJECT_REASONS[int(rng.integers(0, len(REJECT_REASONS)))]
        else:
            st_code, rsn_code = "ACSC", None

        e2e_id = f"E2ELIVE{now_dt.strftime('%Y%m%d')}{seq:08d}"
        ts_iso = now_dt.isoformat()

        msg = build_pacs008_payload(
            event_id=f"EVT-{uuid.uuid4().hex[:18].upper()}",
            end_to_end_id=e2e_id,
            execution_ts=ts_iso,
            customer_id=str(cust_ids[idx]),
            debtor_account_id=str(acc_ids[idx]),
            debtor_iban=str(ibans[idx]),
            guichet_code_5=str(guichets[idx]),
            creditor_name=creditor_name,
            creditor_bic=creditor_bic,
            creditor_iban=creditor_iban,
            payment_scheme=payment_scheme,
            tx_status=st_code,
            status_reason_code=rsn_code,
            amount_cents=amount_cents,
            retry_attempt=0,
            remittance_info=remittance,
        )
        payment_msgs.append(msg)

        # Injection fidèle de ~3,4 % de doublons techniques (retry réseau sur le même end_to_end_id)
        if len(payment_msgs) < batch_size and float(rng.random()) < 0.0355:
            dup_msg = dict(msg)
            dup_msg["event_id"] = f"EVT-{uuid.uuid4().hex[:18].upper()}"
            dup_msg["retry_attempt"] = 1
            payment_msgs.append(dup_msg)

    return payment_msgs[:batch_size], iban_msgs


def build_witness_live_events(universe: dict) -> tuple[list[dict], list[dict]]:
    """Construit les événements temps réel Jour J de Lucas Martin (CUST00002026) pour la Démo #4."""
    acc_row = universe["accounts"].filter(universe["accounts"]["account_id"] == WITNESS_ACC_ID).row(0, named=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    p1 = build_pacs008_payload(
        event_id=f"EVT-WITNESS-{uuid.uuid4().hex[:10].upper()}",
        end_to_end_id="E2EWIT20261113STRMFLIX",
        execution_ts=now_iso,
        customer_id=WITNESS_CUST_ID,
        debtor_account_id=WITNESS_ACC_ID,
        debtor_iban=acc_row["iban"],
        guichet_code_5=acc_row["guichet_code_5"],
        creditor_name="STRMFLIX DIGITAL",
        creditor_bic="BOFAIE3XXXX",
        creditor_iban="IE29BOFI90001712345678",
        payment_scheme="SEPA_SDD",
        tx_status="ACSC",
        status_reason_code=None,
        amount_cents=1999,  # 19,99 € (+4 € vs 15,99 € habituel !)
        retry_attempt=0,
        remittance_info="PRLV SEPA STRMFLIX ABO MENSUEL",
    )

    p2 = build_pacs008_payload(
        event_id=f"EVT-WITNESS-{uuid.uuid4().hex[:10].upper()}",
        end_to_end_id="E2EWIT20261113CPAM42",
        execution_ts=now_iso,
        customer_id=WITNESS_CUST_ID,
        debtor_account_id=WITNESS_ACC_ID,
        debtor_iban=acc_row["iban"],
        guichet_code_5=acc_row["guichet_code_5"],
        creditor_name="LUCAS MARTIN",
        creditor_bic=BANK_BIC,
        creditor_iban=acc_row["iban"],
        payment_scheme="SCT_INST_INBOUND",
        tx_status="ACSC",
        status_reason_code=None,
        amount_cents=4200,  # +42,00 € remboursement santé !
        retry_attempt=0,
        remittance_info="VIR CPAM REMBOURSEMENT SANTE",
    )

    iban_evt = {
        "event_id": f"IBAN-WITNESS-{uuid.uuid4().hex[:10].upper()}",
        "event_ts": now_iso,
        "customer_id": WITNESS_CUST_ID,
        "account_id": WITNESS_ACC_ID,
        "beneficiary_iban": "LT60325000000002026",
        "beneficiary_bic": "REVOLT21XXX",
        "beneficiary_label": "Lucas Martin Revolut",
        "channel": "MOBILE_APP_ANDROID",
        "sca_strong_auth_status": "VERIFIED_BIOMETRIC",
    }
    return [p1, p2], [iban_evt]


def get_gcloud_access_token() -> str:
    """Récupère un jeton OAuth2 actif (ADC) sans bruit console."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/pubsub"])
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            if creds.token:
                return creds.token
        except Exception:
            pass

    for subcmd in (
        ["gcloud", "auth", "application-default", "print-access-token", "--quiet"],
        ["gcloud", "auth", "print-access-token", "--quiet"],
    ):
        res = subprocess.run(subcmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    raise RuntimeError("Impossible de récupérer un jeton d'accès GCP.")


def rest_publish_batch(
    session: requests.Session,
    token: str,
    project_id: str,
    region: str,
    topic_name: str,
    entries: list[dict],
) -> None:
    """Envoie jusqu'à 900 messages par requête HTTPS REST vers l'endpoint régional Pub/Sub."""
    if not entries:
        return
    url = f"https://{region}-pubsub.googleapis.com/v1/projects/{project_id}/topics/{topic_name}:publish"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
        "Content-Type": "application/json",
    }
    for i in range(0, len(entries), 500):
        chunk = entries[i : i + 500]
        resp = session.post(url, headers=headers, json={"messages": chunk}, timeout=20)
        resp.raise_for_status()


def publish_messages(
    session: requests.Session,
    token: str,
    project_id: str,
    region: str,
    payment_msgs: list[dict],
    iban_msgs: list[dict],
) -> dict[str, int]:
    """Publie en batch HTTPS REST vers les 2 topics Pub/Sub avec attributs de routage."""
    counts = {"ACSC": 0, "RJCT_PDNG": 0, "DUP_RETRY": 0, "IBAN_EVENTS": 0}
    pay_entries: list[dict] = []
    iban_entries: list[dict] = []

    for msg in payment_msgs:
        if msg["retry_attempt"] > 0:
            counts["DUP_RETRY"] += 1
        elif msg["tx_status"] == "ACSC":
            counts["ACSC"] += 1
        else:
            counts["RJCT_PDNG"] += 1

        raw_b64 = base64.b64encode(json.dumps(msg, ensure_ascii=False).encode("utf-8")).decode("ascii")
        pay_entries.append({
            "data": raw_b64,
            "attributes": {
                "tx_status": msg["tx_status"],
                "payment_scheme": msg["payment_scheme"],
                "creditor_bic": msg["creditor"]["agent_bic"],
                "is_retry": str(msg["retry_attempt"] > 0).lower(),
            },
        })

    for imsg in iban_msgs:
        counts["IBAN_EVENTS"] += 1
        raw_b64 = base64.b64encode(json.dumps(imsg, ensure_ascii=False).encode("utf-8")).decode("ascii")
        iban_entries.append({
            "data": raw_b64,
            "attributes": {
                "beneficiary_bic": imsg["beneficiary_bic"],
                "channel": imsg["channel"],
            },
        })

    rest_publish_batch(session, token, project_id, region, TOPIC_PAYMENTS, pay_entries)
    rest_publish_batch(session, token, project_id, region, TOPIC_IBAN, iban_entries)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Moulinette temps réel Cloud Pub/Sub pour le flux paiements ISO 20022."
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Projet GCP cible")
    parser.add_argument("--region", default=DEFAULT_REGION, help="Région Pub/Sub (défaut: europe-west1)")
    parser.add_argument(
        "--burst",
        type=int,
        default=0,
        help="Nombre de messages à envoyer immédiatement en une rafale (ex. --burst 500)",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=10,
        help="Cadence de messages/seconde en mode streaming continu (défaut: 10)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Durée en secondes du mode streaming continu (0 = infini jusqu'à Ctrl+C)",
    )
    parser.add_argument(
        "--witness-live",
        action="store_true",
        help="Émet les événements Jour J du client témoin Lucas Martin (CUST00002026)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Génère et affiche un exemple de message sans appeler Cloud Pub/Sub",
    )
    args = parser.parse_args()

    universe = build_or_load_universe()
    rng = np.random.default_rng(DEMO_SEED + int(time.time()) % 10_000)

    if args.dry_run:
        p_msgs, i_msgs = generate_live_event_batch(rng, universe, batch_size=3, seq_start=1)
        print(json.dumps({"sample_payment": p_msgs[0], "sample_iban": i_msgs[:1]}, indent=2, ensure_ascii=False))
        return

    token = get_gcloud_access_token()
    session = requests.Session()

    if args.witness_live:
        p_msgs, i_msgs = build_witness_live_events(universe)
        stats = publish_messages(session, token, args.project_id, args.region, p_msgs, i_msgs)
        print(
            f"[stream_payments_pubsub] Événements témoin Lucas Martin ({WITNESS_CUST_ID} / {WITNESS_ACC_ID}) "
            f"publiés sur {args.project_id} ({args.region}) : {stats}"
        )
        return

    if args.burst > 0:
        t0 = time.perf_counter()
        p_msgs, i_msgs = generate_live_event_batch(rng, universe, batch_size=args.burst, seq_start=1)
        stats = publish_messages(session, token, args.project_id, args.region, p_msgs, i_msgs)
        dt = time.perf_counter() - t0
        print(
            f"[stream_payments_pubsub] Rafale de {len(p_msgs)} paiements (+ {len(i_msgs)} ajouts IBAN) "
            f"publiée en {dt:.2f}s vers {args.project_id} ({args.region}) : {stats}"
        )
        return

    print(
        f"[stream_payments_pubsub] Streaming continu démarré vers {args.project_id}/{TOPIC_PAYMENTS} "
        f"({args.rate} msg/s en {args.region}, Ctrl+C pour arrêter)..."
    )
    start_time = time.monotonic()
    last_token_refresh = start_time
    seq = 10_000
    total_sent = 0
    try:
        while True:
            tick_start = time.monotonic()
            if (tick_start - last_token_refresh) > 1800:
                token = get_gcloud_access_token()
                last_token_refresh = tick_start

            p_msgs, i_msgs = generate_live_event_batch(rng, universe, batch_size=args.rate, seq_start=seq)
            seq += args.rate
            stats = publish_messages(session, token, args.project_id, args.region, p_msgs, i_msgs)
            total_sent += len(p_msgs)
            print(
                f"  -> total={total_sent:,} | ACSC={stats['ACSC']} | "
                f"RJCT/PDNG={stats['RJCT_PDNG']} | DUP_RETRY={stats['DUP_RETRY']} | IBAN={stats['IBAN_EVENTS']}"
            )

            if args.duration > 0 and (time.monotonic() - start_time) >= args.duration:
                break
            elapsed_tick = time.monotonic() - tick_start
            if elapsed_tick < 1.0:
                time.sleep(1.0 - elapsed_tick)
    except KeyboardInterrupt:
        print(f"\n[stream_payments_pubsub] Arrêt propre après {total_sent:,} événements publiés.")


if __name__ == "__main__":
    main()
