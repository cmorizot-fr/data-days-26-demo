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
"""

from __future__ import annotations

import argparse
import calendar
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from shared_universe import (
    BANK_BIC,
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


def build_witness_payment_rows(iban_witness: str, guichet_5: str) -> dict[str, np.ndarray]:
    """Construit les événements paiements sur 18 mois de Lucas Martin (CUST00002026 / ACC00002026)."""
    rows: list[tuple[str, str, str, str, int, str]] = []
    seq = 1
    months_18 = [(2025, m) for m in range(6, 13)] + [(2026, m) for m in range(1, 12)]
    for y, m in months_18:
        ym = f"{y:04d}-{m:02d}"
        if (y, m) < (2026, 11):
            ops = [
                (f"{ym}-01", f"E2EWIT{seq:07d}", "SCT_INBOUND", "EMPLOYEURFR", 185_000, "VIR SALAIRE TECHCORP SAS"),
                (f"{ym}-05", f"E2EWIT{seq+1:07d}", "SEPA_SDD", "MANDATLOYER", 72_000, "PRLV LOYER FONCIERE PARIS"),
                (f"{ym}-08", f"E2EWIT{seq+2:07d}", "SEPA_SDD", "STRMFLIXEUR", 1_599, "PRLV SEPA STRMFLIX ABO"),
                (f"{ym}-11", f"E2EWITCB{seq:06d}", "CARD_CONTACTLESS", "BNPAFRPPXXX", 15_000, "CB CARREFOUR CITY PARIS"),
                (f"{ym}-12", f"E2EWIT{seq+3:07d}", "SEPA_SDD", "EDFPROXIMIT", 6_401, "PRLV EDF ENERGIE"),
                (f"{ym}-18", f"E2EWITCB{seq+1:06d}", "CARD_CONTACTLESS", "SOGEFRPPXXX", 22_000, "CB MONOPRIX OPERA PARIS"),
                (f"{ym}-24", f"E2EWITCB{seq+2:06d}", "CARD_CONTACTLESS", "CMCIFRPPXXX", 19_000, "CB FNAC SAINT LAZARE"),
                (f"{ym}-28", f"E2EWITCB{seq+3:06d}", "CARD_ECOMMERCE", "CMCIFRPPXXX", 22_800, "CB SNCF VOYAGES"),
            ]
            seq += 4
        else:
            ops = [
                ("2026-11-01", f"E2EWIT{seq:07d}", "SCT_INBOUND", "EMPLOYEURFR", 185_000, "VIR SALAIRE TECHCORP SAS"),
                ("2026-11-05", f"E2EWIT{seq+1:07d}", "SEPA_SDD", "MANDATLOYER", 72_000, "PRLV LOYER FONCIERE PARIS"),
                ("2026-11-08", f"E2EWIT{seq+2:07d}", "SEPA_SDD", "STRMFLIXEUR", 1_999, "PRLV SEPA STRMFLIX ABO"),
                ("2026-11-10", f"E2EWIT{seq+3:07d}", "SCT_INBOUND", "CPAMIDF7500", 4_200, "VIR CPAM REMBOURSEMENT SANTE"),
                ("2026-11-11", f"E2EWITCB{seq:06d}", "CARD_CONTACTLESS", "BNPAFRPPXXX", 15_000, "CB CARREFOUR CITY PARIS"),
                ("2026-11-12", f"E2EWIT{seq+4:07d}", "SEPA_SDD", "EDFPROXIMIT", 6_401, "PRLV EDF ENERGIE"),
            ]
            seq += 5
        rows.extend(ops)

    n = len(rows)
    return {
        "end_to_end_id": np.array([r[1] for r in rows], dtype="U28"),
        "date_iso": np.array([r[0] for r in rows], dtype="U10"),
        "sec_of_day": np.full(n, 32_400, dtype=np.int32),
        "customer_id": np.full(n, WITNESS_CUST_ID, dtype="U12"),
        "debtor_account_id": np.full(n, WITNESS_ACC_ID, dtype="U11"),
        "debtor_iban": np.full(n, iban_witness, dtype="U27"),
        "guichet_code_5": np.full(n, guichet_5, dtype="U5"),
        "creditor_bic": np.array([r[3] for r in rows], dtype="U12"),
        "payment_scheme": np.array([r[2] for r in rows], dtype="U16"),
        "tx_status": np.full(n, "ACSC", dtype="U4"),
        "status_reason": np.full(n, "", dtype="U4"),
        "amount_cents": np.array([r[4] for r in rows], dtype=np.int64),
        "retry_attempt": np.zeros(n, dtype=np.int8),
        "remittance_info": np.array([r[5] for r in rows], dtype="U36"),
    }


def generate_iban_beneficiary_table(
    rng: np.random.Generator,
    leak_df: pl.DataFrame,
    accounts_df: pl.DataFrame,
) -> pl.DataFrame:
    """Génère la table des ajouts d'IBAN bénéficiaires (avec ~3,4 % de doublons d'appels API)."""
    acc_iban_map = accounts_df.select(["account_id", "iban", "guichet_code_5"])
    distinct_pairs = (
        leak_df.select(["customer_id", "account_id", "neobank_bic", "accounting_date"])
        .group_by(["customer_id", "account_id", "neobank_bic"])
        .agg(pl.col("accounting_date").min().alias("first_leak_date"))
        .join(acc_iban_map, on="account_id", how="left")
    )

    n_unique = distinct_pairs.height
    event_ids = [f"IBANEVT{i:08d}" for i in range(1, n_unique + 1)]
    dates_str = distinct_pairs["first_leak_date"].to_list()
    added_dates = [
        (date(int(d[:4]), int(d[4:6]), int(d[6:8])) - timedelta(days=1)).isoformat()
        for d in dates_str
    ]
    bics = distinct_pairs["neobank_bic"].to_list()
    ext_ibans = [
        f"LT6032500{i:011d}" if b.startswith("REVOLT") else f"DE8950010517{i:010d}"
        for i, b in enumerate(bics, start=1)
    ]

    base_df = distinct_pairs.with_columns([
        pl.Series("iban_event_id", event_ids),
        pl.Series("added_date", added_dates).str.strptime(pl.Date, "%Y-%m-%d"),
        pl.Series("beneficiary_iban", ext_ibans),
        pl.lit("MOBILE_APP").alias("channel"),
        pl.lit("VERIFIED_SCA").alias("auth_status"),
        pl.lit(0, dtype=pl.Int8).alias("retry_attempt"),
    ]).select([
        "iban_event_id",
        "added_date",
        "customer_id",
        "account_id",
        "guichet_code_5",
        "neobank_bic",
        "beneficiary_iban",
        "channel",
        "auth_status",
        "retry_attempt",
    ]).rename({"neobank_bic": "beneficiary_bic"})

    # ~3,4 % de doublons techniques d'API mobile
    n_dups = int(round(n_unique * 0.0352))
    dup_df = base_df.head(n_dups).with_columns([
        (pl.col("iban_event_id") + "_RETRY").alias("iban_event_id"),
        pl.lit(1, dtype=pl.Int8).alias("retry_attempt"),
    ])

    return pl.concat([base_df, dup_df])


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

    # 1. Witness Lucas Martin (140 événements ACSC)
    w_blocks = build_witness_payment_rows(
        str(ibans_arr[WITNESS_CUST_IDX - 1]),
        str(guichets_arr[WITNESS_CUST_IDX - 1]),
    )
    n_witness = len(w_blocks["end_to_end_id"])

    # 2. Les 200 000 virements de fuite SEPA Instant 90j (ACSC -> exactement 2 420 000 000,00 €)
    n_leak_90d = leak_90d_df.height
    leak_acc_zero = leak_90d_df["acc_idx"].to_numpy() - 1
    leak_raw_dates = leak_90d_df["accounting_date"].to_numpy()
    leak_dates_iso = np.array(
        [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in leak_raw_dates],
        dtype="U10",
    )
    leak_blocks = {
        "end_to_end_id": leak_90d_df["end_to_end_id"].to_numpy().astype("U28"),
        "date_iso": leak_dates_iso,
        "sec_of_day": rng.integers(25_200, 79_200, size=n_leak_90d, dtype=np.int32),
        "customer_id": leak_90d_df["customer_id"].to_numpy().astype("U12"),
        "debtor_account_id": leak_90d_df["account_id"].to_numpy().astype("U11"),
        "debtor_iban": ibans_arr[leak_acc_zero].astype("U27"),
        "guichet_code_5": leak_90d_df["guichet_code_5"].to_numpy().astype("U5"),
        "creditor_bic": leak_90d_df["neobank_bic"].to_numpy().astype("U12"),
        "payment_scheme": np.full(n_leak_90d, "SCT_INST", dtype="U16"),
        "tx_status": np.full(n_leak_90d, "ACSC", dtype="U4"),
        "status_reason": np.full(n, "", dtype="U4") if (n := n_leak_90d) else np.array([], dtype="U4"),
        "amount_cents": leak_90d_df["amount_cents"].to_numpy().astype(np.int64),
        "retry_attempt": np.zeros(n_leak_90d, dtype=np.int8),
        "remittance_info": leak_90d_df["libelle"].to_numpy().astype("U36"),
    }

    # 3. Fuites néobanques historiques avant le trimestre (< 2026-08-13) : 100 000 événements ACSC
    n_leak_hist = 100_000
    pre_cc_zero = np.array([i for i in range(62_000) if (i + 1) != WITNESS_CUST_IDX], dtype=np.int32)
    hist_chosen_zero = rng.choice(pre_cc_zero, size=n_leak_hist, replace=True)
    aug12_ord = date(2026, 8, 12).toordinal()
    hist_ords = rng.integers(ord_start, aug12_ord + 1, size=n_leak_hist)
    hist_neo_idx = rng.choice(len(NEOBANK_DESTINATIONS), size=n_leak_hist, p=[0.40, 0.30, 0.14, 0.10, 0.06])
    neo_bic_arr = np.array([b for b, _ in NEOBANK_DESTINATIONS], dtype="U12")
    neo_lbl_arr = np.array([lbl for _, lbl in NEOBANK_DESTINATIONS], dtype="U36")

    leak_hist_blocks = {
        "end_to_end_id": np.char.add("E2EHISTLEAK", np.char.zfill(np.arange(1, n_leak_hist + 1).astype("U10"), 8)).astype("U28"),
        "date_iso": date_iso_lookup[hist_ords - ord_start],
        "sec_of_day": rng.integers(25_200, 79_200, size=n_leak_hist, dtype=np.int32),
        "customer_id": cust_ids_arr[hist_chosen_zero].astype("U12"),
        "debtor_account_id": acc_ids_arr[hist_chosen_zero].astype("U11"),
        "debtor_iban": ibans_arr[hist_chosen_zero].astype("U27"),
        "guichet_code_5": guichets_arr[hist_chosen_zero].astype("U5"),
        "creditor_bic": neo_bic_arr[hist_neo_idx],
        "payment_scheme": np.full(n_leak_hist, "SCT_INST", dtype="U16"),
        "tx_status": np.full(n_leak_hist, "ACSC", dtype="U4"),
        "status_reason": np.full(n_leak_hist, "", dtype="U4"),
        "amount_cents": rng.integers(15_000, 380_000, size=n_leak_hist, dtype=np.int64),
        "retry_attempt": np.zeros(n_leak_hist, dtype=np.int8),
        "remittance_info": neo_lbl_arr[hist_neo_idx],
    }

    # 4. Opérations courantes compensées ACSC (incluant des flux sur les 650 comptes récents AWS !)
    n_regular_acsc = EXACT_UNIQUE_ACSC_EVENTS - (n_witness + n_leak_90d + n_leak_hist)
    cc_pool_zero = np.array([i for i in range(80_000) if (i + 1) != WITNESS_CUST_IDX], dtype=np.int32)
    reg_zero = rng.choice(cc_pool_zero, size=n_regular_acsc, replace=True)
    # Garantir que chacun des 650 comptes orphelins AWS (79350..79999) a au moins 2 opérations SEPA/CB
    reg_zero[:1300] = np.tile(np.arange(79_350, 80_000, dtype=np.int32), 2)

    reg_min_ords = acc_min_ord[reg_zero]
    reg_ords = rng.integers(reg_min_ords, ord_end + 1)

    merchant_bics = np.array(["BNPAFRPPXXX", "SOGEFRPPXXX", "CMCIFRPPXXX", "AGRIFRPPXXX", "CEPAFRPPXXX", "EMPLOYEURFR"], dtype="U12")
    merchant_schemes = np.array(["CARD_CONTACTLESS", "CARD_ECOMMERCE", "SEPA_SDD", "SCT_OUTBOUND", "CARD_CONTACTLESS", "SCT_INBOUND"], dtype="U16")
    merchant_labels = np.array([
        "PAIEMENT CB COMMERCE PROXIMITE",
        "PAIEMENT CB ECOMMERCE",
        "PRLV SEPA FACTURE ENERGIE TELECOM",
        "VIR SEPA EXTERNE",
        "PAIEMENT CB SUPERMARCHE",
        "VIR SEPA SALAIRE ENTREPRISE",
    ], dtype="U36")
    m_choice = rng.integers(0, len(merchant_bics), size=n_regular_acsc)

    reg_blocks = {
        "end_to_end_id": np.char.add("E2EREG2026", np.char.zfill(np.arange(1, n_regular_acsc + 1).astype("U10"), 9)).astype("U28"),
        "date_iso": date_iso_lookup[reg_ords - ord_start],
        "sec_of_day": rng.integers(21_600, 82_800, size=n_regular_acsc, dtype=np.int32),
        "customer_id": cust_ids_arr[reg_zero].astype("U12"),
        "debtor_account_id": acc_ids_arr[reg_zero].astype("U11"),
        "debtor_iban": ibans_arr[reg_zero].astype("U27"),
        "guichet_code_5": guichets_arr[reg_zero].astype("U5"),
        "creditor_bic": merchant_bics[m_choice],
        "payment_scheme": merchant_schemes[m_choice],
        "tx_status": np.full(n_regular_acsc, "ACSC", dtype="U4"),
        "status_reason": np.full(n_regular_acsc, "", dtype="U4"),
        "amount_cents": rng.integers(650, 240_000, size=n_regular_acsc, dtype=np.int64),
        "retry_attempt": np.zeros(n_regular_acsc, dtype=np.int8),
        "remittance_info": merchant_labels[m_choice],
    }

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
    ns_mer_choice = rng.integers(0, len(merchant_bics), size=n_non_settled)

    n_rjct = 341_000
    ns_statuses = np.concatenate([
        np.full(n_rjct, "RJCT", dtype="U4"),
        np.full(n_non_settled - n_rjct, "PDNG", dtype="U4"),
    ])
    ns_reasons = np.concatenate([
        rng.choice(["AM04", "AM02", "AC04"], size=n_rjct).astype("U4"),
        np.full(n_non_settled - n_rjct, "AB05", dtype="U4"),
    ])

    ns_blocks = {
        "end_to_end_id": np.char.add("E2ENS2026", np.char.zfill(np.arange(1, n_non_settled + 1).astype("U10"), 9)).astype("U28"),
        "date_iso": date_iso_lookup[ns_ords - ord_start],
        "sec_of_day": rng.integers(21_600, 82_800, size=n_non_settled, dtype=np.int32),
        "customer_id": cust_ids_arr[ns_zero].astype("U12"),
        "debtor_account_id": acc_ids_arr[ns_zero].astype("U11"),
        "debtor_iban": ibans_arr[ns_zero].astype("U27"),
        "guichet_code_5": guichets_arr[ns_zero].astype("U5"),
        "creditor_bic": np.where(is_neo_ns, neo_bic_arr[ns_neo_choice], merchant_bics[ns_mer_choice]),
        "payment_scheme": np.where(is_neo_ns, "SCT_INST", merchant_schemes[ns_mer_choice]).astype("U16"),
        "tx_status": ns_statuses,
        "status_reason": ns_reasons,
        "amount_cents": np.where(
            is_neo_ns,
            rng.integers(50_000, 450_000, size=n_non_settled, dtype=np.int64),
            rng.integers(1_200, 120_000, size=n_non_settled, dtype=np.int64),
        ),
        "retry_attempt": np.zeros(n_non_settled, dtype=np.int8),
        "remittance_info": np.where(is_neo_ns, neo_lbl_arr[ns_neo_choice], merchant_labels[ns_mer_choice]),
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
        ).alias("execution_ts")
    ).drop("sec_of_day")

    # Vérification stricte des invariants RAW et SILVER (après dédoublonnage + filtre ACSC)
    dup_pct = round((df.height - df["end_to_end_id"].n_unique()) * 100.0 / df.height, 4)
    non_settled_pct = round(df.filter(pl.col("tx_status").is_in(["RJCT", "PDNG"])).height * 100.0 / df.height, 4)

    neo_bics_list = [b for b, _ in NEOBANK_DESTINATIONS]
    raw_naive_leak_cents = int(
        df.filter(
            (pl.col("execution_date") >= QUARTER_START_DATE)
            & (pl.col("creditor_bic").is_in(neo_bics_list))
        )["amount_cents"].sum()
    )

    clean_leak_df = (
        df.filter(
            (pl.col("tx_status") == "ACSC")
            & (pl.col("execution_date") >= QUARTER_START_DATE)
            & (pl.col("creditor_bic").is_in(neo_bics_list))
        )
        .sort("execution_ts", descending=True)
        .unique(subset=["end_to_end_id"], keep="first")
        .join(universe["customers"].select(["customer_id", "age"]), on="customer_id", how="left")
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

    # Écriture en 4 shards Parquet ZSTD (~30 Mo chacun) pour lecture parallèle ultra-rapide BigLake
    shard_size = (df.height + 3) // 4
    for idx_s in range(4):
        shard = df.slice(idx_s * shard_size, shard_size)
        shard.write_parquet(events_dir / f"part-{idx_s:05d}.parquet", compression="zstd")

    iban_df = generate_iban_beneficiary_table(rng, leak_90d_df, accounts_df)
    iban_df.write_parquet(iban_dir / "part-00000.parquet", compression="zstd")

    stats = {
        "seed": DEMO_SEED,
        "total_raw_payment_events": df.height,
        "duplicate_end_to_end_id_events": EXACT_DUP_RETRY_EVENTS,
        "duplicate_end_to_end_id_pct": dup_pct,
        "non_settled_rjct_pdng_events": EXACT_NON_SETTLED_EVENTS,
        "non_settled_rjct_pdng_pct": non_settled_pct,
        "unique_settled_acsc_events": EXACT_UNIQUE_ACSC_EVENTS,
        "raw_unfiltered_90d_neobank_eur": round(raw_naive_leak_cents / 100.0, 2),
        "clean_dedup_acsc_90d_neobank_eur": round(clean_leak_cents / 100.0, 2),
        "young_18_32_day_1_5_share_pct": round(young_1_5_cents * 100.0 / clean_leak_cents, 2),
        "iban_beneficiary_events": iban_df.height,
    }
    (out_dir / "_manifest_payments_silo.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print(f"[generate_payments_stream] Terminé en {elapsed:.2f}s -> {out_dir}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
