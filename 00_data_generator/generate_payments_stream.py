"""
Générateur déterministe vectorisé (seed=2026) du silo SI Paiements Temps Réel
(archive historique micro-batchs Pub/Sub ISO 20022 pacs.008 sur 18 mois).

Produit dans `00_data_generator/output/RAW/PAYMENTS/` (synchronisé vers `gs://.../RAW/PAYMENTS/`) :
  1. sepa_payment_events/part-*.parquet : exactement 6 200 000 événements RAW garantissant :
       - 100 % d'alignement sur `shared_universe.py` (clients, comptes, IBAN, témoin CUST00002026)
       - Exactement 210 800 doublons de retry sur `end_to_end_id` (3,4000 %)
       - Exactement 502 200 statuts non compensés `RJCT` / `PDNG` (8,1000 %)
       - Exactement 2 420 000 000,00 € de virements sortants `ACSC` dédoublonnés vers néobanques
         sur 90 jours, dont 68,00 % (1 645 600 000,00 €) chez les 18-32 ans entre le 1er et le 5 du mois.
  2. iban_beneficiary_events/part-00000.parquet : ajouts d'IBAN bénéficiaires (avec ~3,4 % doublons API).

Schéma : 100 % Nested STRUCT strictement identique aux tables BigQuery alimentées en temps réel
par Pub/Sub (`raw_sepa_payments_pubsub_stream`, `raw_iban_events_pubsub_stream`).

Cohérence historique ↔ temps réel : toutes les contreparties, IBAN externes, libellés et attributs
digitaux proviennent du contrat partagé `payments_contract.py`, également utilisé par
`stream_payments_pubsub.py`. Convention de sens : `debtor` = compte Banque Hexagone concerné,
`creditor` = contrepartie externe ; `settlement.payment_scheme = *_INBOUND` désigne un crédit reçu.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from payments_contract import (
    BANK_BIC,
    COUNTERPARTIES,
    COUNTERPARTY_WEIGHTS,
    IBAN_ENROLLMENT_SCHEMA_VERSION,
    NEOBANK_BICS,
    NEOBANK_LABELS,
    OUTBOUND_COUNTERPARTIES,
    OUTBOUND_WEIGHTS,
    PACS008_SCHEMA_VERSION,
    WITNESS_COUNTERPARTIES,
    beneficiary_custom_label,
    customer_channel,
    customer_device_ip,
    customer_sca_status,
    neobank_beneficiary_iban,
)
from customer_ledger import build_or_load_ledger
from shared_universe import (
    DEMO_SEED,
    HISTORY_START_DATE,
    NEOBANK_DESTINATIONS,
    QUARTER_START_DATE,
    SNAPSHOT_DATE,
    TOTAL_LEAK_90D_CENTS,
    WITNESS_ACC_ID,
    WITNESS_CUST_ID,
    WITNESS_CUST_IDX,
    YOUNG_1_TO_5_LEAK_90D_CENTS,
    build_or_load_universe,
)

TOTAL_RAW_EVENTS: int = 6_200_000
EXACT_DUP_RETRY_EVENTS: int = 210_800    # 3,4000 % de 6 200 000
EXACT_NON_SETTLED_EVENTS: int = 502_200  # 8,1000 % de 6 200 000 (341 000 RJCT + 161 200 PDNG)
EXACT_UNIQUE_ACSC_EVENTS: int = TOTAL_RAW_EVENTS - EXACT_DUP_RETRY_EVENTS - EXACT_NON_SETTLED_EVENTS  # 5 487 000

SELF_NAME_MARKER = "__SELF__"  # Résolu en nom du titulaire (virement vers son propre compte néobanque)

_CP_NAMES = np.array([c.name for c in COUNTERPARTIES], dtype="U40")
_CP_BICS = np.array([c.bic for c in COUNTERPARTIES], dtype="U12")
_CP_IBANS = np.array([c.iban for c in COUNTERPARTIES], dtype="U34")
_CP_SCHEMES = np.array([c.scheme for c in COUNTERPARTIES], dtype="U16")
_CP_LABELS = np.array([c.label for c in COUNTERPARTIES], dtype="U40")
_CP_LO = np.array([c.min_cents for c in COUNTERPARTIES], dtype=np.int64)
_CP_HI = np.array([c.max_cents for c in COUNTERPARTIES], dtype=np.int64)

_OUT_NAMES = np.array([c.name for c in OUTBOUND_COUNTERPARTIES], dtype="U40")
_OUT_BICS = np.array([c.bic for c in OUTBOUND_COUNTERPARTIES], dtype="U12")
_OUT_IBANS = np.array([c.iban for c in OUTBOUND_COUNTERPARTIES], dtype="U34")
_OUT_SCHEMES = np.array([c.scheme for c in OUTBOUND_COUNTERPARTIES], dtype="U16")
_OUT_LABELS = np.array([c.label for c in OUTBOUND_COUNTERPARTIES], dtype="U40")
_OUT_LO = np.array([c.min_cents for c in OUTBOUND_COUNTERPARTIES], dtype=np.int64)
_OUT_HI = np.array([c.max_cents for c in OUTBOUND_COUNTERPARTIES], dtype=np.int64)


def _uniform_between(rng: np.random.Generator, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Tirage entier uniforme vectorisé dans [lo, hi] (bornes par ligne)."""
    return lo + np.floor(rng.random(len(lo)) * (hi - lo + 1)).astype(np.int64)


def _neobank_ibans(acc_idx: np.ndarray, bics: np.ndarray) -> np.ndarray:
    return np.array(
        [neobank_beneficiary_iban(int(a), str(b)) for a, b in zip(acc_idx, bics)],
        dtype="U34",
    )


def build_witness_payment_rows(iban_witness: str, guichet_5: str) -> dict[str, np.ndarray]:
    """Événements paiements sur 18 mois de Lucas Martin (miroir exact du Mainframe CFONB : mêmes E2E, BIC, montants)."""
    rows: list[tuple[str, str, str, int]] = []  # (date, e2e, label, amount_cents)
    seq = 1
    months_18 = [(2025, m) for m in range(6, 13)] + [(2026, m) for m in range(1, 12)]
    for y, m in months_18:
        ym = f"{y:04d}-{m:02d}"
        if (y, m) < (2026, 11):
            ops = [
                (f"{ym}-01", f"E2EWIT{seq:07d}", "VIR SALAIRE TECHCORP SAS", 185_000),
                (f"{ym}-05", f"E2EWIT{seq+1:07d}", "PRLV LOYER FONCIERE PARIS", 72_000),
                (f"{ym}-08", f"E2EWIT{seq+2:07d}", "PRLV SEPA STRMFLIX ABO", 1_599),
                (f"{ym}-11", f"E2EWITCB{seq:06d}", "CB CARREFOUR CITY PARIS", 15_000),
                (f"{ym}-12", f"E2EWIT{seq+3:07d}", "PRLV EDF ENERGIE", 6_401),
                (f"{ym}-18", f"E2EWITCB{seq+1:06d}", "CB MONOPRIX OPERA PARIS", 22_000),
                (f"{ym}-24", f"E2EWITCB{seq+2:06d}", "CB FNAC SAINT LAZARE", 19_000),
                (f"{ym}-28", f"E2EWITCB{seq+3:06d}", "CB SNCF VOYAGES", 22_800),
            ]
            seq += 4
        else:
            ops = [
                ("2026-11-01", f"E2EWIT{seq:07d}", "VIR SALAIRE TECHCORP SAS", 185_000),
                ("2026-11-05", f"E2EWIT{seq+1:07d}", "PRLV LOYER FONCIERE PARIS", 72_000),
                ("2026-11-08", f"E2EWIT{seq+2:07d}", "PRLV SEPA STRMFLIX ABO", 1_999),
                ("2026-11-10", f"E2EWIT{seq+3:07d}", "VIR CPAM REMBOURSEMENT SANTE", 4_200),
                ("2026-11-11", f"E2EWITCB{seq:06d}", "CB CARREFOUR CITY PARIS", 15_000),
                ("2026-11-12", f"E2EWIT{seq+4:07d}", "PRLV EDF ENERGIE", 6_401),
            ]
            seq += 5
        rows.extend(ops)

    n = len(rows)
    cps = [WITNESS_COUNTERPARTIES[r[2]] for r in rows]
    return {
        "end_to_end_id": np.array([r[1] for r in rows], dtype="U28"),
        "date_iso": np.array([r[0] for r in rows], dtype="U10"),
        "sec_of_day": np.full(n, 32_400, dtype=np.int32),
        "acc_idx": np.full(n, WITNESS_CUST_IDX, dtype=np.int32),
        "customer_id": np.full(n, WITNESS_CUST_ID, dtype="U12"),
        "debtor_account_id": np.full(n, WITNESS_ACC_ID, dtype="U11"),
        "debtor_iban": np.full(n, iban_witness, dtype="U27"),
        "guichet_code_5": np.full(n, guichet_5, dtype="U5"),
        "creditor_bic": np.array([c.bic for c in cps], dtype="U12"),
        "creditor_name": np.array([c.name for c in cps], dtype="U40"),
        "creditor_iban": np.array([c.iban for c in cps], dtype="U34"),
        "payment_scheme": np.array([c.scheme for c in cps], dtype="U16"),
        "tx_status": np.full(n, "ACSC", dtype="U4"),
        "status_reason": np.full(n, "", dtype="U4"),
        "amount_cents": np.array([r[3] for r in rows], dtype=np.int64),
        "retry_attempt": np.zeros(n, dtype=np.int8),
        "remittance_info": np.array([r[2] for r in rows], dtype="U40"),
    }


def generate_iban_beneficiary_table(
    rng: np.random.Generator,
    leak_df: pl.DataFrame,
    accounts_df: pl.DataFrame,
    customers_df: pl.DataFrame,
) -> pl.DataFrame:
    """Enrôlements IBAN bénéficiaires (veille du 1er virement néobanque) en 100 % Nested STRUCT, ~3,4 % doublons API."""
    distinct_pairs = (
        leak_df.select(["customer_id", "account_id", "acc_idx", "cust_idx", "neobank_bic", "accounting_date"])
        .group_by(["customer_id", "account_id", "acc_idx", "cust_idx", "neobank_bic"])
        .agg(pl.col("accounting_date").min().alias("first_leak_date"))
        .join(accounts_df.select(["account_id", "iban", "guichet_code_5"]), on="account_id", how="left")
        .join(customers_df.select(["customer_id", "first_name", "last_name"]), on="customer_id", how="left")
        .sort(["cust_idx", "neobank_bic"])
    )

    n_unique = distinct_pairs.height
    acc_idx = distinct_pairs["acc_idx"].to_list()
    cust_idx = distinct_pairs["cust_idx"].to_list()
    bics = distinct_pairs["neobank_bic"].to_list()
    first_names = distinct_pairs["first_name"].to_list()
    event_ts = [
        f"{(date(int(d[:4]), int(d[4:6]), int(d[6:8])) - timedelta(days=1)).isoformat()} "
        f"{8 + (a * 7) % 13:02d}:{(a * 11) % 60:02d}:{(a * 17) % 60:02d}"
        for d, a in zip(distinct_pairs["first_leak_date"].to_list(), acc_idx)
    ]

    base_df = pl.DataFrame({
        "event_id": [f"IBANEVT{i:08d}" for i in range(1, n_unique + 1)],
        "event_ts": event_ts,
        "retry_attempt": [0] * n_unique,
        "customer_id": distinct_pairs["customer_id"],
        "account_id": distinct_pairs["account_id"],
        "full_name": (distinct_pairs["first_name"] + " " + distinct_pairs["last_name"]),
        "debtor_iban": distinct_pairs["iban"],
        "branch_guichet": distinct_pairs["guichet_code_5"],
        "beneficiary_iban": [neobank_beneficiary_iban(int(a), b) for a, b in zip(acc_idx, bics)],
        "beneficiary_bic": bics,
        "custom_label": [beneficiary_custom_label(f, b) for f, b in zip(first_names, bics)],
        "channel": [customer_channel(int(c)) for c in cust_idx],
        "sca_strong_auth_status": [customer_sca_status(int(c)) for c in cust_idx],
        "device_ip": [customer_device_ip(int(c)) for c in cust_idx],
    })

    # ~3,4 % de doublons techniques d'API mobile (même enrôlement réémis 4 s plus tard)
    n_dups = int(round(n_unique * 0.0352))
    dup_idx = np.sort(rng.choice(n_unique, size=n_dups, replace=False))
    dup_df = (
        base_df.with_row_index("_row")
        .filter(pl.col("_row").is_in(dup_idx.tolist()))
        .drop("_row")
        .with_columns([
            (pl.col("event_id") + "_RETRY").alias("event_id"),
            pl.lit(1, dtype=pl.Int64).alias("retry_attempt"),
        ])
    )

    flat = pl.concat([base_df, dup_df]).with_columns(
        pl.col("event_ts").str.strptime(pl.Datetime("us"), "%Y-%m-%d %H:%M:%S").dt.replace_time_zone("UTC")
    )
    return flat.select([
        pl.struct([
            pl.lit(IBAN_ENROLLMENT_SCHEMA_VERSION).alias("schema_version"),
            pl.col("event_id"),
            pl.col("event_ts"),
            pl.col("retry_attempt").cast(pl.Int64),
        ]).alias("header"),
        pl.struct([
            pl.col("customer_id"),
            pl.col("account_id"),
            pl.col("full_name"),
            pl.col("debtor_iban"),
            pl.col("branch_guichet"),
        ]).alias("account_holder"),
        pl.struct([
            pl.col("beneficiary_iban").alias("iban"),
            pl.col("beneficiary_bic").alias("agent_bic"),
            pl.col("custom_label"),
        ]).alias("beneficiary"),
        pl.struct([
            pl.col("channel"),
            pl.col("sca_strong_auth_status"),
            pl.col("device_ip"),
        ]).alias("security_context"),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère les 6,2 M d'événements du flux paiements ISO 20022 (seed=2026)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output" / "RAW" / "PAYMENTS",
        help="Répertoire de sortie local avant synchronisation vers GCS RAW/PAYMENTS",
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    universe = build_or_load_universe()
    rng = np.random.default_rng(DEMO_SEED + 303)

    accounts_df = universe["accounts"]
    customers_df = universe["customers"]
    leak_90d_df = universe["leak_events_90d"]

    out_dir: Path = args.output_dir
    events_dir = out_dir / "sepa_payment_events"
    iban_dir = out_dir / "iban_beneficiary_events"
    events_dir.mkdir(parents=True, exist_ok=True)
    iban_dir.mkdir(parents=True, exist_ok=True)

    print(f"[generate_payments_stream] Construction vectorisée de {TOTAL_RAW_EVENTS:,} événements ISO 20022...")

    acc_ids_arr = accounts_df["account_id"].to_numpy()
    cust_ids_arr = accounts_df["customer_id"].to_numpy()
    ibans_arr = accounts_df["iban"].to_numpy()
    guichets_arr = accounts_df["guichet_code_5"].to_numpy()
    open_dates_arr = accounts_df["opening_date"].to_numpy()

    ord_start = HISTORY_START_DATE.toordinal()
    ord_end = SNAPSHOT_DATE.toordinal()
    date_iso_lookup = np.array(
        [(HISTORY_START_DATE + timedelta(days=i)).isoformat() for i in range(ord_end - ord_start + 5)],
        dtype="U10",
    )
    acc_min_ord = np.array(
        [max(ord_start, date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal()) for d in open_dates_arr],
        dtype=np.int32,
    )

    # 1. Témoin Lucas Martin (140 événements ACSC, miroir exact du Mainframe)
    w_blocks = build_witness_payment_rows(
        str(ibans_arr[WITNESS_CUST_IDX - 1]),
        str(guichets_arr[WITNESS_CUST_IDX - 1]),
    )
    n_witness = len(w_blocks["end_to_end_id"])

    # 2. Les 200 000 virements de fuite SEPA Instant 90j (ACSC -> exactement 2 420 000 000,00 €)
    n_leak_90d = leak_90d_df.height
    leak_acc_idx = leak_90d_df["acc_idx"].to_numpy().astype(np.int32)
    leak_bics = leak_90d_df["neobank_bic"].to_numpy().astype("U12")
    leak_dates_iso = np.array(
        [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in leak_90d_df["accounting_date"].to_numpy()],
        dtype="U10",
    )
    leak_blocks = {
        "end_to_end_id": leak_90d_df["end_to_end_id"].to_numpy().astype("U28"),
        "date_iso": leak_dates_iso,
        "sec_of_day": rng.integers(25_200, 79_200, size=n_leak_90d, dtype=np.int32),
        "acc_idx": leak_acc_idx,
        "customer_id": leak_90d_df["customer_id"].to_numpy().astype("U12"),
        "debtor_account_id": leak_90d_df["account_id"].to_numpy().astype("U11"),
        "debtor_iban": ibans_arr[leak_acc_idx - 1].astype("U27"),
        "guichet_code_5": leak_90d_df["guichet_code_5"].to_numpy().astype("U5"),
        "creditor_bic": leak_bics,
        "creditor_name": np.full(n_leak_90d, SELF_NAME_MARKER, dtype="U40"),
        "creditor_iban": _neobank_ibans(leak_acc_idx, leak_bics),
        "payment_scheme": np.full(n_leak_90d, "SCT_INST", dtype="U16"),
        "tx_status": np.full(n_leak_90d, "ACSC", dtype="U4"),
        "status_reason": np.full(n_leak_90d, "", dtype="U4"),
        "amount_cents": leak_90d_df["amount_cents"].to_numpy().astype(np.int64),
        "retry_attempt": np.zeros(n_leak_90d, dtype=np.int8),
        "remittance_info": leak_90d_df["libelle"].to_numpy().astype("U40"),
    }

    # 3-4. Journal partagé `customer_ledger.py` : fuites néobanques historiques + vie courante réglée ACSC
    #      (salaires, prélèvements, santé, carte, dont les 650 comptes récents AWS). Mêmes opérations que le
    #      Mainframe CFONB pour tous les comptes présents dans le batch J-1.
    ledger = build_or_load_ledger().filter(pl.col("in_sepa"))
    cc_pool_zero = np.array([i for i in range(80_000) if (i + 1) != WITNESS_CUST_IDX], dtype=np.int32)

    def _ledger_blocks(part: pl.DataFrame) -> dict[str, np.ndarray]:
        zero = part["acc_idx"].to_numpy().astype(np.int32) - 1
        n = part.height
        return {
            "end_to_end_id": part["e2e_id"].to_numpy().astype("U28"),
            "date_iso": np.array([f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in part["op_date"].to_list()], dtype="U10"),
            "sec_of_day": part["sec_of_day"].to_numpy().astype(np.int32),
            "acc_idx": (zero + 1).astype(np.int32),
            "customer_id": cust_ids_arr[zero].astype("U12"),
            "debtor_account_id": acc_ids_arr[zero].astype("U11"),
            "debtor_iban": ibans_arr[zero].astype("U27"),
            "guichet_code_5": guichets_arr[zero].astype("U5"),
            "creditor_bic": part["creditor_bic"].to_numpy().astype("U12"),
            "creditor_name": part["creditor_name"].to_numpy().astype("U40"),
            "creditor_iban": part["creditor_iban"].to_numpy().astype("U34"),
            "payment_scheme": part["payment_scheme"].to_numpy().astype("U16"),
            "tx_status": np.full(n, "ACSC", dtype="U4"),
            "status_reason": np.full(n, "", dtype="U4"),
            "amount_cents": part["amount_cents"].to_numpy().astype(np.int64),
            "retry_attempt": np.zeros(n, dtype=np.int8),
            "remittance_info": part["label"].to_numpy().astype("U40"),
        }

    leak_hist_blocks = _ledger_blocks(ledger.filter(pl.col("family") == "LEAK_HIST"))
    n_leak_hist = len(leak_hist_blocks["end_to_end_id"])
    reg_blocks = _ledger_blocks(ledger.filter(pl.col("family") != "LEAK_HIST"))
    n_regular_acsc = len(reg_blocks["end_to_end_id"])
    assert n_witness + n_leak_90d + n_leak_hist + n_regular_acsc == EXACT_UNIQUE_ACSC_EVENTS
    neo_bic_arr = np.array(NEOBANK_BICS, dtype="U12")
    neo_lbl_arr = np.array([NEOBANK_LABELS[b] for b in NEOBANK_BICS], dtype="U40")

    # 5. Les 502 200 événements non compensés RJCT / PDNG (exactement 8,1000 % du total RAW)
    #    Dont 18 000 tentatives vers des BIC néobanques sur les 90j (pour piéger toute requête sans filtre ACSC !)
    n_non_settled = EXACT_NON_SETTLED_EVENTS
    ns_zero = rng.choice(cc_pool_zero, size=n_non_settled, replace=True)
    ns_ords = rng.integers(acc_min_ord[ns_zero], ord_end + 1)

    is_neo_ns = np.zeros(n_non_settled, dtype=bool)
    is_neo_ns[:18_000] = True
    q_start_ord = QUARTER_START_DATE.toordinal()
    ns_ords[:18_000] = rng.integers(q_start_ord, ord_end + 1, size=18_000)

    ns_neo_choice = rng.integers(0, len(NEOBANK_DESTINATIONS), size=n_non_settled)
    ns_out_choice = rng.choice(len(OUTBOUND_COUNTERPARTIES), size=n_non_settled, p=OUTBOUND_WEIGHTS)

    n_rjct = 341_000
    ns_statuses = np.concatenate([
        np.full(n_rjct, "RJCT", dtype="U4"),
        np.full(n_non_settled - n_rjct, "PDNG", dtype="U4"),
    ])
    ns_reasons = np.concatenate([
        rng.choice(["AM04", "AM02", "AC04"], size=n_rjct).astype("U4"),
        np.full(n_non_settled - n_rjct, "AB05", dtype="U4"),
    ])

    ns_bics = np.where(is_neo_ns, neo_bic_arr[ns_neo_choice], _OUT_BICS[ns_out_choice]).astype("U12")
    ns_creditor_iban = _OUT_IBANS[ns_out_choice].copy()
    neo_rows = np.flatnonzero(is_neo_ns)
    ns_creditor_iban[neo_rows] = _neobank_ibans(ns_zero[neo_rows] + 1, ns_bics[neo_rows])

    ns_blocks = {
        "end_to_end_id": np.char.add("E2ENS2026", np.char.zfill(np.arange(1, n_non_settled + 1).astype("U10"), 9)).astype("U28"),
        "date_iso": date_iso_lookup[ns_ords - ord_start],
        "sec_of_day": rng.integers(21_600, 82_800, size=n_non_settled, dtype=np.int32),
        "acc_idx": (ns_zero + 1).astype(np.int32),
        "customer_id": cust_ids_arr[ns_zero].astype("U12"),
        "debtor_account_id": acc_ids_arr[ns_zero].astype("U11"),
        "debtor_iban": ibans_arr[ns_zero].astype("U27"),
        "guichet_code_5": guichets_arr[ns_zero].astype("U5"),
        "creditor_bic": ns_bics,
        "creditor_name": np.where(is_neo_ns, SELF_NAME_MARKER, _OUT_NAMES[ns_out_choice]).astype("U40"),
        "creditor_iban": ns_creditor_iban,
        "payment_scheme": np.where(is_neo_ns, "SCT_INST", _OUT_SCHEMES[ns_out_choice]).astype("U16"),
        "tx_status": ns_statuses,
        "status_reason": ns_reasons,
        "amount_cents": np.where(
            is_neo_ns,
            rng.integers(50_000, 450_000, size=n_non_settled, dtype=np.int64),
            _uniform_between(rng, _OUT_LO[ns_out_choice], _OUT_HI[ns_out_choice]),
        ),
        "retry_attempt": np.zeros(n_non_settled, dtype=np.int8),
        "remittance_info": np.where(is_neo_ns, neo_lbl_arr[ns_neo_choice], _OUT_LABELS[ns_out_choice]).astype("U40"),
    }

    # Assemblage des 5 989 200 événements uniques avant injection des 210 800 retries doublons
    unique_cols = {}
    for key in w_blocks:
        unique_cols[key] = np.concatenate([
            w_blocks[key],
            leak_blocks[key],
            leak_hist_blocks[key],
            reg_blocks[key],
            ns_blocks[key],
        ])

    # 6. Injection exacte de 210 800 doublons techniques end_to_end_id (3,4000 % de 6 200 000)
    #    On clone 7 500 fuites 90j + 203 300 opérations courantes ACSC (hors témoin Lucas Martin)
    dup_leak_idx = np.arange(n_witness, n_witness + 7_500, dtype=np.int32)
    dup_reg_start = n_witness + n_leak_90d + n_leak_hist
    dup_reg_idx = np.arange(dup_reg_start, dup_reg_start + (EXACT_DUP_RETRY_EVENTS - 7_500), dtype=np.int32)
    dup_indices = np.concatenate([dup_leak_idx, dup_reg_idx])

    all_cols = {}
    for key, arr in unique_cols.items():
        dup_slice = arr[dup_indices].copy()
        if key == "sec_of_day":
            dup_slice = np.minimum(dup_slice + 4, 86_399)
        elif key == "retry_attempt":
            dup_slice = np.ones(EXACT_DUP_RETRY_EVENTS, dtype=np.int8)
        all_cols[key] = np.concatenate([arr, dup_slice])

    n_final = len(all_cols["end_to_end_id"])
    assert n_final == TOTAL_RAW_EVENTS, f"Attendu {TOTAL_RAW_EVENTS}, obtenu {n_final}"

    event_ids = np.char.add("PEVT", np.char.zfill(np.arange(1, n_final + 1).astype("U10"), 9))

    names_df = customers_df.select([
        "customer_id",
        (pl.col("first_name") + pl.lit(" ") + pl.col("last_name")).alias("full_name"),
    ])

    df = pl.DataFrame({
        "event_id": event_ids,
        "end_to_end_id": all_cols["end_to_end_id"],
        "execution_date": pl.Series(all_cols["date_iso"]).str.strptime(pl.Date, "%Y-%m-%d"),
        "sec_of_day": all_cols["sec_of_day"],
        "customer_id": all_cols["customer_id"],
        "debtor_account_id": all_cols["debtor_account_id"],
        "debtor_iban": all_cols["debtor_iban"],
        "guichet_code_5": all_cols["guichet_code_5"],
        "creditor_bic": all_cols["creditor_bic"],
        "creditor_name": all_cols["creditor_name"],
        "creditor_iban": all_cols["creditor_iban"],
        "payment_scheme": all_cols["payment_scheme"],
        "tx_status": all_cols["tx_status"],
        "status_reason": all_cols["status_reason"],
        "retry_attempt": all_cols["retry_attempt"],
        "amount_cents": all_cols["amount_cents"],
        "amount_eur": (pl.Series(all_cols["amount_cents"]).cast(pl.Float64) / 100.0).round(2),
        "currency": np.full(n_final, "EUR", dtype="U3"),
        "remittance_info": all_cols["remittance_info"],
    }).with_columns(
        (
            pl.col("execution_date").cast(pl.Datetime("us"))
            + pl.duration(seconds=pl.col("sec_of_day"))
        ).dt.replace_time_zone("UTC").alias("execution_ts")
    ).drop("sec_of_day").join(names_df, on="customer_id", how="left", maintain_order="left")

    # Vérification stricte des invariants RAW et SILVER (après dédoublonnage + filtre ACSC)
    dup_pct = round((df.height - df["end_to_end_id"].n_unique()) * 100.0 / df.height, 4)
    non_settled_pct = round(df.filter(pl.col("tx_status").is_in(["RJCT", "PDNG"])).height * 100.0 / df.height, 4)

    raw_naive_leak_cents = int(
        df.filter(
            (pl.col("execution_date") >= QUARTER_START_DATE)
            & (pl.col("creditor_bic").is_in(NEOBANK_BICS))
        )["amount_cents"].sum()
    )

    clean_leak_df = (
        df.filter(
            (pl.col("tx_status") == "ACSC")
            & (pl.col("execution_date") >= QUARTER_START_DATE)
            & (pl.col("execution_date") <= SNAPSHOT_DATE)
            & (pl.col("creditor_bic").is_in(NEOBANK_BICS))
        )
        .sort("execution_ts", descending=True)
        .unique(subset=["end_to_end_id"], keep="first")
        .join(customers_df.select(["customer_id", "age"]), on="customer_id", how="left")
    )

    clean_leak_cents = int(clean_leak_df["amount_cents"].sum())
    young_1_5_cents = int(
        clean_leak_df.filter(
            (pl.col("age").is_between(18, 32))
            & (pl.col("execution_date").dt.day().is_between(1, 5))
        )["amount_cents"].sum()
    )

    assert dup_pct == 3.4, f"Attendu 3.4% doublons, obtenu {dup_pct}%"
    assert non_settled_pct == 8.1, f"Attendu 8.1% RJCT/PDNG, obtenu {non_settled_pct}%"
    assert clean_leak_cents == TOTAL_LEAK_90D_CENTS, f"Fuite clean attendue {TOTAL_LEAK_90D_CENTS}, obtenu {clean_leak_cents}"
    assert young_1_5_cents == YOUNG_1_TO_5_LEAK_90D_CENTS, f"Fuite jeunes attendue {YOUNG_1_TO_5_LEAK_90D_CENTS}, obtenu {young_1_5_cents}"
    assert df["full_name"].null_count() == 0, "Nom titulaire manquant"

    # Projection finale en schéma 100 % Nested (STRUCT ISO 20022 identique aux BigQuery Subscriptions Pub/Sub)
    nested_events_df = (
        df.with_columns([
            pl.when(pl.col("payment_scheme").str.starts_with("SCT_INST"))
            .then(pl.lit("CLRG_RT1_INST"))
            .otherwise(pl.lit("CLRG_STEP2"))
            .alias("settlement_method"),
            pl.when(pl.col("status_reason") == "")
            .then(None)
            .otherwise(pl.col("status_reason"))
            .alias("status_reason_code"),
            pl.when(pl.col("creditor_name") == SELF_NAME_MARKER)
            .then(pl.col("full_name"))
            .otherwise(pl.col("creditor_name"))
            .alias("creditor_name_resolved"),
        ])
        .select([
            pl.struct([
                pl.lit(PACS008_SCHEMA_VERSION).alias("schema_version"),
                pl.col("event_id"),
                pl.col("end_to_end_id"),
                pl.col("execution_ts"),
            ]).alias("header"),
            pl.struct([
                pl.col("settlement_method"),
                pl.col("payment_scheme"),
                pl.col("tx_status"),
                pl.col("status_reason_code"),
                pl.col("retry_attempt").cast(pl.Int64),
            ]).alias("settlement"),
            pl.struct([
                pl.col("amount_cents"),
                pl.col("amount_eur").cast(pl.Decimal(15, 2)),
                pl.col("currency"),
            ]).alias("instructed_amount"),
            pl.struct([
                pl.col("customer_id"),
                pl.col("debtor_account_id").alias("account_id"),
                pl.col("full_name"),
                pl.col("debtor_iban").alias("iban"),
                pl.lit(BANK_BIC).alias("agent_bic"),
                pl.col("guichet_code_5").alias("branch_guichet"),
            ]).alias("debtor"),
            pl.struct([
                pl.col("creditor_name_resolved").alias("name"),
                pl.col("creditor_iban").alias("iban"),
                pl.col("creditor_bic").alias("agent_bic"),
            ]).alias("creditor"),
            pl.struct([
                pl.col("remittance_info").alias("unstructured_info"),
            ]).alias("remittance"),
        ])
    )

    # Écriture en 4 shards Parquet ZSTD pour lecture parallèle BigLake (purge préalable des anciens shards)
    for old in events_dir.glob("part-*.parquet"):
        old.unlink()
    shard_size = (nested_events_df.height + 3) // 4
    for idx_s in range(4):
        shard = nested_events_df.slice(idx_s * shard_size, shard_size)
        shard.write_parquet(events_dir / f"part-{idx_s:05d}.parquet", compression="zstd")

    iban_df = generate_iban_beneficiary_table(rng, leak_90d_df, accounts_df, customers_df)
    for old in iban_dir.glob("part-*.parquet"):
        old.unlink()
    iban_df.write_parquet(iban_dir / "part-00000.parquet", compression="zstd")

    sensitive_regex = r"(SANTE|CPAM|MUTUELLE|MEDICAL|ORDONNANCE|PHARMACIE|LOYER)"
    stats = {
        "seed": DEMO_SEED,
        "history_window": [HISTORY_START_DATE.isoformat(), SNAPSHOT_DATE.isoformat()],
        "total_raw_payment_events": df.height,
        "duplicate_end_to_end_id_events": EXACT_DUP_RETRY_EVENTS,
        "duplicate_end_to_end_id_pct": dup_pct,
        "non_settled_rjct_pdng_events": EXACT_NON_SETTLED_EVENTS,
        "non_settled_rjct_pdng_pct": non_settled_pct,
        "unique_settled_acsc_events": EXACT_UNIQUE_ACSC_EVENTS,
        "raw_unfiltered_90d_neobank_eur": round(raw_naive_leak_cents / 100.0, 2),
        "clean_dedup_acsc_90d_neobank_eur": round(clean_leak_cents / 100.0, 2),
        "young_18_32_day_1_5_share_pct": round(young_1_5_cents * 100.0 / clean_leak_cents, 2),
        "sensitive_freetext_share_pct": round(
            df.filter(pl.col("remittance_info").str.contains(sensitive_regex)).height * 100.0 / df.height, 2
        ),
        "iban_beneficiary_events": iban_df.height,
    }
    (out_dir / "_manifest_payments_silo.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print(f"[generate_payments_stream] Terminé en {elapsed:.2f}s -> {out_dir}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
