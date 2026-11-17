"""
Journal partagé des opérations clients (seed=2026) — source de vérité unique de la « vie du client ».

Lu à la fois par :
  - `generate_mainframe_cfonb.py`  -> mouvements CFONB 120 ('04' + complément SEPA '05'),
  - `generate_payments_stream.py`  -> événements ISO 20022 pacs.008 réglés (ACSC).

Garantit que chaque opération réglée d'un compte présent dans le Mainframe existe à l'identique
dans les deux silos (même end_to_end_id, même compte, même date, même montant, même contrepartie).

Contenu (hors client témoin et hors fuite 90 j, déjà portés par `shared_universe.py`) :
  - REGULAR_SALARY / REGULAR_PENSION : revenu mensuel stable, versé autour du même jour (1er-5 ; 9 pour la retraite)
  - REGULAR_SDD : prélèvements fixes (loyer, EDF saisonnier, box, assurance, impôts jan-oct, streaming
                  15,99 € puis 19,99 € à partir du 01/11/2026)
  - REGULAR_HEALTH : remboursements CPAM / mutuelle ponctuels
  - REGULAR_CARD : dépenses carte variables (catalogue partagé `payments_contract.py`)
  - ORPHAN_CARD : 2 opérations carte pour chacun des 650 comptes ouverts après le batch Mainframe J-1
  - LEAK_HIST : 100 000 virements néobanques historiques (avant le 13/08/2026)
  - INTERNAL_58 : épargne programmée compte courant -> livret (Mainframe uniquement, pas SEPA)

Volumes exacts imposés par les invariants des deux silos :
  - SEPA ACSC uniques = 5 487 000 = témoin + 200 000 fuites 90 j + LEAK_HIST + REGULAR_* + ORPHAN_CARD
  - CFONB '04'        = 5 500 000 = témoin + 200 000 fuites 90 j + LEAK_HIST + REGULAR_* + 2 x INTERNAL_58
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from payments_contract import COUNTERPARTIES, NEOBANK_BICS, NEOBANK_LABELS, neobank_beneficiary_iban
from shared_universe import (
    DEMO_SEED,
    HISTORY_START_DATE,
    SNAPSHOT_DATE,
    UNIVERSE_CACHE_DIR,
    WITNESS_CUST_IDX,
    build_or_load_universe,
)

LEDGER_VERSION: str = "v2"
LEDGER_PATH: Path = UNIVERSE_CACHE_DIR / f"customer_ledger_{LEDGER_VERSION}.parquet"

# Invariants des silos
SEPA_UNIQUE_ACSC_EVENTS: int = 5_487_000
CFONB_TOTAL_MOVEMENTS: int = 5_500_000
N_WITNESS_OPS: int = 142          # 17 mois x 8 opérations + 6 opérations en novembre 2026
N_LEAK_90D: int = 200_000         # portés par shared_universe.leak_events_90d
N_LEAK_HIST: int = 100_000
N_ORPHAN_CARD_PER_ACCOUNT: int = 2
N_ORPHAN_ACCOUNTS: int = 650

N_REGULAR_SEPA: int = SEPA_UNIQUE_ACSC_EVENTS - N_WITNESS_OPS - N_LEAK_90D - N_LEAK_HIST  # 5 186 858
N_ORPHAN_OPS: int = N_ORPHAN_ACCOUNTS * N_ORPHAN_CARD_PER_ACCOUNT                        # 1 300
# CFONB = témoin + fuites + (régulier hors orphelins) + 2 x internes  =>  internes = 7 150 paires
N_INTERNAL_PAIRS: int = (
    CFONB_TOTAL_MOVEMENTS - N_WITNESS_OPS - N_LEAK_90D - N_LEAK_HIST - (N_REGULAR_SEPA - N_ORPHAN_OPS)
) // 2
assert N_WITNESS_OPS + N_LEAK_90D + N_LEAK_HIST + (N_REGULAR_SEPA - N_ORPHAN_OPS) + 2 * N_INTERNAL_PAIRS == (
    CFONB_TOTAL_MOVEMENTS
)

STREAMING_HIKE_DATE: date = date(2026, 11, 1)  # 15,99 € -> 19,99 € (+4,00 €), détecté par le Budget Insight

# Codes CFONB par famille : (code opération interne, code AFB)
CFONB_CODES: dict[str, tuple[str, str]] = {
    "SALARY": ("0420", "05"),
    "HEALTH": ("0430", "05"),
    "SDD": ("0650", "08"),
    "CARD": ("0310", "28"),
    "LEAK": ("0810", "16"),
}

_CP = {c.key: c for c in COUNTERPARTIES}
SDD_ITEMS: list[tuple[str, float]] = [  # (clé contrepartie, probabilité qu'un client ait ce prélèvement)
    ("LOYER", 0.30),
    ("EDF", 0.40),
    ("ORANGE", 0.35),
    ("ASSURANCE", 0.20),
    ("STRMFLIX", 0.35),
    ("DGFIP", 0.15),
]
CARD_KEYS: list[str] = [c.key for c in COUNTERPARTIES if c.scheme.startswith("CARD")]
CARD_WEIGHTS: np.ndarray = np.array([_CP[k].weight for k in CARD_KEYS]) / sum(_CP[k].weight for k in CARD_KEYS)


def _months() -> pl.DataFrame:
    rows = []
    for y, m in [(2025, mm) for mm in range(6, 13)] + [(2026, mm) for mm in range(1, 12)]:
        start = date(y, m, 1)
        nxt = date(y + (m == 12), (m % 12) + 1, 1)
        end = min(nxt - timedelta(days=1), SNAPSHOT_DATE)
        rows.append((y, m, start.toordinal(), end.toordinal()))
    return pl.DataFrame(rows, schema=["year", "month", "m_start_ord", "m_end_ord"], orient="row")


def _ord_to_str(ords: np.ndarray) -> np.ndarray:
    base = HISTORY_START_DATE.toordinal()
    lookup = np.array(
        [(HISTORY_START_DATE + timedelta(days=i)).strftime("%Y%m%d") for i in range(SNAPSHOT_DATE.toordinal() - base + 1)],
        dtype="U8",
    )
    return lookup[ords - base]


def _cp_columns(keys: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "cp_key": keys.astype("U12"),
        "label": np.array([_CP[k].label for k in keys], dtype="U31"),
        "creditor_bic": np.array([_CP[k].bic for k in keys], dtype="U12"),
        "creditor_name": np.array([_CP[k].name for k in keys], dtype="U40"),
        "creditor_iban": np.array([_CP[k].iban for k in keys], dtype="U34"),
        "payment_scheme": np.array([_CP[k].scheme for k in keys], dtype="U16"),
    }


def _frame(family: str, acc_idx, ords, amounts, signs, keys, sec_lo: int, sec_hi: int, rng, cfonb: str) -> pl.DataFrame:
    n = len(acc_idx)
    cols = _cp_columns(np.asarray(keys))
    op, afb = CFONB_CODES[cfonb]
    return pl.DataFrame(
        {
            "family": np.full(n, family, dtype="U16"),
            "acc_idx": np.asarray(acc_idx, dtype=np.int32),
            "op_ord": np.asarray(ords, dtype=np.int32),
            "sec_of_day": rng.integers(sec_lo, sec_hi, size=n, dtype=np.int32),
            "amount_cents": np.asarray(amounts, dtype=np.int64),
            "signed_cents": np.asarray(amounts, dtype=np.int64) * np.asarray(signs, dtype=np.int64),
            **cols,
            "cfonb_code_op": np.full(n, op, dtype="U4"),
            "cfonb_afb": np.full(n, afb, dtype="U2"),
        }
    )


def build_customer_ledger(universe: dict[str, pl.DataFrame]) -> pl.DataFrame:
    rng = np.random.default_rng(DEMO_SEED + 777)
    accounts = universe["accounts"]
    customers = universe["customers"]
    snap_ord = SNAPSHOT_DATE.toordinal()
    hist_ord = HISTORY_START_DATE.toordinal()

    # ------------------------------------------------------------------ comptes courants Mainframe actifs
    cc = (
        accounts.filter((pl.col("account_type") == "CC_CHQ") & pl.col("in_mainframe") & (pl.col("acc_idx") != WITNESS_CUST_IDX))
        .join(customers.select("cust_idx", "age", "is_young_18_32"), on="cust_idx", how="left")
        .with_columns(pl.col("opening_date").str.strptime(pl.Date, "%Y%m%d").alias("open_d"))
        .with_columns(pl.col("open_d").dt.epoch("d").alias("open_epoch"))
        .sort("acc_idx")
    )
    epoch_to_ord = date(1970, 1, 1).toordinal()
    n_acc = cc.height
    acc_idx = cc["acc_idx"].to_numpy()
    open_ord = cc["open_epoch"].to_numpy().astype(np.int64) + epoch_to_ord
    ages = cc["age"].to_numpy()
    young = cc["is_young_18_32"].to_numpy()

    # Profil stable par compte
    is_pension = ages >= 64
    has_income = rng.random(n_acc) < 0.93
    income_day = np.where(is_pension, 9, np.where(young, rng.integers(1, 4, n_acc), rng.integers(1, 6, n_acc)))
    salary_base = np.clip(rng.lognormal(np.log(260_000), 0.35, n_acc), 145_000, 680_000)
    pension_base = np.clip(rng.lognormal(np.log(190_000), 0.30, n_acc), 95_000, 420_000)
    income_base = np.where(is_pension, pension_base, salary_base).round().astype(np.int64)
    card_intensity = rng.lognormal(0.0, 0.5, n_acc)

    sdd_profile: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for key, prob in SDD_ITEMS:
        cp = _CP[key]
        flag = rng.random(n_acc) < prob
        day = rng.integers(3, 21, n_acc)
        amount = rng.integers(cp.min_cents, cp.max_cents + 1, n_acc, dtype=np.int64)
        if key == "ORANGE":
            amount = (np.round(amount / 1000) * 1000 - 1).clip(cp.min_cents, cp.max_cents)  # 29,99 / 39,99 ...
        if key == "LOYER":
            day = np.full(n_acc, 5)
        sdd_profile[key] = (flag, day, amount)

    # ------------------------------------------------------------------ grille compte x mois actif
    months = _months()
    grid = (
        pl.DataFrame({"pos": np.arange(n_acc, dtype=np.int32), "open_ord": open_ord})
        .join(months, how="cross")
        .filter(pl.col("m_end_ord") >= pl.col("open_ord"))
    )
    g_pos = grid["pos"].to_numpy()
    g_month = grid["month"].to_numpy()
    g_mstart = grid["m_start_ord"].to_numpy().astype(np.int64)
    g_mend = grid["m_end_ord"].to_numpy().astype(np.int64)
    g_open = grid["open_ord"].to_numpy().astype(np.int64)

    def _valid(day_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ords = g_mstart + day_arr - 1
        ok = (ords <= g_mend) & (ords >= g_open) & (ords >= hist_ord) & (ords <= snap_ord)
        return ok, ords

    frames: list[pl.DataFrame] = []

    # Revenus mensuels (salaire / retraite)
    ok, ords = _valid(income_day[g_pos])
    sel = ok & has_income[g_pos]
    p = g_pos[sel]
    amt = (income_base[p] * (1 + rng.normal(0, 0.01, sel.sum()))).round().astype(np.int64)
    keys = np.where(is_pension[p], "RETRAITE", "SALAIRE")
    frames.append(_frame("REGULAR_INCOME", acc_idx[p], ords[sel], amt, 1, keys, 21_600, 28_800, rng, "SALARY"))

    # Prélèvements fixes
    for key, _ in SDD_ITEMS:
        flag, day, base_amt = sdd_profile[key]
        ok, ords = _valid(day[g_pos])
        sel = ok & flag[g_pos]
        if key == "DGFIP":
            sel &= g_month <= 10
        p = g_pos[sel]
        amt = base_amt[p].copy()
        if key == "EDF":
            winter = np.isin(g_month[sel], [11, 12, 1, 2, 3])
            amt = np.where(winter, amt * 1.35, amt * 0.85).round().astype(np.int64)
        if key == "STRMFLIX":
            amt = np.where(ords[sel] >= STREAMING_HIKE_DATE.toordinal(), 1_999, 1_599)
        frames.append(_frame("REGULAR_SDD", acc_idx[p], ords[sel], amt, -1, np.full(len(p), key), 25_200, 36_000, rng, "SDD"))

    # Remboursements santé ponctuels
    n_health = rng.poisson(0.08, len(g_pos))
    hp = np.repeat(np.arange(len(g_pos)), n_health)
    lo = np.maximum(g_mstart[hp], g_open[hp])
    ords = lo + np.floor(rng.random(len(hp)) * (g_mend[hp] - lo + 1)).astype(np.int64)
    keys = np.where(rng.random(len(hp)) < 0.6, "CPAM", "MUTUELLE")
    amt = np.array([rng.integers(_CP[k].min_cents, _CP[k].max_cents + 1) for k in keys], dtype=np.int64)
    frames.append(_frame("REGULAR_HEALTH", acc_idx[g_pos[hp]], ords, amt, 1, keys, 32_400, 64_800, rng, "HEALTH"))

    # Dépenses carte : complément exact jusqu'au volume SEPA cible
    n_fixed = sum(f.height for f in frames)
    n_card = N_REGULAR_SEPA - N_ORPHAN_OPS - n_fixed
    assert n_card > 0, f"Volume récurrent ({n_fixed}) supérieur au budget SEPA régulier"
    act_lo = np.maximum(g_mstart, g_open)
    active_days = (g_mend - act_lo + 1).clip(min=1)
    w = active_days * card_intensity[g_pos]
    cell = rng.choice(len(g_pos), size=n_card, p=w / w.sum())
    ords = act_lo[cell] + np.floor(rng.random(n_card) * active_days[cell]).astype(np.int64)
    keys = np.array(CARD_KEYS)[rng.choice(len(CARD_KEYS), size=n_card, p=CARD_WEIGHTS)]
    lo_c = np.array([_CP[k].min_cents for k in CARD_KEYS])
    hi_c = np.array([_CP[k].max_cents for k in CARD_KEYS])
    k_idx = np.searchsorted(np.array(CARD_KEYS), keys, sorter=np.argsort(CARD_KEYS))
    k_idx = np.argsort(CARD_KEYS)[k_idx]
    amt = lo_c[k_idx] + np.floor(rng.random(n_card) * (hi_c[k_idx] - lo_c[k_idx] + 1)).astype(np.int64)
    frames.append(_frame("REGULAR_CARD", acc_idx[g_pos[cell]], ords, amt, -1, keys, 28_800, 79_200, rng, "CARD"))

    # 650 comptes ouverts après le batch Mainframe J-1 : 2 opérations carte chacun (SEPA uniquement)
    orphans = accounts.filter((pl.col("account_type") == "CC_CHQ") & ~pl.col("in_mainframe")).sort("acc_idx")
    assert orphans.height == N_ORPHAN_ACCOUNTS
    o_acc = np.repeat(orphans["acc_idx"].to_numpy(), N_ORPHAN_CARD_PER_ACCOUNT)
    o_open = np.repeat(
        np.array([date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal() for d in orphans["opening_date"]]),
        N_ORPHAN_CARD_PER_ACCOUNT,
    )
    o_ords = o_open + np.floor(rng.random(N_ORPHAN_OPS) * (snap_ord - o_open + 1)).astype(np.int64)
    o_keys = np.array(CARD_KEYS)[rng.choice(len(CARD_KEYS), size=N_ORPHAN_OPS, p=CARD_WEIGHTS)]
    o_amt = np.array([rng.integers(_CP[k].min_cents, _CP[k].max_cents + 1) for k in o_keys], dtype=np.int64)
    frames.append(_frame("ORPHAN_CARD", o_acc, o_ords, o_amt, -1, o_keys, 28_800, 79_200, rng, "CARD"))

    regular = pl.concat(frames).sort(["op_ord", "acc_idx", "sec_of_day", "family", "cp_key"])
    assert regular.height == N_REGULAR_SEPA
    regular = regular.with_columns(
        pl.concat_str([pl.lit("E2EREG2026"), (pl.int_range(1, pl.len() + 1)).cast(pl.Utf8).str.zfill(9)]).alias("e2e_id"),
        pl.lit(True).alias("in_sepa"),
    )

    # ------------------------------------------------------------------ fuites néobanques historiques
    pre_pool = np.array([i for i in range(1, 62_001) if i != WITNESS_CUST_IDX], dtype=np.int32)
    l_acc = rng.choice(pre_pool, size=N_LEAK_HIST, replace=True)
    l_ords = rng.integers(hist_ord, date(2026, 8, 12).toordinal() + 1, size=N_LEAK_HIST)
    l_bic = np.array(NEOBANK_BICS)[rng.choice(len(NEOBANK_BICS), size=N_LEAK_HIST, p=[0.40, 0.30, 0.14, 0.10, 0.06])]
    l_amt = rng.integers(15_000, 380_000, size=N_LEAK_HIST, dtype=np.int64)
    op, afb = CFONB_CODES["LEAK"]
    leak_hist = pl.DataFrame(
        {
            "family": np.full(N_LEAK_HIST, "LEAK_HIST", dtype="U16"),
            "acc_idx": l_acc,
            "op_ord": l_ords.astype(np.int32),
            "sec_of_day": rng.integers(25_200, 79_200, size=N_LEAK_HIST, dtype=np.int32),
            "amount_cents": l_amt,
            "signed_cents": -l_amt,
            "cp_key": np.full(N_LEAK_HIST, "NEOBANK", dtype="U12"),
            "label": np.array([NEOBANK_LABELS[b] for b in l_bic], dtype="U31"),
            "creditor_bic": l_bic.astype("U12"),
            "creditor_name": np.full(N_LEAK_HIST, "__SELF__", dtype="U40"),
            "creditor_iban": np.array([neobank_beneficiary_iban(int(a), str(b)) for a, b in zip(l_acc, l_bic)], dtype="U34"),
            "payment_scheme": np.full(N_LEAK_HIST, "SCT_INST", dtype="U16"),
            "cfonb_code_op": np.full(N_LEAK_HIST, op, dtype="U4"),
            "cfonb_afb": np.full(N_LEAK_HIST, afb, dtype="U2"),
        }
    ).sort(["op_ord", "acc_idx"]).with_columns(
        pl.concat_str([pl.lit("E2EHISTLEAK"), (pl.int_range(1, pl.len() + 1)).cast(pl.Utf8).str.zfill(8)]).alias("e2e_id"),
        pl.lit(True).alias("in_sepa"),
    )

    # ------------------------------------------------------------------ épargne programmée CC -> livret (58*)
    savings = accounts.filter(
        (pl.col("account_type") != "CC_CHQ") & (pl.col("opening_date") < "20250601")
    ).sort("acc_idx")
    sav_acc = savings["acc_idx"].to_numpy()
    sav_owner_cc = savings["cust_idx"].to_numpy()  # le compte courant d'un client a acc_idx = cust_idx
    order = rng.permutation(len(sav_acc))
    pairs: list[tuple[int, int, int, int]] = []  # (cc_acc, livret_acc, ord, cents)
    month_starts = months["m_start_ord"].to_list()
    for i in order:
        if len(pairs) >= N_INTERNAL_PAIRS:
            break
        if sav_owner_cc[i] == WITNESS_CUST_IDX:
            continue
        day = int(rng.integers(6, 11))
        cents = int(rng.integers(5, 51)) * 1_000  # 50 € .. 500 €, montant rond
        for ms in month_starts:
            o = ms + day - 1
            if o <= snap_ord and len(pairs) < N_INTERNAL_PAIRS:
                pairs.append((int(sav_owner_cc[i]), int(sav_acc[i]), o, cents))
    assert len(pairs) == N_INTERNAL_PAIRS
    pa = np.array(pairs, dtype=np.int64)
    e2e_int = np.array([f"E2EINT58TR{i:08d}" for i in range(1, N_INTERNAL_PAIRS + 1)], dtype="U36")
    n2 = 2 * N_INTERNAL_PAIRS
    internal = pl.DataFrame(
        {
            "family": np.full(n2, "INTERNAL_58", dtype="U16"),
            "acc_idx": np.concatenate([pa[:, 0], pa[:, 1]]).astype(np.int32),
            "op_ord": np.concatenate([pa[:, 2], pa[:, 2]]).astype(np.int32),
            "sec_of_day": np.full(n2, 30_000, dtype=np.int32),
            "amount_cents": np.concatenate([pa[:, 3], pa[:, 3]]),
            "signed_cents": np.concatenate([-pa[:, 3], pa[:, 3]]),
            "cp_key": np.full(n2, "INTERNAL", dtype="U12"),
            "label": np.concatenate(
                [np.full(N_INTERNAL_PAIRS, "VIR INTERNE 58 VERS LIVRET", dtype="U31"),
                 np.full(N_INTERNAL_PAIRS, "VIR INTERNE 58 DEPUIS CC", dtype="U31")]
            ),
            "creditor_bic": np.full(n2, "HEXAFRLPXXX", dtype="U12"),
            "creditor_name": np.full(n2, "", dtype="U40"),
            "creditor_iban": np.full(n2, "", dtype="U34"),
            "payment_scheme": np.full(n2, "INTERNAL", dtype="U16"),
            "cfonb_code_op": np.full(n2, "0580", dtype="U4"),
            "cfonb_afb": np.concatenate([np.full(N_INTERNAL_PAIRS, "16", dtype="U2"), np.full(N_INTERNAL_PAIRS, "05", dtype="U2")]),
            "e2e_id": np.concatenate([e2e_int, e2e_int]),
            "in_sepa": np.zeros(n2, dtype=bool),
        }
    )

    ledger = pl.concat([regular, leak_hist, internal], how="diagonal_relaxed")
    ledger = ledger.with_columns(
        pl.Series("op_date", _ord_to_str(ledger["op_ord"].to_numpy().astype(np.int64))),
    ).join(
        accounts.select("acc_idx", "in_mainframe"), on="acc_idx", how="left"
    )

    # Contrôles des volumes
    n_sepa = ledger.filter(pl.col("in_sepa")).height
    n_mf = ledger.filter(pl.col("in_mainframe")).height
    assert n_sepa == N_REGULAR_SEPA + N_LEAK_HIST, n_sepa
    assert n_mf + N_WITNESS_OPS + N_LEAK_90D == CFONB_TOTAL_MOVEMENTS, n_mf
    assert ledger.filter(pl.col("in_sepa"))["e2e_id"].n_unique() == n_sepa
    return ledger


def build_or_load_ledger(force_rebuild: bool = False) -> pl.DataFrame:
    if LEDGER_PATH.exists() and not force_rebuild:
        return pl.read_parquet(LEDGER_PATH)
    ledger = build_customer_ledger(build_or_load_universe())
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_parquet(LEDGER_PATH)
    return ledger


if __name__ == "__main__":
    led = build_or_load_ledger(force_rebuild=True)
    print(led.group_by("family").agg(pl.len(), (pl.col("amount_cents").mean() / 100).round(2).alias("avg_eur")).sort("family"))
    print("SEPA:", led.filter(pl.col("in_sepa")).height, "| Mainframe:", led.filter(pl.col("in_mainframe")).height)
