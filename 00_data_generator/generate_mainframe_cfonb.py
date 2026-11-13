"""
Générateur déterministe (seed=2026) des fichiers Core Banking Mainframe z/OS
pour Paris Data Summit 2026 (Banque Hexagone) — Version « Dirty Mainframe » pour Spark -> BigLake Iceberg.

Produit dans `00_data_generator/output/corebanking/` :
1. Copybooks COBOL (.cpy) + bordereau JCL `MANIFEST_Z_OS_DROP.ctl`
2. `CBK_CUSTOMERS_REF_20261112.ebcdic` :
   Flux binaire continu RECFM=FB (sans '\\n'), LRECL=140 octets, EBCDIC CP500 + COMP-3,
   encadré par des blocs CFT '00CFT_HDR' / '99CFT_TRL' (79 350 clients Mainframe).
3. `CBK_ACCOUNTS_MSTR_20261112.ebcdic` :
   Flux binaire continu RECFM=FB (sans '\\n'), LRECL=150 octets, EBCDIC CP500 + COMP-3
   sur le taux et le solde veille, encadré par '00CFT_HDR' / '99CFT_TRL' (94 350 comptes).
4. Relevés multi-lignes CFONB 120 (`00` CFT, `01` solde init, `04` mouvement + `05` complément SEPA
   portant le BIC et l'EndToEndId liés uniquement par ordre physique, `07` solde fin, `99` CFT) :
   - `CFONB120_MVTS_202506.cfonb.gz` .. `202512.cfonb.gz` (historique 2025 compressé gzip)
   - `CFONB120_MVTS_202601.cfonb` .. `202611.cfonb` (2026 en clair ISO-8859-15)
   - Piège d'exploitation sur octobre 2026 :
     * `CFONB120_MVTS_202610_RUN01.cfonb` (interrompu à mi-parcours, trailer `STATUS=ABEND_S0C7 RC=0012`)
     * `CFONB120_MVTS_202610_RUN02_RERUN.cfonb` (complet, trailer `STATUS=OK RC=0000`)
"""

from __future__ import annotations

import calendar
import gzip
import shutil
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from shared_universe import (
    BANK_BIC,
    BANK_CODE,
    BASE_DIR,
    DEMO_SEED,
    HISTORY_START_DATE,
    NEOBANK_DESTINATIONS,
    SNAPSHOT_DATE,
    WITNESS_ACC_ID,
    WITNESS_CUST_IDX,
    build_or_load_universe,
)

OUTPUT_DIR: Path = BASE_DIR / "output" / "corebanking"
COPYBOOKS_SRC_DIR: Path = BASE_DIR / "copybooks"

TARGET_TOTAL_MOVEMENTS_04: int = 5_500_000
CORRUPT_VALUE_DATE_COUNT: int = 66_000  # Exactement 1,2000 % de 5 500 000
EBCDIC_ENCODING: str = "cp500"

CFONB_SIGN_MAP: list[str] = list("{ABCDEFGHI}JKLMNOPQR")

MONTHS_18: list[tuple[int, int, str, str, str]] = []
for _y, _m in [(2025, m) for m in range(6, 13)] + [(2026, m) for m in range(1, 12)]:
    _ym = f"{_y:04d}{_m:02d}"
    _start = f"{_y:04d}{_m:02d}01"
    if (_y, _m) == (2026, 11):
        _end = SNAPSHOT_DATE.strftime("%Y%m%d")
    else:
        _last_d = calendar.monthrange(_y, _m)[1]
        _end = f"{_y:04d}{_m:02d}{_last_d:02d}"
    MONTHS_18.append((_y, _m, _ym, _start, _end))


def pack_comp3(val: int, num_digits: int) -> bytes:
    """Encode un entier signé en binaire Mainframe Packed Decimal (COMP-3)."""
    sign_nibble = "c" if val >= 0 else "d"
    return bytes.fromhex(f"{abs(int(val)):0{num_digits}d}{sign_nibble}")


def encode_cfonb_signed_expr(cents_col: str) -> pl.Expr:
    """Expression Polars vectorisée encodant un montant int64 (centimes) sur 14 car. CFONB."""
    c = pl.col(cents_col)
    abs_c = c.abs()
    prefix_13 = (abs_c // 10).cast(pl.String).str.zfill(13)
    sign_idx = pl.when(c >= 0).then(abs_c % 10).otherwise(10 + (abs_c % 10))
    sign_char = sign_idx.cast(pl.String).replace_strict(
        {str(i): ch for i, ch in enumerate(CFONB_SIGN_MAP)},
        return_dtype=pl.String,
    )
    return pl.concat_str([prefix_13, sign_char])


def corrupt_agency_codes(
    codes_4: np.ndarray,
    codes_5: np.ndarray,
    rng: np.random.Generator,
    protect_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Injecte les anomalies legacy Mainframe sur les codes agences (4 car.) et guichets (5 car.) :
    - ~11,5 % cadrés à gauche sans zéros de tête ('42  ' vs '0042', '42   ' vs '00042')
    - ~0,6 % blancs ('    ' / '     ')
    """
    n = len(codes_4)
    out_4 = codes_4.astype("U4").copy()
    out_5 = codes_5.astype("U5").copy()

    u = rng.random(n)
    if protect_mask is not None:
        u = np.where(protect_mask, 1.0, u)

    left_pad_idx = np.flatnonzero(u < 0.115)
    blank_idx = np.flatnonzero((u >= 0.115) & (u < 0.121))

    for i in left_pad_idx:
        num_str = str(int(out_4[i]))
        out_4[i] = num_str.ljust(4)
        out_5[i] = num_str.ljust(5)

    out_4[blank_idx] = "    "
    out_5[blank_idx] = "     "
    return out_4, out_5


def build_witness_movements(guichet_5: str) -> dict[str, np.ndarray]:
    """Construit l'historique sur 18 mois de Lucas Martin (CUST00002026 / ACC00002026)."""
    rows: list[tuple[str, str, str, int, str, str, str]] = []
    seq = 1
    for y, m, ym, _, _ in MONTHS_18:
        if (y, m) < (2026, 11):
            ops = [
                (f"{ym}01", "0420", "05", +185_000, "VIR SALAIRE TECHCORP SAS", "EMPLOYEURFR", f"E2EWIT{seq:07d}"),
                (f"{ym}05", "0650", "08", -72_000, "PRLV LOYER FONCIERE PARIS", "MANDATLOYER", f"E2EWIT{seq+1:07d}"),
                (f"{ym}08", "0650", "08", -1_599, "PRLV SEPA STRMFLIX ABO", "STRMFLIXEUR", f"E2EWIT{seq+2:07d}"),
                (f"{ym}11", "0310", "28", -15_000, "CB CARREFOUR CITY PARIS", "CARTEVISA42", ""),
                (f"{ym}12", "0650", "08", -6_401, "PRLV EDF ENERGIE", "EDFPROXIMIT", f"E2EWIT{seq+3:07d}"),
                (f"{ym}18", "0310", "28", -22_000, "CB MONOPRIX OPERA PARIS", "CARTEVISA42", ""),
                (f"{ym}24", "0310", "28", -19_000, "CB FNAC SAINT LAZARE", "CARTEVISA42", ""),
                (f"{ym}28", "0310", "28", -22_800, "CB SNCF VOYAGES", "CARTEVISA42", ""),
            ]
            seq += 4
        else:
            ops = [
                ("20261101", "0420", "05", +185_000, "VIR SALAIRE TECHCORP SAS", "EMPLOYEURFR", f"E2EWIT{seq:07d}"),
                ("20261105", "0650", "08", -72_000, "PRLV LOYER FONCIERE PARIS", "MANDATLOYER", f"E2EWIT{seq+1:07d}"),
                ("20261108", "0650", "08", -1_999, "PRLV SEPA STRMFLIX ABO", "STRMFLIXEUR", f"E2EWIT{seq+2:07d}"),
                ("20261110", "0430", "05", +4_200, "VIR CPAM REMBOURSEMENT SANTE", "CPAMIDF7500", f"E2EWIT{seq+3:07d}"),
                ("20261111", "0310", "28", -15_000, "CB CARREFOUR CITY PARIS", "CARTEVISA42", ""),
                ("20261112", "0650", "08", -6_401, "PRLV EDF ENERGIE", "EDFPROXIMIT", f"E2EWIT{seq+4:07d}"),
            ]
            seq += 5
        rows.extend(ops)

    n = len(rows)
    return {
        "acc_idx": np.full(n, WITNESS_CUST_IDX, dtype=np.int32),
        "code_op_interne": np.array([r[1] for r in rows], dtype="U4"),
        "code_afb": np.array([r[2] for r in rows], dtype="U2"),
        "guichet_5": np.full(n, guichet_5, dtype="U5"),
        "date_compta": np.array([r[0] for r in rows], dtype="U8"),
        "signed_cents": np.array([r[3] for r in rows], dtype=np.int64),
        "libelle": np.array([r[4] for r in rows], dtype="U31"),
        "ref_bic": np.array([r[5] for r in rows], dtype="U12"),
        "e2e_id": np.array([r[6] for r in rows], dtype="U36"),
        "is_protected": np.ones(n, dtype=bool),
    }


def generate_all_movements_04(
    universe: dict[str, pl.DataFrame],
    rng: np.random.Generator,
) -> pl.DataFrame:
    """Génère les 5 500 000 mouvements '04' (et leurs attributs SEPA pour les lignes '05')."""
    accounts_df = universe["accounts"]
    leak_90d_df = universe["leak_events_90d"]

    acc_agencies_4 = accounts_df["agency_code_4"].to_numpy()
    acc_guichets = accounts_df["guichet_code_5"].to_numpy()
    acc_num_11 = accounts_df["num_compte_11"].to_numpy()
    acc_open_dates = accounts_df["opening_date"].to_numpy()
    acc_cust_idx = accounts_df["cust_idx"].to_numpy()
    acc_in_mf = accounts_df["in_mainframe"].to_numpy()
    acc_types = accounts_df["account_type"].to_numpy()

    ord_start = HISTORY_START_DATE.toordinal()
    ord_end = SNAPSHOT_DATE.toordinal()
    ord_lookup = np.array(
        [(HISTORY_START_DATE + timedelta(days=i)).strftime("%Y%m%d") for i in range(ord_end - ord_start + 5)],
        dtype="U8",
    )
    acc_min_ord = np.array(
        [max(ord_start, date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal()) for d in acc_open_dates],
        dtype=np.int32,
    )

    # 1. Client témoin Démo #4
    w_dict = build_witness_movements(str(acc_guichets[WITNESS_CUST_IDX - 1]))
    n_witness = len(w_dict["acc_idx"])

    # 2. Fuites néobanques 90j (200 000 lignes = -2 420 000 000,00 €)
    n_leak_90d = leak_90d_df.height
    leak_acc_idx = leak_90d_df["acc_idx"].to_numpy().astype(np.int32)
    leak_dict = {
        "acc_idx": leak_acc_idx,
        "code_op_interne": np.full(n_leak_90d, "0810", dtype="U4"),
        "code_afb": np.full(n_leak_90d, "16", dtype="U2"),
        "guichet_5": leak_90d_df["guichet_code_5"].to_numpy().astype("U5"),
        "date_compta": leak_90d_df["accounting_date"].to_numpy().astype("U8"),
        "signed_cents": -leak_90d_df["amount_cents"].to_numpy().astype(np.int64),
        "libelle": leak_90d_df["libelle"].to_numpy().astype("U31"),
        "ref_bic": leak_90d_df["neobank_bic"].to_numpy().astype("U12"),
        "e2e_id": leak_90d_df["end_to_end_id"].to_numpy().astype("U36"),
        "is_protected": leak_acc_idx == WITNESS_CUST_IDX,
    }

    # 3. Fuites néobanques historiques avant trimestre [2025-06-01 .. 2026-08-12]
    n_leak_hist = 100_000
    pre_cc_pool = np.array([i for i in range(1, 62_001) if i != WITNESS_CUST_IDX], dtype=np.int32)
    hist_leak_acc = rng.choice(pre_cc_pool, size=n_leak_hist, replace=True)
    aug12_ord = date(2026, 8, 12).toordinal()
    hist_leak_ords = rng.integers(ord_start, aug12_ord + 1, size=n_leak_hist)
    hist_neo_choice = rng.choice(len(NEOBANK_DESTINATIONS), size=n_leak_hist, p=[0.40, 0.30, 0.14, 0.10, 0.06])
    hist_leak_cents = -rng.integers(15_000, 380_000, size=n_leak_hist, dtype=np.int64)
    leak_hist_dict = {
        "acc_idx": hist_leak_acc,
        "code_op_interne": np.full(n_leak_hist, "0810", dtype="U4"),
        "code_afb": np.full(n_leak_hist, "16", dtype="U2"),
        "guichet_5": acc_guichets[hist_leak_acc - 1],
        "date_compta": ord_lookup[hist_leak_ords - ord_start],
        "signed_cents": hist_leak_cents,
        "libelle": np.array([NEOBANK_DESTINATIONS[i][1] for i in hist_neo_choice], dtype="U31"),
        "ref_bic": np.array([NEOBANK_DESTINATIONS[i][0] for i in hist_neo_choice], dtype="U12"),
        "e2e_id": np.array([f"E2EHISTLEAK{i:08d}" for i in range(1, n_leak_hist + 1)], dtype="U36"),
        "is_protected": np.zeros(n_leak_hist, dtype=bool),
    }

    # 4. Virements internes Compte-à-Livret 58* (190 000 paires = 380 000 écritures '04')
    n_int_pairs = 190_000
    hist_sav_pool = np.arange(80_001, 92_001, dtype=np.int32)
    sav_chosen = rng.choice(hist_sav_pool, size=n_int_pairs, replace=True)
    cc_paired = acc_cust_idx[sav_chosen - 1]
    int_ords = rng.integers(ord_start, ord_end + 1, size=n_int_pairs)
    int_dates = ord_lookup[int_ords - ord_start]
    int_amounts = rng.integers(10_000, 250_000, size=n_int_pairs, dtype=np.int64)
    int_e2e = np.array([f"E2EINT58TR{i:08d}" for i in range(1, n_int_pairs + 1)], dtype="U36")

    internal_dict = {
        "acc_idx": np.concatenate([cc_paired, sav_chosen]),
        "code_op_interne": np.full(2 * n_int_pairs, "0580", dtype="U4"),
        "code_afb": np.concatenate(
            [np.full(n_int_pairs, "16", dtype="U2"), np.full(n_int_pairs, "05", dtype="U2")]
        ),
        "guichet_5": np.concatenate([acc_guichets[cc_paired - 1], acc_guichets[sav_chosen - 1]]),
        "date_compta": np.concatenate([int_dates, int_dates]),
        "signed_cents": np.concatenate([-int_amounts, +int_amounts]),
        "libelle": np.concatenate(
            [
                np.full(n_int_pairs, "VIR INTERNE 58 VERS LIVRET", dtype="U31"),
                np.full(n_int_pairs, "VIR INTERNE 58 DEPUIS CC", dtype="U31"),
            ]
        ),
        "ref_bic": np.full(2 * n_int_pairs, BANK_BIC, dtype="U12"),
        "e2e_id": np.concatenate([int_e2e, int_e2e]),
        "is_protected": np.zeros(2 * n_int_pairs, dtype=bool),
    }

    # 5. Opérations courantes
    used_rows = n_witness + n_leak_90d + n_leak_hist + (2 * n_int_pairs)
    rem_rows = TARGET_TOTAL_MOVEMENTS_04 - used_rows
    n_sal = 1_150_000
    n_remb = 150_000
    n_prlv = 1_100_000
    n_cb = rem_rows - (n_sal + n_remb + n_prlv)

    mf_cc_all = (
        np.flatnonzero(acc_in_mf & (acc_types == "CC_CHQ") & (np.arange(len(acc_in_mf)) != WITNESS_CUST_IDX - 1))
        + 1
    )
    mf_cc_pre = np.array([i for i in range(1, 62_001) if i != WITNESS_CUST_IDX], dtype=np.int32)

    def _sample_dates_after_open(chosen_acc_idx: np.ndarray) -> np.ndarray:
        mins = acc_min_ord[chosen_acc_idx - 1]
        ords = rng.integers(mins, ord_end + 1)
        return ord_lookup[ords - ord_start]

    sal_acc = rng.choice(mf_cc_all, size=n_sal, replace=True)
    sal_dates = _sample_dates_after_open(sal_acc)
    sal_cents = rng.integers(145_000, 680_000, size=n_sal, dtype=np.int64)
    sal_labels = rng.choice(
        [
            "VIR SEPA SALAIRE ENTREPRISE",
            "VIR PAIE MENSUELLE DRH",
            "VIR REVENUS ACTIVITE PRO",
            "VIR CAISSE RETRAITE",
        ],
        size=n_sal,
    ).astype("U31")

    remb_acc = rng.choice(mf_cc_all, size=n_remb, replace=True)
    remb_dates = _sample_dates_after_open(remb_acc)
    remb_cents = rng.integers(1_800, 42_000, size=n_remb, dtype=np.int64)
    remb_labels = rng.choice(
        [
            "VIR CPAM REMBOURSEMENT SANTE",
            "VIR MUTUELLE COMPLEMENTAIRE",
            "VIR REMBOURSEMENT FRAIS",
        ],
        size=n_remb,
    ).astype("U31")

    prlv_acc = rng.choice(mf_cc_pre, size=n_prlv, replace=True)
    prlv_dates = _sample_dates_after_open(prlv_acc)
    prlv_cents = -rng.integers(1_299, 115_000, size=n_prlv, dtype=np.int64)
    prlv_labels = rng.choice(
        [
            "PRLV SEPA EDF ENERGIE",
            "PRLV SEPA LOYER HABITAT",
            "PRLV SEPA ORANGE FIBRE",
            "PRLV SEPA IMPOTS DGFIP",
            "PRLV SEPA ASSURANCE AUTO",
            "PRLV SEPA STRMFLIX ABO",
        ],
        size=n_prlv,
    ).astype("U31")

    cb_acc = rng.choice(mf_cc_pre, size=n_cb, replace=True)
    cb_dates = _sample_dates_after_open(cb_acc)
    cb_cents = -rng.integers(450, 28_500, size=n_cb, dtype=np.int64)
    cb_labels = rng.choice(
        [
            "CB CARREFOUR HYPER",
            "CB LECLERC DISTRIBUTION",
            "CB SNCF VOYAGES",
            "CB PHARMACIE CENTRALE",
            "CB BOULANGERIE ARTISANALE",
            "CB TOTALENERGIES STATION",
            "CB AMAZON EU SARL",
            "CB RESTAURANT BRASSERIE",
        ],
        size=n_cb,
    ).astype("U31")

    chunks = [
        w_dict,
        leak_dict,
        leak_hist_dict,
        internal_dict,
        {
            "acc_idx": sal_acc,
            "code_op_interne": np.full(n_sal, "0420", dtype="U4"),
            "code_afb": np.full(n_sal, "05", dtype="U2"),
            "guichet_5": acc_guichets[sal_acc - 1],
            "date_compta": sal_dates,
            "signed_cents": sal_cents,
            "libelle": sal_labels,
            "ref_bic": np.full(n_sal, "EMPLOYEURFR", dtype="U12"),
            "e2e_id": np.full(n_sal, "E2ESEPASALAIREBATCH", dtype="U36"),
            "is_protected": np.zeros(n_sal, dtype=bool),
        },
        {
            "acc_idx": remb_acc,
            "code_op_interne": np.full(n_remb, "0430", dtype="U4"),
            "code_afb": np.full(n_remb, "05", dtype="U2"),
            "guichet_5": acc_guichets[remb_acc - 1],
            "date_compta": remb_dates,
            "signed_cents": remb_cents,
            "libelle": remb_labels,
            "ref_bic": np.full(n_remb, "CPAMFRANCE0", dtype="U12"),
            "e2e_id": np.full(n_remb, "E2ESEPAREMBSANTE", dtype="U36"),
            "is_protected": np.zeros(n_remb, dtype=bool),
        },
        {
            "acc_idx": prlv_acc,
            "code_op_interne": np.full(n_prlv, "0650", dtype="U4"),
            "code_afb": np.full(n_prlv, "08", dtype="U2"),
            "guichet_5": acc_guichets[prlv_acc - 1],
            "date_compta": prlv_dates,
            "signed_cents": prlv_cents,
            "libelle": prlv_labels,
            "ref_bic": np.full(n_prlv, "MANDATSEPA0", dtype="U12"),
            "e2e_id": np.full(n_prlv, "E2ESEPAMANDATPRLV", dtype="U36"),
            "is_protected": np.zeros(n_prlv, dtype=bool),
        },
        {
            "acc_idx": cb_acc,
            "code_op_interne": np.full(n_cb, "0310", dtype="U4"),
            "code_afb": np.full(n_cb, "28", dtype="U2"),
            "guichet_5": acc_guichets[cb_acc - 1],
            "date_compta": cb_dates,
            "signed_cents": cb_cents,
            "libelle": cb_labels,
            "ref_bic": np.full(n_cb, "", dtype="U12"),
            "e2e_id": np.full(n_cb, "", dtype="U36"),
            "is_protected": np.zeros(n_cb, dtype=bool),
        },
    ]

    all_acc_idx = np.concatenate([c["acc_idx"] for c in chunks]).astype(np.int32)
    all_op_int = np.concatenate([c["code_op_interne"] for c in chunks])
    all_afb = np.concatenate([c["code_afb"] for c in chunks])
    all_guichet = np.concatenate([c["guichet_5"] for c in chunks])
    all_date_compta = np.concatenate([c["date_compta"] for c in chunks])
    all_signed_cents = np.concatenate([c["signed_cents"] for c in chunks])
    all_libelle = np.concatenate([c["libelle"] for c in chunks])
    all_ref_bic = np.concatenate([c["ref_bic"] for c in chunks])
    all_e2e_id = np.concatenate([c["e2e_id"] for c in chunks])
    all_protected = np.concatenate([c["is_protected"] for c in chunks])

    assert len(all_acc_idx) == TARGET_TOTAL_MOVEMENTS_04

    # Anomalie RAW #1 : codes guichets non normalisés ('42   ' / '     ')
    _, noisy_guichet_5 = corrupt_agency_codes(
        acc_agencies_4[all_acc_idx - 1], all_guichet, rng, protect_mask=all_protected
    )

    # Anomalie RAW #2 : exactement 66 000 lignes (1,20 %) avec DATE_VALEUR = '00000000' / '99999999'
    all_date_valeur = all_date_compta.astype("U8").copy()
    eligible_corrupt = np.flatnonzero(~all_protected)
    chosen_corrupt = rng.choice(eligible_corrupt, size=CORRUPT_VALUE_DATE_COUNT, replace=False)
    n_zeros = 41_250
    all_date_valeur[chosen_corrupt[:n_zeros]] = "00000000"
    all_date_valeur[chosen_corrupt[n_zeros:]] = "99999999"

    mvts_df = pl.DataFrame(
        {
            "acc_idx": all_acc_idx,
            "num_compte_11": acc_num_11[all_acc_idx - 1],
            "code_op_interne": all_op_int,
            "code_guichet_raw": noisy_guichet_5,
            "code_afb": all_afb,
            "date_compta": all_date_compta,
            "date_valeur": all_date_valeur,
            "libelle": all_libelle,
            "signed_cents": all_signed_cents,
            "ref_bic": all_ref_bic,
            "e2e_id": all_e2e_id,
        }
    ).with_columns(pl.col("date_compta").str.slice(0, 6).alias("ym"))
    return mvts_df


def make_cft_header_120(ym: str, run_no: int, enc_label: str) -> str:
    hdr = f"00CFT_HDR BANQUE_HEXAGONE ZOS_JCBK2345 PERIOD={ym} RUN={run_no:02d} ENCODING={enc_label}"
    return hdr.ljust(120, " ")[:120]


def make_cft_trailer_120(status: str, rc: str, data_records: int, mvt_04_count: int, extra: str = "") -> str:
    trl = (
        f"99CFT_TRL STATUS={status:<10s} RC={rc} "
        f"DATA_RECORDS={data_records:09d} CHECKSUM_MVTS_04={mvt_04_count:09d} {extra}"
    )
    return trl.ljust(120, " ")[:120]


def write_cfonb_file(
    body_df: pl.DataFrame,
    out_path: Path,
    hdr_120: str,
    trl_120: str,
    compress_gzip: bool,
) -> int:
    """Écrit un fichier CFONB 120 octets encadré par ses bannières 00CFT_HDR / 99CFT_TRL."""
    widths = body_df.select(
        pl.col("raw_line").str.len_bytes().min().alias("min_w"),
        pl.col("raw_line").str.len_bytes().max().alias("max_w"),
    ).row(0)
    if widths != (120, 120):
        raise AssertionError(f"Largeur CFONB invalide sur {out_path.name}: {widths}")
    assert len(hdr_120) == 120 and len(trl_120) == 120

    full_df = pl.concat(
        [
            pl.DataFrame({"raw_line": [hdr_120]}),
            body_df.select("raw_line"),
            pl.DataFrame({"raw_line": [trl_120]}),
        ]
    )
    payload_bytes = ("\n".join(full_df["raw_line"].to_list()) + "\n").encode("iso-8859-15")
    if compress_gzip:
        with gzip.open(out_path, "wb", compresslevel=1) as gz:
            gz.write(payload_bytes)
    else:
        out_path.write_bytes(payload_bytes)
    return full_df.height


def write_ebcdic_customers_master(
    mf_customers: pl.DataFrame,
    ag4_noisy: np.ndarray,
    gu5_noisy: np.ndarray,
    out_path: Path,
) -> int:
    """
    Écrit `CBK_CUSTOMERS_REF_20261112.ebcdic` en flux binaire continu RECFM=FB (LRECL=140, sans '\\n') :
    - 1er bloc 140B : 00CFT_HDR en EBCDIC CP500
    - 79 350 blocs  : EBCDIC CP500 + AGE en binaire COMP-3 (octets 34..35, 0-index 33:35)
    - Dernier bloc  : 99CFT_TRL STATUS=OK RC=0000 en EBCDIC CP500
    """
    n = mf_customers.height
    buf = bytearray()

    hdr = "00CFT_HDR DS=CBK.CUSTOMERS.REF DATE=20261112 RECFM=FB LRECL=0140 ENC=EBCDIC_CP500_COMP3".ljust(140)
    buf.extend(hdr.encode(EBCDIC_ENCODING))

    cust_ids = mf_customers["customer_id"].to_list()
    regions = mf_customers["region_code"].to_list()
    b_dates = mf_customers["birth_date"].to_list()
    ages = mf_customers["age"].to_list()
    segs = mf_customers["segment"].to_list()
    onb_dates = mf_customers["onboarding_date"].to_list()
    clo_dates = mf_customers["closure_date"].to_list()
    statuses = mf_customers["status"].to_list()
    lnames = mf_customers["last_name"].to_list()
    fnames = mf_customers["first_name"].to_list()
    csps = mf_customers["csp"].to_list()
    snap_str = SNAPSHOT_DATE.strftime("%Y%m%d")

    for i in range(n):
        part1 = (
            f"{cust_ids[i]:<12s}"
            f"{str(ag4_noisy[i]):<4s}"
            f"{str(gu5_noisy[i]):<5s}"
            f"{regions[i]:<4s}"
            f"{b_dates[i]:<8s}"
        ).encode(EBCDIC_ENCODING)
        age_comp3 = pack_comp3(int(ages[i]), 3)  # 2 octets
        part2 = (
            f"{segs[i]:<12.12s}"
            f"{onb_dates[i]:<8s}"
            f"{clo_dates[i]:<8s}"
            f"{statuses[i]:<6.6s}"
            f"{lnames[i]:<26.26s}"
            f"{fnames[i]:<20.20s}"
            f"{csps[i]:<10.10s}"
            f"{snap_str}"
            f"{'':<7s}"
        ).encode(EBCDIC_ENCODING)
        rec = part1 + age_comp3 + part2
        if len(rec) != 140:
            raise AssertionError(f"Longueur client EBCDIC invalide: {len(rec)}")
        buf.extend(rec)

    trl = f"99CFT_TRL STATUS=OK RC=0000 DATA_RECORDS={n:09d} LRECL=0140".ljust(140)
    buf.extend(trl.encode(EBCDIC_ENCODING))

    assert len(buf) == (n + 2) * 140
    out_path.write_bytes(bytes(buf))
    return n


def write_ebcdic_accounts_master(
    mf_acc_joined: pl.DataFrame,
    ag4_noisy: np.ndarray,
    gu5_noisy: np.ndarray,
    out_path: Path,
) -> int:
    """
    Écrit `CBK_ACCOUNTS_MSTR_20261112.ebcdic` en flux binaire continu RECFM=FB (LRECL=150, sans '\\n') :
    - 1er bloc 150B : 00CFT_HDR en EBCDIC CP500
    - 94 350 blocs  : EBCDIC CP500 + TAUX (3B COMP-3, pos 113..115) + SOLDE_VEILLE (8B COMP-3, pos 116..123)
    - Dernier bloc  : 99CFT_TRL STATUS=OK RC=0000 en EBCDIC CP500
    """
    n = mf_acc_joined.height
    buf = bytearray()

    hdr = "00CFT_HDR DS=CBK.ACCOUNTS.MSTR DATE=20261112 RECFM=FB LRECL=0150 ENC=EBCDIC_CP500_COMP3".ljust(150)
    buf.extend(hdr.encode(EBCDIC_ENCODING))

    acc_ids = mf_acc_joined["account_id"].to_list()
    nums_11 = mf_acc_joined["num_compte_11"].to_list()
    cust_ids = mf_acc_joined["customer_id"].to_list()
    cles = mf_acc_joined["cle_rib"].to_list()
    ibans = mf_acc_joined["iban"].to_list()
    types = mf_acc_joined["account_type"].to_list()
    opens = mf_acc_joined["opening_date"].to_list()
    closes = mf_acc_joined["closure_date"].to_list()
    statuses = mf_acc_joined["status"].to_list()
    rates = mf_acc_joined["rate_bps"].to_list()
    bals = mf_acc_joined["final_balance_cents"].to_list()
    last_mvts = mf_acc_joined["eff_last_mvt_date"].to_list()
    labels = mf_acc_joined["product_label"].to_list()

    for i in range(n):
        part1 = (
            f"{acc_ids[i]:<11s}"
            f"{nums_11[i]:<11s}"
            f"{cust_ids[i]:<12s}"
            f"{BANK_CODE}"
            f"{str(ag4_noisy[i]):<4s}"
            f"{str(gu5_noisy[i]):<5s}"
            f"{cles[i]:<2s}"
            f"{ibans[i]:<27s}"
            f"{types[i]:<10.10s}"
            f"EUR"
            f"{opens[i]:<8s}"
            f"{closes[i]:<8s}"
            f"{statuses[i]:<6.6s}"
        ).encode(EBCDIC_ENCODING)
        rate_comp3 = pack_comp3(int(rates[i]), 5)     # 3 octets (pos 113..115)
        solde_comp3 = pack_comp3(int(bals[i]), 15)    # 8 octets (pos 116..123)
        part2 = (
            f"{last_mvts[i]:<8s}"
            f"{labels[i]:<19.19s}"
        ).encode(EBCDIC_ENCODING)
        rec = part1 + rate_comp3 + solde_comp3 + part2
        if len(rec) != 150:
            raise AssertionError(f"Longueur compte EBCDIC invalide: {len(rec)}")
        buf.extend(rec)

    trl = f"99CFT_TRL STATUS=OK RC=0000 DATA_RECORDS={n:09d} LRECL=0150".ljust(150)
    buf.extend(trl.encode(EBCDIC_ENCODING))

    assert len(buf) == (n + 2) * 150
    out_path.write_bytes(bytes(buf))
    return n


def generate_corebanking_files() -> None:
    t0 = time.perf_counter()
    print("[1/5] Construction / chargement de l'univers déterministe (seed=2026)...")
    universe = build_or_load_universe(force_rebuild=False)
    rng = np.random.default_rng(DEMO_SEED + 101)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_cpy_dir = OUTPUT_DIR / "copybooks"
    out_cpy_dir.mkdir(parents=True, exist_ok=True)
    for cpy_file in COPYBOOKS_SRC_DIR.glob("*.cpy"):
        shutil.copy2(cpy_file, out_cpy_dir / cpy_file.name)

    # ------------------------------------------------------------------
    # [2/5] Génération des 5 500 000 d'écritures '04' (+ attributs SEPA '05')
    # ------------------------------------------------------------------
    print("[2/5] Génération vectorisée des 5 500 000 mouvements CFONB '04' + compléments '05'...")
    mvts_df = generate_all_movements_04(universe, rng)

    # ------------------------------------------------------------------
    # [3/5] Calcul exact de la chaîne des soldes mensuels ('01' -> '04' -> '07')
    # ------------------------------------------------------------------
    print("[3/5] Calcul et réconciliation au centime des soldes '01' / '07' sur 18 mois...")
    mf_accounts = universe["accounts"].filter(pl.col("in_mainframe")).sort("acc_idx")
    n_mf_acc = mf_accounts.height

    monthly_net = mvts_df.group_by(["acc_idx", "ym"]).agg(
        pl.col("signed_cents").sum().alias("net_cents"),
    )

    ym_list = [m[2] for m in MONTHS_18]
    grid = (
        mf_accounts.select("acc_idx", "num_compte_11", "guichet_code_5", "opening_date", "account_type")
        .join(pl.DataFrame({"ym": ym_list}), how="cross")
        .join(monthly_net, on=["acc_idx", "ym"], how="left")
        .with_columns(pl.col("net_cents").fill_null(0))
        .sort(["acc_idx", "ym"])
    )

    min_cum_per_acc = (
        grid.with_columns(pl.col("net_cents").cum_sum().over("acc_idx").alias("cum_net"))
        .group_by("acc_idx")
        .agg(pl.col("cum_net").min().alias("min_cum"))
        .sort("acc_idx")
    )

    open_dates_mf = mf_accounts["opening_date"].to_numpy()
    acc_idx_mf = mf_accounts["acc_idx"].to_numpy()
    acc_types_mf = mf_accounts["account_type"].to_numpy()
    min_cums = min_cum_per_acc["min_cum"].to_numpy()

    cushions = np.where(
        acc_types_mf == "CC_CHQ",
        rng.integers(120_000, 1_850_000, size=n_mf_acc, dtype=np.int64),
        rng.integers(350_000, 2_295_000, size=n_mf_acc, dtype=np.int64),
    )
    init_balances = np.where(open_dates_mf <= "20250531", np.maximum(0, -min_cums) + cushions, 0)
    witness_pos = int(np.flatnonzero(acc_idx_mf == WITNESS_CUST_IDX)[0])
    init_balances[witness_pos] = 240_000

    init_df = pl.DataFrame({"acc_idx": acc_idx_mf, "init_202506_cents": init_balances})
    balances_grid = (
        grid.join(init_df, on="acc_idx", how="left")
        .with_columns(pl.col("net_cents").cum_sum().over("acc_idx").alias("cum_net"))
        .with_columns((pl.col("init_202506_cents") + pl.col("cum_net")).alias("closing_07_cents"))
        .with_columns((pl.col("closing_07_cents") - pl.col("net_cents")).alias("opening_01_cents"))
    )

    # ------------------------------------------------------------------
    # [4/5] Écriture des fichiers CFONB 120 (.cfonb.gz 2025, .cfonb 2026 + piège ABEND 202610)
    # ------------------------------------------------------------------
    print("[4/5] Écriture des fichiers multi-lignes CFONB 120 (01/04/05/07 + CFT + ABEND 202610)...")
    total_valid_lines = 0
    total_04_written = 0
    total_05_written = 0

    motif_map = {
        "0810": "TRANSFERT SEPA INSTANTANE",
        "0580": "VIREMENT EPARGNE INTERNE ",
        "0420": "VIREMENT SEPA SALAIRE/REV",
        "0430": "VIREMENT SEPA TIERS/SANTE",
        "0650": "PRELEVEMENT MANDAT SEPA  ",
    }

    for y, _, ym, ym_start, ym_end in MONTHS_18:
        bal_m = (
            balances_grid.filter(pl.col("ym") == ym)
            .filter(pl.col("opening_date") <= ym_end)
            .with_columns(
                pl.when(pl.col("opening_date") > ym_start)
                .then(pl.col("opening_date"))
                .otherwise(pl.lit(ym_start))
                .alias("date_solde_01"),
                pl.lit(ym_end).alias("date_solde_07"),
            )
        )

        df_01 = bal_m.select(
            pl.col("acc_idx"),
            pl.lit(0, dtype=pl.Int32).alias("ord_type"),
            pl.col("date_solde_01").alias("sort_date"),
            pl.lit(0, dtype=pl.Int64).alias("mvt_row_id"),
            pl.lit(0, dtype=pl.Int32).alias("sub_line"),
            pl.concat_str(
                [
                    pl.lit("01"),
                    pl.lit(BANK_CODE),
                    pl.lit("0000"),
                    pl.col("guichet_code_5"),
                    pl.lit("EUR2 "),
                    pl.col("num_compte_11"),
                    pl.lit("60"),
                    pl.col("date_solde_01"),
                    pl.lit("00"),
                    pl.col("date_solde_01"),
                    pl.lit("ANCIEN SOLDE DEBUT PERIODE     "),
                    pl.lit("  000000000"),
                    encode_cfonb_signed_expr("opening_01_cents"),
                    pl.lit("SOLDEINIT01 "),
                ]
            ).alias("raw_line"),
        )

        mvts_m = mvts_df.filter(pl.col("ym") == ym).sort(["acc_idx", "date_compta"])
        n_m = mvts_m.height
        total_04_written += n_m
        row_ids = np.arange(1, n_m + 1, dtype=np.int64)
        mvts_m = mvts_m.with_columns(
            pl.Series("mvt_row_id", row_ids),
            pl.Series("seq", row_ids).cast(pl.String).str.zfill(7),
        )

        # Ligne '04' : ne porte PAS le BIC ni l'EndToEndId (uniquement réf lot MVTxxxxxxx)
        df_04 = mvts_m.select(
            pl.col("acc_idx"),
            pl.lit(1, dtype=pl.Int32).alias("ord_type"),
            pl.col("date_compta").alias("sort_date"),
            pl.col("mvt_row_id"),
            pl.lit(0, dtype=pl.Int32).alias("sub_line"),
            pl.concat_str(
                [
                    pl.lit("04"),
                    pl.lit(BANK_CODE),
                    pl.col("code_op_interne"),
                    pl.col("code_guichet_raw"),
                    pl.lit("EUR2 "),
                    pl.col("num_compte_11"),
                    pl.col("code_afb"),
                    pl.col("date_compta"),
                    pl.lit("00"),
                    pl.col("date_valeur"),
                    pl.col("libelle").str.pad_end(31, " ").str.slice(0, 31),
                    pl.lit("  "),
                    pl.col("seq"),
                    pl.lit("00"),
                    encode_cfonb_signed_expr("signed_cents"),
                    pl.lit("MVT"),
                    pl.col("seq"),
                    pl.lit("  "),
                ]
            ).alias("raw_line"),
        )

        # Ligne complémentaire '05' (pour tous les flux SEPA hors CB '0310') placée JUSTE SOUS son '04' !
        mvts_sepa = mvts_m.filter(pl.col("code_op_interne") != "0310")
        total_05_written += mvts_sepa.height
        df_05 = mvts_sepa.with_columns(
            pl.col("code_op_interne")
            .replace_strict(motif_map, return_dtype=pl.String)
            .alias("motif_sepa")
        ).select(
            pl.col("acc_idx"),
            pl.lit(1, dtype=pl.Int32).alias("ord_type"),
            pl.col("date_compta").alias("sort_date"),
            pl.col("mvt_row_id"),
            pl.lit(1, dtype=pl.Int32).alias("sub_line"),
            pl.concat_str(
                [
                    pl.lit("05"),
                    pl.lit(BANK_CODE),
                    pl.col("code_op_interne"),
                    pl.col("code_guichet_raw"),
                    pl.lit("EUR2 "),
                    pl.col("num_compte_11"),
                    pl.col("code_afb"),
                    pl.col("date_compta"),
                    pl.lit("  "),
                    pl.lit("IBI"),
                    pl.col("ref_bic").str.pad_end(12, " ").str.slice(0, 12),
                    pl.col("e2e_id").str.pad_end(36, " ").str.slice(0, 36),
                    pl.col("motif_sepa").str.pad_end(25, " ").str.slice(0, 25),
                ]
            ).alias("raw_line"),
        )

        df_07 = bal_m.select(
            pl.col("acc_idx"),
            pl.lit(2, dtype=pl.Int32).alias("ord_type"),
            pl.col("date_solde_07").alias("sort_date"),
            pl.lit(999_999_999, dtype=pl.Int64).alias("mvt_row_id"),
            pl.lit(0, dtype=pl.Int32).alias("sub_line"),
            pl.concat_str(
                [
                    pl.lit("07"),
                    pl.lit(BANK_CODE),
                    pl.lit("0000"),
                    pl.col("guichet_code_5"),
                    pl.lit("EUR2 "),
                    pl.col("num_compte_11"),
                    pl.lit("62"),
                    pl.col("date_solde_07"),
                    pl.lit("00"),
                    pl.col("date_solde_07"),
                    pl.lit("NOUVEAU SOLDE FIN PERIODE      "),
                    pl.lit("  999999900"),
                    encode_cfonb_signed_expr("closing_07_cents"),
                    pl.lit("SOLDEFIN07  "),
                ]
            ).alias("raw_line"),
        )

        month_body = pl.concat([df_01, df_04, df_05, df_07]).sort(
            ["acc_idx", "ord_type", "sort_date", "mvt_row_id", "sub_line"]
        )

        is_2025_gz = y == 2025
        if ym == "202610":
            # Piège #1 : RUN01 interrompu à ~38 % avec trailer ABEND_S0C7 RC=0012
            abort_n = 280_000
            body_abort = month_body.head(abort_n)
            abort_04_cnt = int(body_abort.filter(pl.col("raw_line").str.starts_with("04")).height)
            write_cfonb_file(
                body_df=body_abort,
                out_path=OUTPUT_DIR / "CFONB120_MVTS_202610_RUN01.cfonb",
                hdr_120=make_cft_header_120(ym, run_no=1, enc_label="ISO8859_15"),
                trl_120=make_cft_trailer_120(
                    status="ABEND_S0C7",
                    rc="0012",
                    data_records=abort_n,
                    mvt_04_count=abort_04_cnt,
                    extra="ERR=INTERRUPTED_DUMP",
                ),
                compress_gzip=False,
            )

            # Fichier valide : RUN02_RERUN complet avec RC=0000
            written = write_cfonb_file(
                body_df=month_body,
                out_path=OUTPUT_DIR / "CFONB120_MVTS_202610_RUN02_RERUN.cfonb",
                hdr_120=make_cft_header_120(ym, run_no=2, enc_label="ISO8859_15"),
                trl_120=make_cft_trailer_120(
                    status="OK",
                    rc="0000",
                    data_records=month_body.height,
                    mvt_04_count=n_m,
                ),
                compress_gzip=False,
            )
            total_valid_lines += written
        else:
            ext = ".cfonb.gz" if is_2025_gz else ".cfonb"
            enc_lbl = "ISO8859_15_GZIP" if is_2025_gz else "ISO8859_15"
            written = write_cfonb_file(
                body_df=month_body,
                out_path=OUTPUT_DIR / f"CFONB120_MVTS_{ym}{ext}",
                hdr_120=make_cft_header_120(ym, run_no=1, enc_label=enc_lbl),
                trl_120=make_cft_trailer_120(
                    status="OK",
                    rc="0000",
                    data_records=month_body.height,
                    mvt_04_count=n_m,
                ),
                compress_gzip=is_2025_gz,
            )
            total_valid_lines += written

    assert total_04_written == TARGET_TOTAL_MOVEMENTS_04

    # ------------------------------------------------------------------
    # [5/5] Écriture binaire EBCDIC CP500 + COMP-3 des référentiels maîtres
    # ------------------------------------------------------------------
    print("[5/5] Encodage binaire z/OS (EBCDIC CP500 + COMP-3 RECFM=FB) des maîtres Clients & Comptes...")
    mf_customers = universe["customers"].filter(pl.col("in_mainframe")).sort("cust_idx")
    c_prot = mf_customers["cust_idx"].to_numpy() == WITNESS_CUST_IDX
    c_ag4_noisy, c_gu5_noisy = corrupt_agency_codes(
        mf_customers["agency_code_4"].to_numpy(),
        mf_customers["guichet_code_5"].to_numpy(),
        rng,
        protect_mask=c_prot,
    )
    n_cust_written = write_ebcdic_customers_master(
        mf_customers,
        c_ag4_noisy,
        c_gu5_noisy,
        OUTPUT_DIR / "CBK_CUSTOMERS_REF_20261112.ebcdic",
    )

    last_mvt_per_acc = mvts_df.group_by("acc_idx").agg(pl.col("date_compta").max().alias("last_mvt_date"))
    final_bal_202611 = balances_grid.filter(pl.col("ym") == "202611").select(
        "acc_idx", pl.col("closing_07_cents").alias("final_balance_cents")
    )
    mf_acc_joined = (
        mf_accounts.join(final_bal_202611, on="acc_idx", how="left")
        .join(last_mvt_per_acc, on="acc_idx", how="left")
        .with_columns(
            pl.col("final_balance_cents").fill_null(0),
            pl.coalesce([pl.col("last_mvt_date"), pl.col("opening_date")]).alias("eff_last_mvt_date"),
        )
        .sort("acc_idx")
    )
    a_prot = mf_acc_joined["account_id"].to_numpy() == WITNESS_ACC_ID
    a_ag4_noisy, a_gu5_noisy = corrupt_agency_codes(
        mf_acc_joined["agency_code_4"].to_numpy(),
        mf_acc_joined["guichet_code_5"].to_numpy(),
        rng,
        protect_mask=a_prot,
    )
    n_acc_written = write_ebcdic_accounts_master(
        mf_acc_joined,
        a_ag4_noisy,
        a_gu5_noisy,
        OUTPUT_DIR / "CBK_ACCOUNTS_MSTR_20261112.ebcdic",
    )

    manifest_content = f"""********************************************************************************
* BANQUE HEXAGONE - EXPLOITATION Z/OS PROD - BORDEREAU TRANSFERT CFT -> GCS    *
* JOBNAME  : JCBK2345  | STEP : EXTRCFON | DATE ARRETE : 2026-11-12 23:45:12   *
********************************************************************************

[COPYBOOKS_COBOL]
  - copybooks/CBK_CUSTOMERS_REF.cpy    (RECFM=FB, LRECL=0140, EBCDIC CP500 + COMP-3)
  - copybooks/CBK_ACCOUNTS_MSTR.cpy    (RECFM=FB, LRECL=0150, EBCDIC CP500 + COMP-3)
  - copybooks/CFONB120_BAL_OPS.cpy     (LRECL=0120, ENR 00/01/04/05/07/99)

[DATASETS_MAITRES_BINAIRES_Z_OS]
  - CBK_CUSTOMERS_REF_20261112.ebcdic  DATA_RECORDS={n_cust_written:09d}  LRECL=140 (NO LF)
  - CBK_ACCOUNTS_MSTR_20261112.ebcdic  DATA_RECORDS={n_acc_written:09d}  LRECL=150 (NO LF)

[JOURNAUX_CFONB_120]
  - 202506..202512 : 7 archives .cfonb.gz (GZIP ISO-8859-15)
  - 202601..202611 : fichiers .cfonb en clair (ISO-8859-15)
  - INCIDENT EXPLOITATION 2026-10 :
      * CFONB120_MVTS_202610_RUN01.cfonb       -> INTERROMPU (ABEND_S0C7, RC=0012)
      * CFONB120_MVTS_202610_RUN02_RERUN.cfonb -> REPRISE COMPLETE (STATUS=OK, RC=0000)
  - TOTAL LIGNES VALIDES (HORS RUN01) : {total_valid_lines:,}
      dont {total_04_written:,} mouvements '04' et {total_05_written:,} compléments SEPA '05'.
********************************************************************************
"""
    (OUTPUT_DIR / "MANIFEST_Z_OS_DROP.ctl").write_text(manifest_content, encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print(
        f"\nTerminé en {elapsed:.1f}s -> {OUTPUT_DIR}\n"
        f"  - Clients EBCDIC+COMP3 : {n_cust_written:,} blocs fixes de 140 octets\n"
        f"  - Comptes EBCDIC+COMP3 : {n_acc_written:,} blocs fixes de 150 octets\n"
        f"  - Lignes CFONB valides : {total_valid_lines:,} (04={total_04_written:,}, 05={total_05_written:,})\n"
        f"  - Piège ABEND généré   : CFONB120_MVTS_202610_RUN01.cfonb (RC=0012)"
    )


if __name__ == "__main__":
    generate_corebanking_files()
