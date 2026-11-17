"""
Moulinette temps réel Cloud Pub/Sub — Flux Paiements ISO 20022 (pacs.008) & Ajouts d'IBAN.

Émet dans Cloud Pub/Sub (`data-days-demo`) des événements JSON 100 % Nested STRUCT,
strictement cohérents avec l'archive historique 18 mois (`generate_payments_stream.py`) :
les deux générateurs partagent le contrat `payments_contract.py` (mêmes contreparties,
mêmes BIC, mêmes IBAN externes de néobanques par client, mêmes libellés alignés sur le
Mainframe CFONB, mêmes attributs digitaux par client).

Continuité temporelle : l'historique s'arrête au snapshot du 12/11/2026 ; le flux temps réel
est horodaté à l'instant de l'émission (jour J et suivants), sans aucun chevauchement.

Bruit technique RAW reproduit :
  - ~3,4 % de doublons de retry réseau sur `end_to_end_id`
  - ~8,1 % de statuts non compensés (`RJCT` / `PDNG`) à côté des `ACSC`
  - Concentration des virements SEPA Instant vers néobanques chez les 18-32 ans

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

from payments_contract import (
    BANK_BIC,
    COUNTERPARTIES,
    COUNTERPARTY_WEIGHTS,
    IBAN_ENROLLMENT_SCHEMA_VERSION,
    NEOBANK_BICS,
    NEOBANK_LABELS,
    PACS008_SCHEMA_VERSION,
    REJECT_REASONS,
    WITNESS_COUNTERPARTIES,
    beneficiary_custom_label,
    customer_channel,
    customer_device_ip,
    customer_sca_status,
    neobank_beneficiary_iban,
    settlement_method_for,
)
from shared_universe import (
    DEMO_SEED,
    WITNESS_ACC_ID,
    WITNESS_CUST_ID,
    WITNESS_CUST_IDX,
    build_or_load_universe,
)

DEFAULT_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "data-days-demo")
DEFAULT_REGION = os.getenv("GCP_REGION", "europe-west1")
TOPIC_PAYMENTS = "sepa-payments-pacs008-topic"
TOPIC_IBAN = "iban-beneficiary-events-topic"


def build_pacs008_payload(
    *,
    event_id: str,
    end_to_end_id: str,
    execution_ts: str,
    customer_id: str,
    debtor_account_id: str,
    debtor_full_name: str,
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
    """Message JSON 100 % Nested (STRUCT BigQuery) ISO 20022 pacs.008.001.08.

    Convention identique à l'historique : `debtor` = compte Banque Hexagone concerné,
    `creditor` = contrepartie externe ; `*_INBOUND` = crédit reçu par le client.
    """
    amount_eur = round(amount_cents / 100.0, 2)
    return {
        "header": {
            "schema_version": PACS008_SCHEMA_VERSION,
            "event_id": event_id,
            "end_to_end_id": end_to_end_id,
            "execution_ts": execution_ts,
        },
        "settlement": {
            "settlement_method": settlement_method_for(payment_scheme),
            "payment_scheme": payment_scheme,
            "tx_status": tx_status,
            "status_reason_code": status_reason_code,
            "retry_attempt": int(retry_attempt),
        },
        "instructed_amount": {
            "amount_cents": int(amount_cents),
            "amount_eur": f"{amount_eur:.2f}",
            "currency": "EUR",
        },
        "debtor": {
            "customer_id": customer_id,
            "account_id": debtor_account_id,
            "full_name": debtor_full_name,
            "iban": debtor_iban,
            "agent_bic": BANK_BIC,
            "branch_guichet": guichet_code_5,
        },
        "creditor": {
            "name": creditor_name,
            "iban": creditor_iban,
            "agent_bic": creditor_bic,
        },
        "remittance": {
            "unstructured_info": remittance_info,
        },
    }


def build_iban_enrollment_payload(
    *,
    event_id: str,
    event_ts: str,
    retry_attempt: int,
    cust_idx: int,
    customer_id: str,
    account_id: str,
    first_name: str,
    full_name: str,
    debtor_iban: str,
    branch_guichet: str,
    beneficiary_iban: str,
    beneficiary_bic: str,
) -> dict:
    """Événement JSON 100 % Nested (STRUCT BigQuery) d'ajout de bénéficiaire IBAN (attributs digitaux partagés)."""
    return {
        "header": {
            "schema_version": IBAN_ENROLLMENT_SCHEMA_VERSION,
            "event_id": event_id,
            "event_ts": event_ts,
            "retry_attempt": int(retry_attempt),
        },
        "account_holder": {
            "customer_id": customer_id,
            "account_id": account_id,
            "full_name": full_name,
            "debtor_iban": debtor_iban,
            "branch_guichet": branch_guichet,
        },
        "beneficiary": {
            "iban": beneficiary_iban,
            "agent_bic": beneficiary_bic,
            "custom_label": beneficiary_custom_label(first_name, beneficiary_bic),
        },
        "security_context": {
            "channel": customer_channel(cust_idx),
            "sca_strong_auth_status": customer_sca_status(cust_idx),
            "device_ip": customer_device_ip(cust_idx),
        },
    }


def _enrolled_pairs(universe: dict) -> set[tuple[str, str]]:
    """Couples (client, BIC néobanque) déjà enrôlés dans l'historique (veille du 1er virement 90j)."""
    leak_df = universe["leak_events_90d"]
    return set(zip(leak_df["customer_id"].to_list(), leak_df["neobank_bic"].to_list()))


def generate_live_event_batch(
    rng: np.random.Generator,
    universe: dict,
    batch_size: int,
    seq_start: int,
    enrolled_pairs: set[tuple[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Génère un lot cohérent d'événements paiements (+ enrôlements IBAN des nouveaux bénéficiaires)."""
    accounts_df = universe["accounts"]
    customers_df = universe["customers"]
    enrolled = enrolled_pairs if enrolled_pairs is not None else _enrolled_pairs(universe)

    # Les 80 000 comptes courants (CC_CHQ) sont alignés 1:1 sur les clients (compte i <-> client i),
    # y compris les 650 comptes récents AWS ; le témoin est réservé aux événements --witness-live.
    cc_df = accounts_df.filter(accounts_df["account_type"] == "CC_CHQ")
    acc_ids = cc_df["account_id"].to_numpy()
    cust_ids = cc_df["customer_id"].to_numpy()
    ibans = cc_df["iban"].to_numpy()
    guichets = cc_df["guichet_code_5"].to_numpy()
    ages = customers_df["age"].to_numpy()
    first_names = customers_df["first_name"].to_numpy()
    last_names = customers_df["last_name"].to_numpy()

    not_witness = np.arange(len(acc_ids)) != (WITNESS_CUST_IDX - 1)
    young_indices = np.flatnonzero((ages >= 18) & (ages <= 32) & not_witness)
    all_indices = np.flatnonzero(not_witness)

    payment_msgs: list[dict] = []
    iban_msgs: list[dict] = []

    now_dt = datetime.now(timezone.utc)
    ts_iso = now_dt.isoformat()
    e2e_prefix = f"E2ELIVE{now_dt.strftime('%Y%m%d%H%M%S')}"
    seq = seq_start

    while len(payment_msgs) < batch_size:
        seq += 1
        u_type = float(rng.random())

        # 28 % des flux live illustrent les virements SEPA Instant vers néobanques (68 % jeunes 18-32)
        if u_type < 0.28:
            idx = int(rng.choice(young_indices)) if float(rng.random()) < 0.68 else int(rng.choice(all_indices))
            holder_name = f"{first_names[idx]} {last_names[idx]}"
            neo_bic = NEOBANK_BICS[int(rng.choice(len(NEOBANK_BICS), p=[0.38, 0.32, 0.14, 0.10, 0.06]))]
            payment_scheme = "SCT_INST"
            creditor_name = holder_name
            creditor_bic = neo_bic
            creditor_iban = neobank_beneficiary_iban(idx + 1, neo_bic)
            amount_cents = int(rng.integers(20_000, 185_000))
            remittance = NEOBANK_LABELS[neo_bic]

            # Nouveau bénéficiaire : l'enrôlement IBAN précède obligatoirement le 1er virement
            pair = (str(cust_ids[idx]), neo_bic)
            if pair not in enrolled:
                enrolled.add(pair)
                iban_evt = build_iban_enrollment_payload(
                    event_id=f"IBAN-{uuid.uuid4().hex[:16].upper()}",
                    event_ts=ts_iso,
                    retry_attempt=0,
                    cust_idx=idx + 1,
                    customer_id=str(cust_ids[idx]),
                    account_id=str(acc_ids[idx]),
                    first_name=str(first_names[idx]),
                    full_name=holder_name,
                    debtor_iban=str(ibans[idx]),
                    branch_guichet=str(guichets[idx]),
                    beneficiary_iban=creditor_iban,
                    beneficiary_bic=neo_bic,
                )
                iban_msgs.append(iban_evt)
                if float(rng.random()) < 0.035:
                    iban_msgs.append({
                        **iban_evt,
                        "header": {
                            **iban_evt["header"],
                            "event_id": f"IBAN-{uuid.uuid4().hex[:16].upper()}",
                            "retry_attempt": 1,
                        },
                    })
        else:
            idx = int(rng.choice(all_indices))
            holder_name = f"{first_names[idx]} {last_names[idx]}"
            cp = COUNTERPARTIES[int(rng.choice(len(COUNTERPARTIES), p=COUNTERPARTY_WEIGHTS))]
            payment_scheme = cp.scheme
            creditor_name = cp.name
            creditor_bic = cp.bic
            creditor_iban = cp.iban
            amount_cents = int(rng.integers(cp.min_cents, cp.max_cents + 1))
            remittance = cp.label

        # Statut : ~8,1 % RJCT / PDNG sur le flux brut (les crédits entrants restent compensés)
        if float(rng.random()) < 0.081 and not payment_scheme.endswith("_INBOUND"):
            st_code, rsn_code = REJECT_REASONS[int(rng.integers(0, len(REJECT_REASONS)))]
        else:
            st_code, rsn_code = "ACSC", None

        msg = build_pacs008_payload(
            event_id=f"EVT-{uuid.uuid4().hex[:18].upper()}",
            end_to_end_id=f"{e2e_prefix}{seq:06d}",
            execution_ts=ts_iso,
            customer_id=str(cust_ids[idx]),
            debtor_account_id=str(acc_ids[idx]),
            debtor_full_name=holder_name,
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
            payment_msgs.append({
                **msg,
                "header": {**msg["header"], "event_id": f"EVT-{uuid.uuid4().hex[:18].upper()}"},
                "settlement": {**msg["settlement"], "retry_attempt": 1},
            })

    return payment_msgs[:batch_size], iban_msgs


def build_witness_live_events(universe: dict) -> tuple[list[dict], list[dict]]:
    """Événements Jour J de Lucas Martin (CUST00002026), dans la continuité stricte de son historique.

    L'historique (jusqu'au 12/11) contient déjà le salaire du 01/11, la hausse STRMFLIX 15,99 € -> 19,99 €
    du 08/11, le remboursement CPAM +42,00 € du 10/11 et son bénéficiaire Revolut enrôlé le 02/09 :
    le flux temps réel n'émet donc que des opérations nouvelles du jour (aucune réémission, aucun ré-enrôlement).
    """
    acc_row = universe["accounts"].filter(universe["accounts"]["account_id"] == WITNESS_ACC_ID).row(0, named=True)
    now_dt = datetime.now(timezone.utc)
    stamp = now_dt.strftime("%Y%m%d")
    ops = [
        ("CB BOULANGERIE ARTISANALE", 680, "BOULANGERIE"),
        ("CB PHARMACIE CENTRALE", 1_240, "PHARMACIE"),
    ]
    payment_msgs = []
    for label, cents, tag in ops:
        cp = WITNESS_COUNTERPARTIES[label]
        payment_msgs.append(build_pacs008_payload(
            event_id=f"EVT-WITNESS-{uuid.uuid4().hex[:10].upper()}",
            end_to_end_id=f"E2EWITLIVE{stamp}{tag[:6]}",
            execution_ts=now_dt.isoformat(),
            customer_id=WITNESS_CUST_ID,
            debtor_account_id=WITNESS_ACC_ID,
            debtor_full_name="LUCAS MARTIN",
            debtor_iban=acc_row["iban"],
            guichet_code_5=acc_row["guichet_code_5"],
            creditor_name=cp.name,
            creditor_bic=cp.bic,
            creditor_iban=cp.iban,
            payment_scheme=cp.scheme,
            tx_status="ACSC",
            status_reason_code=None,
            amount_cents=cents,
            retry_attempt=0,
            remittance_info=cp.label,
        ))
    return payment_msgs, []


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
    """Envoie jusqu'à 500 messages par requête HTTPS REST vers l'endpoint régional Pub/Sub."""
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
        st = msg["settlement"]
        if st["retry_attempt"] > 0:
            counts["DUP_RETRY"] += 1
        elif st["tx_status"] == "ACSC":
            counts["ACSC"] += 1
        else:
            counts["RJCT_PDNG"] += 1

        raw_b64 = base64.b64encode(json.dumps(msg, ensure_ascii=False).encode("utf-8")).decode("ascii")
        pay_entries.append({
            "data": raw_b64,
            "attributes": {
                "tx_status": st["tx_status"],
                "payment_scheme": st["payment_scheme"],
                "creditor_bic": msg["creditor"]["agent_bic"],
                "is_retry": str(st["retry_attempt"] > 0).lower(),
            },
        })

    for imsg in iban_msgs:
        counts["IBAN_EVENTS"] += 1
        raw_b64 = base64.b64encode(json.dumps(imsg, ensure_ascii=False).encode("utf-8")).decode("ascii")
        iban_entries.append({
            "data": raw_b64,
            "attributes": {
                "beneficiary_bic": imsg["beneficiary"]["agent_bic"],
                "channel": imsg["security_context"]["channel"],
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
    enrolled = _enrolled_pairs(universe)

    if args.dry_run:
        p_msgs, i_msgs = generate_live_event_batch(rng, universe, batch_size=40, seq_start=1, enrolled_pairs=enrolled)
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
        p_msgs, i_msgs = generate_live_event_batch(
            rng, universe, batch_size=args.burst, seq_start=0, enrolled_pairs=enrolled
        )
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
    seq = 0
    total_sent = 0
    try:
        while True:
            tick_start = time.monotonic()
            if (tick_start - last_token_refresh) > 1800:
                token = get_gcloud_access_token()
                last_token_refresh = tick_start

            p_msgs, i_msgs = generate_live_event_batch(
                rng, universe, batch_size=args.rate, seq_start=seq, enrolled_pairs=enrolled
            )
            seq += args.rate * 2
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
