"""
Générateur déterministe du silo Finance SAP / PCEC & Trésorerie ALM (seed=2026)
adossé au socle partagé `shared_universe.py`.

Produit une table unique `raw_sap_gl_alm` (exactement 1 200 000 lignes) chargée
directement dans BigQuery `raw_bank.raw_sap_gl_alm` par `scripts/load_finance_sap_bq.sh` :

  Sortie locale : `00_data_generator/output/RAW/FINANCE_SAP_ALM/raw_sap_gl_alm.parquet`
  Schéma BQ documenté : `00_data_generator/output/bq_schemas/raw_sap_gl_alm.json`

Périmètre : extraction SAP du « grand livre d'écart PNB » sur la fenêtre de 90 jours
[2026-08-15 .. 2026-11-12] — comptes de résultat PCEC classes 6 & 7 + comptes de
liaison internes 58* (aucun compte de bilan classes 1 à 5).

4 familles de lignes (colonne `source_system`) :
  1. SAP_FI_GL     (ledger REEL)   : écritures réelles produits (C) & charges (D) par agence.
  2. BPC_BUDGET_T4 (ledger BUDGET) : budget PNB par agence / mois / compte, chargé en
                                     contre-valeur NÉGATIVE (convention BPC : réel − budget).
  3. ALM_TCI_DROP  (ledger REEL)   : 90 dépôts quotidiens de la Trésorerie Centrale — charge TCI
                                     de remplacement des dépôts à vue évaporés (PCEC 601320).
  4. SAP_FI_LIAISON(ledger REEL)   : virements internes compte courant -> livret (58*), 2 jambes D/C.

Invariants vérifiés au centime près (AGENTS.md §2) :
  * SQL naïf  : SUM(gross_amount_eur)                                       = +42 800 000,00 €
  * SQL signé : SUM(gross * IF(sens_dc='D',-1,1)) WHERE pcec NOT LIKE '58%' = -24 120 000,00 €
  * Certifié  : SQL signé − 250 PDF hors-SAP (-14 300 000,00 €)              = -38 420 000,00 €
  * Le grand livre réel (hors ALM, hors 58*) est exactement au budget (écart signé = 0,00 €).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from shared_universe import (
    ALM_TCI_COST_90D_CENTS,
    BASE_DIR,
    CERTIFIED_PNB_VARIANCE_CENTS,
    DEMO_SEED,
    NAIVE_PNB_VARIANCE_CENTS,
    PDF_PROMO_COST_CENTS,
    QUARTER_START_DATE,
    SNAPSHOT_DATE,
    TOTAL_LEAK_90D_CENTS,
    UNIVERSE_CACHE_DIR,
    build_or_load_universe,
    distribute_exact_cents,
)

# ==============================================================================
# Paramètres du silo Finance
# ==============================================================================
DEFAULT_OUTPUT_RAW_DIR: Path = BASE_DIR / "output" / "RAW"
DEFAULT_SCHEMA_DIR: Path = BASE_DIR / "output" / "bq_schemas"
TABLE_NAME: str = "raw_sap_gl_alm"

N_GL_ROWS_TOTAL: int = 1_200_000
COMPANY_CODE: str = "HEXA"
FISCAL_YEAR: int = 2026

# Budget PNB du trimestre (fenêtre 90 j) — montants positifs en centimes
BUDGET_PRODUITS_CENTS: int = 26_000_000_000  # 260,00 M€
BUDGET_CHARGES_CENTS: int = 8_000_000_000  # 80,00 M€

# Virements internes compte -> livret (58*) : 20 000 virements x 2 jambes = 12,40 M€ bruts
N_INTERNAL_TRANSFERS: int = 20_000
INTERNAL_TRANSFER_GROSS_CENTS: int = 1_240_000_000  # somme des 2 jambes D + C

# Dépassement symétrique réel vs budget (produits ET charges) => écart signé nul,
# mais +2 x 3,14 M€ dans une somme non signée.
#   naïf = 2*delta + ALM + liaison 58*  =>  delta = (42,80 - 24,12 - 12,40) / 2 = 3,14 M€
ACTUAL_OVER_BUDGET_DELTA_CENTS: int = (
    NAIVE_PNB_VARIANCE_CENTS - ALM_TCI_COST_90D_CENTS - INTERNAL_TRANSFER_GROSS_CENTS
) // 2
assert 2 * ACTUAL_OVER_BUDGET_DELTA_CENTS + ALM_TCI_COST_90D_CENTS + INTERNAL_TRANSFER_GROSS_CENTS == (
    NAIVE_PNB_VARIANCE_CENTS
)

# Convention ALM (REG_02_CHARTE_ALM_TCI) : tirage marché à 3 mois, base ACT/360 (90 j),
# taux = €STR du jour + spread de liquidité fixe de 32 bps.
# => €STR moyen pondéré 3,667 % + 32 bps = TCI 3,987 % (~399 bps).
ALM_TERM_DAYS: int = 90
ALM_DAY_COUNT_BASIS: int = 360
ALM_SPREAD_BPS: float = 32.0
ALM_AGENCY_CODE: str = "0000"  # Trésorerie Centrale (siège)
ALM_REGION_CODE: str = "SIEGE"

# Plan de comptes PCEC (compte, libellé, poids)
PRODUITS_ACCOUNTS: list[tuple[str, str, float]] = [
    ("702100", "Intérêts sur crédits habitat", 0.42),
    ("702200", "Intérêts sur crédits à la consommation", 0.14),
    ("702300", "Intérêts sur découverts comptes à vue", 0.05),
    ("706100", "Commissions de tenue de compte & packages", 0.15),
    ("706200", "Commissions sur moyens de paiement & cartes", 0.12),
    ("706300", "Commissions d'intervention", 0.04),
    ("708100", "Commissions de placement assurance & prévoyance", 0.08),
]
CHARGES_ACCOUNTS: list[tuple[str, str, float]] = [
    ("602100", "Intérêts versés sur livrets réglementés (A / LDDS)", 0.38),
    ("602200", "Intérêts versés sur livrets Hexa (Livret Maison)", 0.17),
    ("601100", "Charges de refinancement interbancaire structurel", 0.30),
    ("606100", "Commissions versées schémas cartes & interchange", 0.15),
]
ALM_ACCOUNT: tuple[str, str] = ("601320", "Charge de refinancement TCI ALM (dépôts à vue évaporés)")
LIAISON_ACCOUNT: tuple[str, str] = ("581000", "Virements internes compte courant -> livret (liaison)")
# Comptes des avenants PDF : volontairement ABSENTS de SAP (engagements hors-SAP, déversement M+1)
PDF_ONLY_ACCOUNTS: tuple[str, ...] = ("602910", "602920", "708590")

PRODUITS_SHARE_OF_ROWS: float = 0.70

OUTPUT_COLUMNS: list[str] = [
    "gl_line_id",
    "company_code",
    "fiscal_year",
    "fiscal_period",
    "ledger",
    "source_system",
    "doc_type",
    "doc_number",
    "line_item",
    "posting_date",
    "agency_code",
    "region_code",
    "pcec_account",
    "pcec_account_label",
    "sens_dc",
    "gross_amount_cents",
    "item_text",
]

BQ_SCHEMA: list[dict[str, str]] = [
    {"name": "gl_line_id", "type": "STRING", "description": "Identifiant unique de la ligne comptable (doc_number-line_item)."},
    {"name": "company_code", "type": "STRING", "description": "Société SAP (BUKRS) — HEXA = Banque Hexagone."},
    {"name": "fiscal_year", "type": "INTEGER", "description": "Exercice comptable (GJAHR)."},
    {"name": "fiscal_period", "type": "INTEGER", "description": "Période comptable = mois (MONAT), 8 à 11 sur la fenêtre 2026-08-15 .. 2026-11-12."},
    {"name": "ledger", "type": "STRING", "description": "Ledger : REEL (grand livre réel SAP FI + dépôts ALM) ou BUDGET (plan BPC)."},
    {"name": "source_system", "type": "STRING", "description": "Origine : SAP_FI_GL, SAP_FI_LIAISON (virements internes 58*), BPC_BUDGET_T4 ou ALM_TCI_DROP (Trésorerie Centrale)."},
    {"name": "doc_type", "type": "STRING", "description": "Type de pièce SAP (BLART) : SA écriture GL, UB virement interne, BU budget, TC charge TCI ALM."},
    {"name": "doc_number", "type": "STRING", "description": "Numéro de pièce comptable (BELNR)."},
    {"name": "line_item", "type": "INTEGER", "description": "Numéro de poste dans la pièce (BUZEI)."},
    {"name": "posting_date", "type": "DATE", "description": "Date comptable (BUDAT). Budget : 1er jour de la période dans la fenêtre."},
    {"name": "agency_code", "type": "STRING", "description": "Centre de profit = code agence sur 4 caractères ('0000' = Trésorerie Centrale)."},
    {"name": "region_code", "type": "STRING", "description": "Région commerciale (REG1..REG8, SIEGE pour la Trésorerie Centrale)."},
    {"name": "pcec_account", "type": "STRING", "description": "Compte PCEC (HKONT) : 6xxxxx charges, 7xxxxx produits, 58xxxx comptes de liaison internes."},
    {"name": "pcec_account_label", "type": "STRING", "description": "Libellé du compte PCEC."},
    {"name": "sens_dc", "type": "STRING", "description": "Code sens comptable (SHKZG) : D = Débit (charge), C = Crédit (produit). Le montant brut n'est jamais signé par SAP."},
    {"name": "gross_amount_eur", "type": "NUMERIC", "description": "Montant brut en euros (WRBTR), non signé pour le ledger REEL ; lignes BUDGET chargées en contre-valeur négative (convention BPC réel − budget)."},
    {"name": "item_text", "type": "STRING", "description": "Libellé de poste (SGTXT)."},
]

TABLE_DESCRIPTION: str = (
    "Grand livre d'écart PNB SAP / PCEC & dépôts Trésorerie ALM (fenêtre 90 j 2026-08-15 .. 2026-11-12). "
    "Comptes de résultat 6/7 + liaisons internes 58*, ledger REEL vs BUDGET. Chargé directement depuis "
    "l'extraction SAP (bq load) — 1 200 000 lignes."
)


def window_days() -> list[date]:
    days: list[date] = []
    cur = QUARTER_START_DATE
    while cur <= SNAPSHOT_DATE:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def build_actual_gl_lines(
    rng: np.random.Generator,
    n_rows: int,
    days: list[date],
    agencies_df: pl.DataFrame,
    agency_weights: np.ndarray,
) -> pl.DataFrame:
    """Écritures réelles SAP FI (produits C / charges D) réparties par agence, jour et compte."""
    n_prod = int(round(n_rows * PRODUITS_SHARE_OF_ROWS))
    n_chg = n_rows - n_prod
    frames: list[pl.DataFrame] = []
    for accounts, n, total_cents, sens in (
        (PRODUITS_ACCOUNTS, n_prod, BUDGET_PRODUITS_CENTS + ACTUAL_OVER_BUDGET_DELTA_CENTS, "C"),
        (CHARGES_ACCOUNTS, n_chg, BUDGET_CHARGES_CENTS + ACTUAL_OVER_BUDGET_DELTA_CENTS, "D"),
    ):
        acc_w = np.array([a[2] for a in accounts])
        acc_idx = rng.choice(len(accounts), size=n, p=acc_w / acc_w.sum())
        ag_idx = rng.choice(agencies_df.height, size=n, p=agency_weights)
        day_idx = rng.integers(0, len(days), size=n)
        weights = rng.lognormal(mean=0.0, sigma=0.9, size=n)
        cents = distribute_exact_cents(weights, total_cents, min_cents=100, max_cents=5_000_000)
        frames.append(
            pl.DataFrame(
                {
                    "posting_date": [days[i] for i in day_idx],
                    "agency_code": agencies_df["agency_code_4"].to_numpy()[ag_idx],
                    "region_code": agencies_df["region_code"].to_numpy()[ag_idx],
                    "pcec_account": np.array([a[0] for a in accounts])[acc_idx],
                    "pcec_account_label": np.array([a[1] for a in accounts])[acc_idx],
                    "sens_dc": [sens] * n,
                    "gross_amount_cents": cents.astype(np.int64),
                }
            )
        )
    df = pl.concat(frames).with_columns(
        pl.lit("REEL").alias("ledger"),
        pl.lit("SAP_FI_GL").alias("source_system"),
        pl.lit("SA").alias("doc_type"),
        pl.lit(1, dtype=pl.Int32).alias("line_item"),
    )
    return df.with_columns(
        pl.concat_str(
            [pl.lit("Ecriture "), pl.col("pcec_account_label"), pl.lit(" ag. "), pl.col("agency_code")]
        ).alias("item_text")
    )


def build_budget_lines(
    rng: np.random.Generator, actual_df: pl.DataFrame, agencies_df: pl.DataFrame
) -> pl.DataFrame:
    """Budget BPC par agence x période x compte, chargé en contre-valeur négative."""
    days = window_days()
    periods = sorted({d.month for d in days})
    period_first_day = {m: min(d for d in days if d.month == m) for m in periods}

    actual_cells = (
        actual_df.with_columns(pl.col("posting_date").dt.month().cast(pl.Int32).alias("fiscal_period"))
        .group_by(["agency_code", "fiscal_period", "pcec_account"])
        .agg(pl.col("gross_amount_cents").sum().alias("actual_cents"))
    )
    frames: list[pl.DataFrame] = []
    for accounts, total_cents, sens in (
        (PRODUITS_ACCOUNTS, BUDGET_PRODUITS_CENTS, "C"),
        (CHARGES_ACCOUNTS, BUDGET_CHARGES_CENTS, "D"),
    ):
        grid = (
            agencies_df.select(["agency_code_4", "region_code"])
            .rename({"agency_code_4": "agency_code"})
            .join(pl.DataFrame({"fiscal_period": pl.Series(periods, dtype=pl.Int32)}), how="cross")
            .join(
                pl.DataFrame(
                    {"pcec_account": [a[0] for a in accounts], "pcec_account_label": [a[1] for a in accounts]}
                ),
                how="cross",
            )
            .join(actual_cells, on=["agency_code", "fiscal_period", "pcec_account"], how="left")
            .with_columns(pl.col("actual_cents").fill_null(0))
            .sort(["agency_code", "fiscal_period", "pcec_account"])
        )
        noise = rng.lognormal(mean=0.0, sigma=0.06, size=grid.height)
        weights = (grid["actual_cents"].to_numpy().astype(np.float64) + 1.0) * noise
        cents = distribute_exact_cents(weights, total_cents, min_cents=1, max_cents=total_cents)
        frames.append(grid.with_columns(pl.Series("budget_cents", cents.astype(np.int64)), pl.lit(sens).alias("sens_dc")))

    budget = pl.concat(frames)
    return budget.select(
        pl.col("fiscal_period")
        .replace_strict(period_first_day, return_dtype=pl.Date)
        .alias("posting_date"),
        "agency_code",
        "region_code",
        "pcec_account",
        "pcec_account_label",
        "sens_dc",
        (-pl.col("budget_cents")).alias("gross_amount_cents"),
        pl.lit("BUDGET").alias("ledger"),
        pl.lit("BPC_BUDGET_T4").alias("source_system"),
        pl.lit("BU").alias("doc_type"),
        pl.lit(1, dtype=pl.Int32).alias("line_item"),
        pl.concat_str(
            [pl.lit("Budget T4 2026 P"), pl.col("fiscal_period").cast(pl.Utf8), pl.lit(" "), pl.col("pcec_account_label")]
        ).alias("item_text"),
    )


def build_alm_tci_lines(rng: np.random.Generator, leak_df: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """90 dépôts quotidiens ALM : assiette = fuite du jour, coût = assiette x TCI x 90/360."""
    daily = (
        leak_df.group_by("accounting_date")
        .agg(pl.col("amount_cents").sum().alias("draw_cents"))
        .sort("accounting_date")
    )
    draw = daily["draw_cents"].to_numpy().astype(np.int64)
    assert int(draw.sum()) == TOTAL_LEAK_90D_CENTS
    n = len(draw)

    # Fixings €STR quotidiens (marche aléatoire bornée) recalés pour que le TCI moyen pondéré
    # (€STR + spread fixe de 32 bps, charte REG_02) donne exactement la charge ALM cible.
    walk = np.clip(np.cumsum(rng.normal(0.0, 0.004, size=n)), -0.03, 0.03)
    year_frac = ALM_TERM_DAYS / ALM_DAY_COUNT_BASIS
    target_tci_pct = 100.0 * ALM_TCI_COST_90D_CENTS / (TOTAL_LEAK_90D_CENTS * year_frac)
    spread_pct = ALM_SPREAD_BPS / 100.0
    estr = walk + (target_tci_pct - spread_pct - float((draw * walk).sum() / draw.sum()))
    wavg_estr = float((draw * estr).sum() / draw.sum())
    tci = estr + spread_pct

    cost = np.rint(draw * (tci / 100.0) * year_frac).astype(np.int64)
    cost[int(np.argmax(cost))] += ALM_TCI_COST_90D_CENTS - int(cost.sum())  # arrondi au centime
    assert int(cost.sum()) == ALM_TCI_COST_90D_CENTS

    dates = [date(int(s[:4]), int(s[4:6]), int(s[6:8])) for s in daily["accounting_date"].to_list()]
    texts = [
        f"TCI ALM tirage 3M assiette {d / 100:,.2f} EUR - ESTR {e:.3f} % + {spread_pct * 100:.1f} bps".replace(",", " ")
        for d, e in zip(draw, estr)
    ]
    df = pl.DataFrame(
        {
            "posting_date": dates,
            "agency_code": [ALM_AGENCY_CODE] * n,
            "region_code": [ALM_REGION_CODE] * n,
            "pcec_account": [ALM_ACCOUNT[0]] * n,
            "pcec_account_label": [ALM_ACCOUNT[1]] * n,
            "sens_dc": ["D"] * n,
            "gross_amount_cents": cost,
            "ledger": ["REEL"] * n,
            "source_system": ["ALM_TCI_DROP"] * n,
            "doc_type": ["TC"] * n,
            "line_item": pl.Series([1] * n, dtype=pl.Int32),
            "item_text": texts,
        }
    )
    params = {
        "estr_wavg_pct": round(wavg_estr, 4),
        "spread_bps": round(spread_pct * 100, 2),
        "tci_wavg_pct": round(target_tci_pct, 4),
        "term": f"{ALM_TERM_DAYS}/{ALM_DAY_COUNT_BASIS}",
    }
    return df, params


def build_internal_transfer_lines(
    rng: np.random.Generator, days: list[date], accounts_df: pl.DataFrame
) -> pl.DataFrame:
    """Virements internes compte courant -> livret (58*), 2 jambes D/C de même montant."""
    savings = accounts_df.filter(pl.col("account_type") != "CC_CHQ")
    cc_by_cust = accounts_df.filter(pl.col("account_type") == "CC_CHQ").select(
        "cust_idx", pl.col("account_id").alias("cc_account_id")
    )
    pick = rng.choice(savings.height, size=N_INTERNAL_TRANSFERS, replace=True)
    sav = savings[pick].join(cc_by_cust, on="cust_idx", how="left")

    day_w = np.array([3.0 if 1 <= d.day <= 5 else 1.0 for d in days])
    day_idx = rng.choice(len(days), size=N_INTERNAL_TRANSFERS, p=day_w / day_w.sum())
    leg_cents = distribute_exact_cents(
        rng.lognormal(0.0, 0.8, size=N_INTERNAL_TRANSFERS),
        INTERNAL_TRANSFER_GROSS_CENTS // 2,
        min_cents=1_000,
        max_cents=500_000,
    ).astype(np.int64)

    base = pl.DataFrame(
        {
            "transfer_no": np.arange(N_INTERNAL_TRANSFERS, dtype=np.int64),
            "posting_date": [days[i] for i in day_idx],
            "agency_code": sav["agency_code_4"],
            "gross_amount_cents": leg_cents,
            "item_text": [
                f"VIR INT {cc} -> {t} {acc}"
                for cc, t, acc in zip(sav["cc_account_id"], sav["account_type"], sav["account_id"])
            ],
        }
    )
    legs = pl.concat(
        [
            base.with_columns(pl.lit("D").alias("sens_dc"), pl.lit(1, dtype=pl.Int32).alias("line_item")),
            base.with_columns(pl.lit("C").alias("sens_dc"), pl.lit(2, dtype=pl.Int32).alias("line_item")),
        ]
    )
    return legs.with_columns(
        pl.lit(LIAISON_ACCOUNT[0]).alias("pcec_account"),
        pl.lit(LIAISON_ACCOUNT[1]).alias("pcec_account_label"),
        pl.lit("REEL").alias("ledger"),
        pl.lit("SAP_FI_LIAISON").alias("source_system"),
        pl.lit("UB").alias("doc_type"),
    )


def assign_doc_numbers(df: pl.DataFrame, prefix: str, group_col: str | None = None) -> pl.DataFrame:
    """BELNR sur 10 caractères : préfixe 2 chiffres + séquence (partagée entre jambes si group_col)."""
    if group_col is None:
        seq = pl.int_range(1, pl.len() + 1)
    else:
        seq = pl.col(group_col) + 1
    return df.with_columns(
        pl.concat_str([pl.lit(prefix), seq.cast(pl.Utf8).str.zfill(8)]).alias("doc_number")
    )


def to_arrow_with_decimal(df: pl.DataFrame) -> pa.Table:
    """Convertit gross_amount_cents (int) en gross_amount_eur DECIMAL(18,2) exact (-> NUMERIC BQ)."""
    cents = df["gross_amount_cents"].to_list()
    eur = pa.array([Decimal(c).scaleb(-2) for c in cents], type=pa.decimal128(18, 2))
    tbl = df.drop("gross_amount_cents").to_arrow()
    idx = tbl.schema.get_field_index("sens_dc") + 1
    tbl = tbl.add_column(idx, "gross_amount_eur", eur)
    # Types simples et stables pour BigQuery (pas de large_string / string_view)
    fields = []
    for f in tbl.schema:
        if pa.types.is_large_string(f.type) or str(f.type) == "string_view":
            fields.append(pa.field(f.name, pa.string()))
        else:
            fields.append(f)
    return tbl.cast(pa.schema(fields))


def verify_invariants(parquet_path: Path) -> dict:
    """Rejoue les SQL naïf et certifié (scriptés dans stage_ui) au centime près via DuckDB."""
    con = duckdb.connect()
    t = f"read_parquet('{parquet_path.as_posix()}')"
    naive = con.execute(f"SELECT SUM(gross_amount_eur) FROM {t}").fetchone()[0]
    gl_net = con.execute(
        f"SELECT SUM(gross_amount_eur * CASE WHEN sens_dc = 'D' THEN -1 ELSE 1 END) FROM {t} "
        "WHERE NOT starts_with(pcec_account, '58')"
    ).fetchone()[0]
    gl_without_alm = con.execute(
        f"SELECT SUM(gross_amount_eur * CASE WHEN sens_dc = 'D' THEN -1 ELSE 1 END) FROM {t} "
        "WHERE NOT starts_with(pcec_account, '58') AND source_system <> 'ALM_TCI_DROP'"
    ).fetchone()[0]
    n_rows = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    n_ids = con.execute(f"SELECT COUNT(DISTINCT gl_line_id) FROM {t}").fetchone()[0]
    n_pdf_acc = con.execute(
        f"SELECT COUNT(*) FROM {t} WHERE pcec_account IN {PDF_ONLY_ACCOUNTS}"
    ).fetchone()[0]
    n_bilan = con.execute(
        f"SELECT COUNT(*) FROM {t} WHERE substr(pcec_account, 1, 1) IN ('1','2','3','4') "
        "OR (substr(pcec_account, 1, 1) = '5' AND NOT starts_with(pcec_account, '58'))"
    ).fetchone()[0]

    pdf_cents = PDF_PROMO_COST_CENTS
    gt_path = UNIVERSE_CACHE_DIR / "promo_pdfs_ground_truth.parquet"
    if gt_path.exists():
        pdf_cents = int(pl.read_parquet(gt_path)["committed_cents"].sum())
    certified_cents = int(round(gl_net * 100)) - pdf_cents

    assert n_rows == N_GL_ROWS_TOTAL, n_rows
    assert n_ids == N_GL_ROWS_TOTAL, "gl_line_id non unique"
    assert n_pdf_acc == 0, "Les comptes PDF 602910/602920/708590 doivent rester hors-SAP"
    assert n_bilan == 0, "Aucun compte de bilan (classes 1 à 5 hors 58*) dans l'extraction"
    assert int(round(naive * 100)) == NAIVE_PNB_VARIANCE_CENTS, naive
    assert int(round(gl_net * 100)) == -ALM_TCI_COST_90D_CENTS, gl_net
    assert int(round(gl_without_alm * 100)) == 0, gl_without_alm
    assert pdf_cents == PDF_PROMO_COST_CENTS, pdf_cents
    assert certified_cents == CERTIFIED_PNB_VARIANCE_CENTS, certified_cents

    return {
        "rows": n_rows,
        "naive_sum_gross_eur": f"{naive:.2f}",
        "signed_gl_net_excl_58_eur": f"{gl_net:.2f}",
        "signed_gl_excl_58_excl_alm_eur": f"{gl_without_alm:.2f}",
        "pdf_promo_cost_eur": f"{-pdf_cents / 100:.2f}",
        "certified_pnb_variance_eur": f"{certified_cents / 100:.2f}",
    }


def generate(output_raw_dir: Path, schema_dir: Path) -> dict:
    rng = np.random.default_rng(DEMO_SEED + 4)  # flux dédié au silo #4 Finance
    universe = build_or_load_universe()
    agencies_df = universe["agencies"]
    customers_df = universe["customers"]
    days = window_days()
    assert len(days) == 90

    # Poids agences = nombre de clients rattachés (activité comptable proportionnelle)
    cust_per_ag = (
        customers_df.group_by("agency_code_4").len().rename({"len": "n"})
    )
    ag = agencies_df.join(cust_per_ag, on="agency_code_4", how="left").with_columns(pl.col("n").fill_null(1))
    agency_weights = ag["n"].to_numpy().astype(np.float64)
    agency_weights /= agency_weights.sum()

    alm_df, alm_params = build_alm_tci_lines(rng, universe["leak_events_90d"])
    liaison_df = build_internal_transfer_lines(rng, days, universe["accounts"])
    liaison_df = liaison_df.join(
        agencies_df.select(pl.col("agency_code_4").alias("agency_code"), "region_code"), on="agency_code", how="left"
    )
    n_budget = agencies_df.height * len({d.month for d in days}) * (len(PRODUITS_ACCOUNTS) + len(CHARGES_ACCOUNTS))
    n_actual = N_GL_ROWS_TOTAL - alm_df.height - liaison_df.height - n_budget
    actual_df = build_actual_gl_lines(rng, n_actual, days, agencies_df, agency_weights)
    budget_df = build_budget_lines(rng, actual_df, agencies_df)
    assert budget_df.height == n_budget

    actual_df = assign_doc_numbers(actual_df.sort(["posting_date", "agency_code"]), "01")
    liaison_df = assign_doc_numbers(liaison_df, "05", group_col="transfer_no").drop("transfer_no")
    alm_df = assign_doc_numbers(alm_df, "07")
    budget_df = assign_doc_numbers(budget_df, "09")

    gl = (
        pl.concat(
            [
                d.with_columns(pl.col("line_item").cast(pl.Int32)).select(
                    [c for c in OUTPUT_COLUMNS if c not in ("gl_line_id", "company_code", "fiscal_year", "fiscal_period")]
                )
                for d in (actual_df, liaison_df, alm_df, budget_df)
            ]
        )
        .with_columns(
            pl.concat_str([pl.col("doc_number"), pl.lit("-"), pl.col("line_item").cast(pl.Utf8).str.zfill(3)]).alias(
                "gl_line_id"
            ),
            pl.lit(COMPANY_CODE).alias("company_code"),
            pl.lit(FISCAL_YEAR, dtype=pl.Int32).alias("fiscal_year"),
            pl.col("posting_date").dt.month().cast(pl.Int32).alias("fiscal_period"),
        )
        .select(OUTPUT_COLUMNS)
        .sort(["posting_date", "doc_number", "line_item"])
    )
    assert gl.height == N_GL_ROWS_TOTAL

    out_dir = output_raw_dir / "FINANCE_SAP_ALM"
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / f"{TABLE_NAME}.parquet"
    pq.write_table(to_arrow_with_decimal(gl), parquet_path, compression="zstd")

    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / f"{TABLE_NAME}.json").write_text(
        json.dumps([{**f, "mode": "NULLABLE"} for f in BQ_SCHEMA], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (schema_dir / f"{TABLE_NAME}.description.txt").write_text(TABLE_DESCRIPTION, encoding="utf-8")

    checks = verify_invariants(parquet_path)
    summary = {
        "silo": "Finance SAP / PCEC & Trésorerie ALM",
        "parquet": str(parquet_path),
        "bq_target": f"raw_bank.{TABLE_NAME}",
        "rows_by_source": dict(
            gl.group_by("source_system").len().sort("source_system").iter_rows()
        ),
        "alm_tci": alm_params,
        "invariants": checks,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--output-raw-dir", type=Path, default=DEFAULT_OUTPUT_RAW_DIR)
    parser.add_argument("--schema-dir", type=Path, default=DEFAULT_SCHEMA_DIR)
    args = parser.parse_args()
    generate(args.output_raw_dir, args.schema_dir)


if __name__ == "__main__":
    main()
