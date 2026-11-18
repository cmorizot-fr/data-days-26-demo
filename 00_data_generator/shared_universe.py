"""
Socle déterministe partagé (seed=2026) pour tous les silos Couche 0 de la démo
Paris Data Summit 2026 (Banque Hexagone).

Garantit l'alignement au centime et à l'ID près entre :
- Core Banking Mainframe (CFONB 120 + maîtres comptes/clients)
- AWS S3 CRM & Call Center (BigQuery Omni Borderless)
- Flux Paiements Temps Réel (ISO 20022 pacs.008)
- Finance SAP / PCEC & Trésorerie ALM + Contrats PDF
- Persona témoin Démo #4 (Lucas Martin, CUST00002026 / ACC00002026)
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

# ==============================================================================
# Constantes & Invariants métier (AGENTS.md & DESIGN_AND_CONTEXT.md)
# ==============================================================================
DEMO_SEED: int = 2026
BANK_CODE: str = "30002"
BANK_BIC: str = "HEXAFRLPXXX"

SNAPSHOT_DATE: date = date(2026, 11, 12)  # Drop batch Mainframe J-1 23h45
DEMO_LIVE_DATE: date = date(2026, 11, 13)  # Jour J de la démo live
QUARTER_START_DATE: date = date(2026, 8, 15)  # Fenêtre exacte de 90 jours [08-15 .. 11-12]
HISTORY_START_DATE: date = date(2025, 6, 1)  # 18 mois glissants [2025-06 .. 2026-11]

N_REGIONS: int = 8
N_AGENCIES: int = 450
N_CUSTOMERS_TOTAL: int = 80_000
N_ACCOUNTS_TOTAL: int = 95_000
N_AWS_ORPHANS: int = 650  # Créés récemment sur AWS S3, pas encore dans Mainframe J-1
N_RECENT_ACCOUNT_OPENINGS: int = 15_000  # Ouvertures sur le trimestre [2026-08-15 .. 2026-11-12]

# Fuite des dépôts à vue sur 90 jours : exactement 2 420 000 000,00 €
TOTAL_LEAK_90D_CENTS: int = 242_000_000_000
YOUNG_1_TO_5_LEAK_90D_CENTS: int = 164_560_000_000  # Exactement 68,0 %
OTHER_LEAK_90D_CENTS: int = TOTAL_LEAK_90D_CENTS - YOUNG_1_TO_5_LEAK_90D_CENTS  # 32,0 %

# Écart PNB CFO vs budget sur la fenêtre de 90 jours (Démo #3 — Fake vs Certifié)
ALM_TCI_COST_90D_CENTS: int = 2_412_000_000  # -24 120 000,00 € (TCI ALM, PCEC 601320)
PDF_PROMO_COST_CENTS: int = 1_430_000_000  # -14 300 000,00 € (250 avenants PDF hors-SAP)
NAIVE_PNB_VARIANCE_CENTS: int = 4_280_000_000  # +42 800 000,00 € (SUM brut non signé)
CERTIFIED_PNB_VARIANCE_CENTS: int = -(ALM_TCI_COST_90D_CENTS + PDF_PROMO_COST_CENTS)  # -38 420 000,00 €

WITNESS_CUST_IDX: int = 2026
WITNESS_CUST_ID: str = "CUST00002026"
WITNESS_ACC_ID: str = "ACC00002026"
WITNESS_NUM_COMPTE: str = "00000002026"

NEOBANK_DESTINATIONS: list[tuple[str, str]] = [
    ("REVOLT21XXX", "VIR SEPA INST REVOLT21"),
    ("TRBKDEBBXXX", "VIR SEPA INST TRBKDEBB"),
    ("NTSBDEB1XXX", "VIR SEPA INST NTSBDEB1"),
    ("BOURFRPPXXX", "VIR SEPA INST BOURFRPP"),
    ("DEGIRO2AXXX", "VIR SEPA INST DEGIRO2A"),
]

REGIONS_DEF: list[tuple[str, str, float, list[str]]] = [
    ("REG1", "Ile-de-France", 0.24, ["PARIS", "BOULOGNE", "VERSAILLES", "SAINT DENIS", "NANTERRE"]),
    ("REG2", "Auvergne-Rhone-Alpes", 0.15, ["LYON", "GRENOBLE", "ANNECY", "CLERMONT", "SAINT ETIENNE"]),
    ("REG3", "Nouvelle-Aquitaine", 0.11, ["BORDEAUX", "PAU", "LIMOGES", "LA ROCHELLE", "BAYONNE"]),
    ("REG4", "Occitanie", 0.11, ["TOULOUSE", "MONTPELLIER", "NIMES", "PERPIGNAN", "ALBI"]),
    ("REG5", "Hauts-de-France", 0.10, ["LILLE", "AMIENS", "ARRAS", "ROUBAIX", "VALENCIENNES"]),
    ("REG6", "Grand Est", 0.09, ["STRASBOURG", "REIMS", "METZ", "NANCY", "MULHOUSE"]),
    ("REG7", "Provence-Cote-d-Azur", 0.10, ["MARSEILLE", "NICE", "AIX", "TOULON", "AVIGNON"]),
    ("REG8", "Grand Ouest", 0.10, ["NANTES", "RENNES", "ANGERS", "BREST", "LE MANS"]),
]

LAST_NAMES: list[str] = [
    "MARTIN", "BERNARD", "THOMAS", "PETIT", "ROBERT", "RICHARD", "DURAND", "DUBOIS",
    "MOREAU", "LAURENT", "SIMON", "MICHEL", "LEFEBVRE", "LEROY", "ROUX", "DAVID",
    "BERTRAND", "MOREL", "FOURNIER", "GIRARD", "BONNET", "DUPONT", "LAMBERT", "FONTAINE",
    "ROUSSEAU", "VINCENT", "MULLER", "LEFEVRE", "FAURE", "ANDRE", "MERCIER", "BLANC",
    "GUERIN", "BOYER", "GARNIER", "CHEVALIER", "FRANCOIS", "LEGRAND", "GAUTHIER", "GARCIA",
]

FIRST_NAMES: list[str] = [
    "LUCAS", "EMMA", "LEO", "JADE", "GABRIEL", "LOUISE", "RAPHAEL", "ALICE",
    "ARTHUR", "CHLOE", "LOUIS", "INES", "JULES", "LEA", "ADAM", "MANON",
    "MAEL", "JULIA", "PAUL", "CAMILLE", "HUGO", "SARAH", "NATHAN", "CLARA",
    "THOMAS", "MARIE", "NICOLAS", "JULIEN", "SOPHIE", "ANTOINE", "CLAIRE", "MAXIME",
    "ALEXANDRE", "HELENE", "ROMAIN", "VALERIE", "PHILIPPE", "ISABELLE", "LAURENT", "CECILE",
]

BASE_DIR: Path = Path(__file__).resolve().parent
UNIVERSE_CACHE_DIR: Path = BASE_DIR / "data" / "universe"


def distribute_exact_cents(
    weights: np.ndarray,
    target_cents: int,
    min_cents: int = 15_000,
    max_cents: int = 9_500_000,
) -> np.ndarray:
    """Alloue exactement `target_cents` sur un vecteur d'entiers bornés [min_cents, max_cents]."""
    n = len(weights)
    if n * min_cents > target_cents or n * max_cents < target_cents:
        raise ValueError(
            f"Impossible d'allouer {target_cents} centimes sur {n} lignes "
            f"dans [{min_cents}, {max_cents}]."
        )

    w = np.asarray(weights, dtype=np.float64)
    w = np.maximum(w, 1e-9)
    alloc = np.floor((w / w.sum()) * target_cents).astype(np.int64)
    alloc = np.clip(alloc, min_cents, max_cents)

    diff = int(target_cents - int(alloc.sum()))
    while diff != 0:
        if diff > 0:
            eligible = np.flatnonzero(alloc < max_cents)
            step = max(1, diff // len(eligible))
            headroom = max_cents - alloc[eligible]
            add = np.minimum(headroom, step)
            if int(add.sum()) > diff:
                # Ajustement fin unitaire
                idx = eligible[:diff]
                alloc[idx] += 1
            else:
                alloc[eligible] += add
        else:
            need = -diff
            eligible = np.flatnonzero(alloc > min_cents)
            step = max(1, need // len(eligible))
            headroom = alloc[eligible] - min_cents
            sub = np.minimum(headroom, step)
            if int(sub.sum()) > need:
                idx = eligible[:need]
                alloc[idx] -= 1
            else:
                alloc[eligible] -= sub
        diff = int(target_cents - int(alloc.sum()))

    return alloc


def compute_french_rib_and_iban(
    bank_code: str,
    guichet_codes: np.ndarray,
    account_nums_11: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcule la vraie clé RIB française (01..97) et le vrai IBAN FRkk (ISO 13616)."""
    b_int = int(bank_code)
    g_int = np.array([int(g) for g in guichet_codes], dtype=np.int64)
    c_int = np.array([int(c) for c in account_nums_11], dtype=np.int64)

    # Clé RIB = 97 - ((89 * CodeBanque + 15 * CodeGuichet + 3 * NumCompte) % 97)
    rem_rib = (89 * b_int + 15 * g_int + (3 * (c_int % 97))) % 97
    cle_rib_int = 97 - rem_rib
    cle_rib = np.array([f"{k:02d}" for k in cle_rib_int], dtype="U2")

    # IBAN FRkk : BBAN (23 chiffres) + 'FR00' -> FR = 1527 -> + '152700'
    # Modulo 97 par découpage entier pour éviter tout dépassement int64
    # BBAN = bank(5) || guichet(5) || compte(11) || cle(2)
    ibans = np.empty(len(guichet_codes), dtype="U27")
    for i in range(len(guichet_codes)):
        bban = f"{bank_code}{guichet_codes[i]}{account_nums_11[i]}{cle_rib[i]}"
        iban_num = int(bban + "152700")
        kk = 98 - (iban_num % 97)
        ibans[i] = f"FR{kk:02d}{bban}"
    return cle_rib, ibans


def build_or_load_universe(force_rebuild: bool = False) -> dict[str, pl.DataFrame]:
    """Construit (ou charge depuis le cache Parquet) l'univers déterministe complet."""
    UNIVERSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "regions": UNIVERSE_CACHE_DIR / "regions.parquet",
        "agencies": UNIVERSE_CACHE_DIR / "agencies.parquet",
        "customers": UNIVERSE_CACHE_DIR / "customers.parquet",
        "accounts": UNIVERSE_CACHE_DIR / "accounts.parquet",
        "leak_events_90d": UNIVERSE_CACHE_DIR / "leak_events_90d.parquet",
    }
    if not force_rebuild and all(p.exists() for p in paths.values()):
        return {k: pl.read_parquet(p) for k, p in paths.items()}

    rng = np.random.default_rng(DEMO_SEED)

    # ------------------------------------------------------------------
    # 1. Régions (8) & Agences (450)
    # ------------------------------------------------------------------
    regions_df = pl.DataFrame(
        {
            "region_code": [r[0] for r in REGIONS_DEF],
            "region_name": [r[1] for r in REGIONS_DEF],
            "weight": [r[2] for r in REGIONS_DEF],
        }
    )

    reg_weights = np.array([r[2] for r in REGIONS_DEF])
    reg_counts = np.floor(reg_weights * N_AGENCIES).astype(int)
    reg_counts[0] += N_AGENCIES - int(reg_counts.sum())

    agency_regions: list[str] = []
    agency_cities: list[str] = []
    for idx_r, (r_code, _, _, cities) in enumerate(REGIONS_DEF):
        cnt = int(reg_counts[idx_r])
        agency_regions.extend([r_code] * cnt)
        chosen_cities = rng.choice(cities, size=cnt)
        agency_cities.extend(chosen_cities.tolist())

    agency_nums = np.arange(1, N_AGENCIES + 1, dtype=np.int32)
    # Garantir que l'agence 0042 est à PARIS (REG1) pour notre client témoin
    agency_regions[41] = "REG1"
    agency_cities[41] = "PARIS"

    agencies_df = pl.DataFrame(
        {
            "agency_num": agency_nums,
            "agency_code_4": [f"{n:04d}" for n in agency_nums],
            "guichet_code_5": [f"{n:05d}" for n in agency_nums],
            "region_code": agency_regions,
            "city": agency_cities,
        }
    )

    # ------------------------------------------------------------------
    # 2. Clients (80 000 dont 79 350 Mainframe + 650 orphelins AWS S3)
    # ------------------------------------------------------------------
    cust_idx = np.arange(1, N_CUSTOMERS_TOTAL + 1, dtype=np.int32)
    customer_ids = np.array([f"CUST{i:08d}" for i in cust_idx], dtype="U12")

    cust_agency_idx = rng.integers(0, N_AGENCIES, size=N_CUSTOMERS_TOTAL)
    cust_agency_idx[WITNESS_CUST_IDX - 1] = 41  # Agence 0042

    # Distribution d'âge : ~34 % entre 18 et 32 ans, ~46 % entre 33 et 58, ~20 % entre 59 et 82
    age_bucket = rng.choice([0, 1, 2], size=N_CUSTOMERS_TOTAL, p=[0.34, 0.46, 0.20])
    ages = np.empty(N_CUSTOMERS_TOTAL, dtype=np.int32)
    m0 = age_bucket == 0
    m1 = age_bucket == 1
    m2 = age_bucket == 2
    ages[m0] = rng.integers(18, 33, size=int(m0.sum()))
    ages[m1] = rng.integers(33, 59, size=int(m1.sum()))
    ages[m2] = rng.integers(59, 83, size=int(m2.sum()))
    ages[WITNESS_CUST_IDX - 1] = 27

    # Dates de naissance cohérentes avec l'âge révolu au 2026-11-12
    birth_days_offset = rng.integers(1, 300, size=N_CUSTOMERS_TOTAL)
    birth_dates_str = [
        (date(SNAPSHOT_DATE.year - int(ages[i]), 1, 1) + timedelta(days=int(birth_days_offset[i]))).strftime(
            "%Y%m%d"
        )
        for i in range(N_CUSTOMERS_TOTAL)
    ]
    birth_dates_str[WITNESS_CUST_IDX - 1] = "19990415"

    # Segments & CSP
    segments = np.where(
        ages <= 32,
        rng.choice(
            ["JEUNE_ACTIF", "AFFLUENT", "PATRIMONIAL"],
            size=N_CUSTOMERS_TOTAL,
            p=[0.74, 0.20, 0.06],
        ),
        rng.choice(
            ["MASS_MARKET", "AFFLUENT", "PATRIMONIAL"],
            size=N_CUSTOMERS_TOTAL,
            p=[0.62, 0.28, 0.10],
        ),
    )
    segments[WITNESS_CUST_IDX - 1] = "JEUNE_ACTIF"

    csps = np.where(
        ages <= 23,
        rng.choice(["ETUDIANT", "EMPLOYE", "CADRE_TECH"], size=N_CUSTOMERS_TOTAL, p=[0.55, 0.30, 0.15]),
        np.where(
            ages >= 64,
            "RETRAITE",
            rng.choice(
                ["CADRE_TECH", "INGENIEUR", "EMPLOYE", "LIBERAL", "FONCTIONN", "COMMERCANT"],
                size=N_CUSTOMERS_TOTAL,
                p=[0.24, 0.18, 0.28, 0.12, 0.11, 0.07],
            ),
        ),
    )
    csps[WITNESS_CUST_IDX - 1] = "CADRE_TECH"

    last_names = rng.choice(LAST_NAMES, size=N_CUSTOMERS_TOTAL)
    first_names = rng.choice(FIRST_NAMES, size=N_CUSTOMERS_TOTAL)
    last_names[WITNESS_CUST_IDX - 1] = "MARTIN"
    first_names[WITNESS_CUST_IDX - 1] = "LUCAS"

    # Dates d'entrée en relation :
    # - 1 .. 62 000 : historiques [2015-01-01 .. 2025-05-31] (présents dès le début des 18 mois)
    # - 62 001 .. 68 000 (6 000 clients) : [2025-06-01 .. 2026-08-14] (in_mainframe=True)
    # - 68 001 .. 79 350 (11 350 clients) : récents trimestre [2026-08-15 .. 2026-11-09] (in_mainframe=True)
    # - 79 351 .. 80 000 (650 clients) : créés sur AWS S3 [2026-11-10 .. 2026-11-12] (in_mainframe=False -> orphelins !)
    N_PRE_WINDOW_CUST = 62_000
    N_MID_WINDOW_CUST = 6_000
    N_HIST_CUST = N_PRE_WINDOW_CUST + N_MID_WINDOW_CUST  # 68 000
    N_RECENT_MF_CUST = N_CUSTOMERS_TOTAL - N_AWS_ORPHANS - N_HIST_CUST  # 11 350

    pre_span = (date(2025, 5, 31) - date(2015, 1, 1)).days
    pre_offsets = rng.integers(0, pre_span + 1, size=N_PRE_WINDOW_CUST)
    mid_span = (date(2026, 8, 14) - HISTORY_START_DATE).days
    mid_offsets = rng.integers(0, mid_span + 1, size=N_MID_WINDOW_CUST)
    rec_mf_span = (date(2026, 11, 9) - QUARTER_START_DATE).days
    rec_mf_offsets = rng.integers(0, rec_mf_span + 1, size=N_RECENT_MF_CUST)
    orphan_offsets = rng.integers(0, 3, size=N_AWS_ORPHANS)  # 2026-11-10 .. 2026-11-12

    onboarding_dates: list[str] = []
    for d in pre_offsets:
        onboarding_dates.append((date(2015, 1, 1) + timedelta(days=int(d))).strftime("%Y%m%d"))
    for d in mid_offsets:
        onboarding_dates.append((HISTORY_START_DATE + timedelta(days=int(d))).strftime("%Y%m%d"))
    for d in rec_mf_offsets:
        onboarding_dates.append((QUARTER_START_DATE + timedelta(days=int(d))).strftime("%Y%m%d"))
    for d in orphan_offsets:
        onboarding_dates.append((date(2026, 11, 10) + timedelta(days=int(d))).strftime("%Y%m%d"))
    onboarding_dates[WITNESS_CUST_IDX - 1] = "20210910"

    in_mainframe_cust = np.ones(N_CUSTOMERS_TOTAL, dtype=bool)
    in_mainframe_cust[N_CUSTOMERS_TOTAL - N_AWS_ORPHANS :] = False

    agency_code_4_arr = agencies_df["agency_code_4"].to_numpy()
    guichet_code_5_arr = agencies_df["guichet_code_5"].to_numpy()
    region_code_arr = agencies_df["region_code"].to_numpy()

    customers_df = pl.DataFrame(
        {
            "cust_idx": cust_idx,
            "customer_id": customer_ids,
            "agency_num": cust_agency_idx + 1,
            "agency_code_4": agency_code_4_arr[cust_agency_idx],
            "guichet_code_5": guichet_code_5_arr[cust_agency_idx],
            "region_code": region_code_arr[cust_agency_idx],
            "birth_date": birth_dates_str,
            "age": ages,
            "is_young_18_32": (ages >= 18) & (ages <= 32),
            "segment": segments,
            "csp": csps,
            "last_name": last_names,
            "first_name": first_names,
            "onboarding_date": onboarding_dates,
            "closure_date": ["00000000"] * N_CUSTOMERS_TOTAL,
            "status": ["ACTIF"] * N_CUSTOMERS_TOTAL,
            "in_mainframe": in_mainframe_cust,
            "is_aws_orphan": ~in_mainframe_cust,
        }
    )

    # ------------------------------------------------------------------
    # 3. Comptes (95 000 : 80 000 CC_CHQ + 15 000 Livrets)
    #    - Ouvertures trimestre [2026-08-15 .. 2026-11-12] :
    #      12 000 CC_CHQ (11 350 MF + 650 AWS) + 3 000 Livrets = 15 000 exactes !
    #    - Clôtures sur le trimestre : 0 !
    # ------------------------------------------------------------------
    N_SAVINGS = N_ACCOUNTS_TOTAL - N_CUSTOMERS_TOTAL  # 15 000
    N_RECENT_SAVINGS = N_RECENT_ACCOUNT_OPENINGS - (N_RECENT_MF_CUST + N_AWS_ORPHANS)  # 3 000
    N_HIST_SAVINGS = N_SAVINGS - N_RECENT_SAVINGS  # 12 000

    # Choix de 15 000 titulaires distincts parmi les clients historiques pré-fenêtre (hors témoin 2026)
    eligible_sav_cust = np.array(
        [i for i in range(N_PRE_WINDOW_CUST) if (i + 1) != WITNESS_CUST_IDX], dtype=np.int32
    )
    sav_cust_zero_idx = rng.choice(eligible_sav_cust, size=N_SAVINGS, replace=False)

    sav_types = rng.choice(
        ["LIVRET_A", "LDDS", "LIV_MAISON"],
        size=N_SAVINGS,
        p=[0.52, 0.28, 0.20],
    )

    sav_open_dates: list[str] = []
    # 12 000 livrets historiques ouverts avant le 2025-05-31 (après l'onboarding du client)
    may31_2025_ord = date(2025, 5, 31).toordinal()
    for k in range(N_HIST_SAVINGS):
        c_onb = onboarding_dates[int(sav_cust_zero_idx[k])]
        c_ord = date(int(c_onb[:4]), int(c_onb[4:6]), int(c_onb[6:8])).toordinal()
        open_ord = int(rng.integers(c_ord, may31_2025_ord + 1))
        sav_open_dates.append(date.fromordinal(open_ord).strftime("%Y%m%d"))

    # 3 000 livrets ouverts sur le trimestre [2026-08-15 .. 2026-11-09]
    q_start_ord = QUARTER_START_DATE.toordinal()
    nov09_ord = date(2026, 11, 9).toordinal()
    for k in range(N_RECENT_SAVINGS):
        open_ord = int(rng.integers(q_start_ord, nov09_ord + 1))
        sav_open_dates.append(date.fromordinal(open_ord).strftime("%Y%m%d"))

    acc_idx = np.arange(1, N_ACCOUNTS_TOTAL + 1, dtype=np.int32)
    account_ids = np.array([f"ACC{i:08d}" for i in acc_idx], dtype="U11")
    num_comptes_11 = np.array([f"{i:011d}" for i in acc_idx], dtype="U11")

    all_cust_zero_idx = np.concatenate([np.arange(N_CUSTOMERS_TOTAL, dtype=np.int32), sav_cust_zero_idx])
    all_acc_types = np.concatenate([np.full(N_CUSTOMERS_TOTAL, "CC_CHQ", dtype="U10"), sav_types])
    all_open_dates = onboarding_dates + sav_open_dates
    all_in_mf = np.concatenate([in_mainframe_cust, np.ones(N_SAVINGS, dtype=bool)])

    acc_guichets = guichet_code_5_arr[cust_agency_idx[all_cust_zero_idx]]
    acc_agencies_4 = agency_code_4_arr[cust_agency_idx[all_cust_zero_idx]]
    cle_rib, ibans = compute_french_rib_and_iban(BANK_CODE, acc_guichets, num_comptes_11)

    # Taux faciaux : Livret Maison à 1,50 %, comme le PDF réglementaire REG_06 (ACPR 2024-R-01),
    # les avenants agence (« taux facial du Livret Maison (1,50 %) ») et le seed savings_offer_catalog.
    rate_bps_map = {"CC_CHQ": 0, "LIVRET_A": 300, "LDDS": 300, "LIV_MAISON": 150}
    label_map = {
        "CC_CHQ": "COMPTE COURANT HEXA",
        "LIVRET_A": "LIVRET A REGLEMENTE",
        "LDDS": "LIVRET DEV DURABLE",
        "LIV_MAISON": "LIVRET EPARGNE HEXA",
    }
    rates_bps = np.array([rate_bps_map[t] for t in all_acc_types], dtype=np.int32)
    prod_labels = np.array([label_map[t] for t in all_acc_types], dtype="U20")

    accounts_df = pl.DataFrame(
        {
            "acc_idx": acc_idx,
            "account_id": account_ids,
            "num_compte_11": num_comptes_11,
            "cust_idx": all_cust_zero_idx + 1,
            "customer_id": customer_ids[all_cust_zero_idx],
            "agency_code_4": acc_agencies_4,
            "guichet_code_5": acc_guichets,
            "cle_rib": cle_rib,
            "iban": ibans,
            "account_type": all_acc_types,
            "opening_date": all_open_dates,
            "closure_date": ["00000000"] * N_ACCOUNTS_TOTAL,
            "status": ["OUVERT"] * N_ACCOUNTS_TOTAL,
            "rate_bps": rates_bps,
            "product_label": prod_labels,
            "in_mainframe": all_in_mf,
            "is_aws_orphan": ~all_in_mf,
            "is_opened_in_quarter": [d >= "20260815" for d in all_open_dates],
        }
    )

    # ------------------------------------------------------------------
    # 4. Fuite exacte des dépôts à vue sur 90j (2 420 000 000,00 €)
    #    - 68,0 % (1 645 600 000,00 €) : 18-32 ans ET jour du mois 1..5
    #    - 32,0 % (  774 400 000,00 €) : 33+ ans OU jour du mois >= 6
    #    - Aucun virement néobanque les 13-14 août 2026 (zone tampon SQL 90j)
    # ------------------------------------------------------------------
    # Comptes courants historiques déjà dotés de dépôts avant 2025-06-01 (clients 1..62 000)
    pre_ages = ages[:N_PRE_WINDOW_CUST]
    young_hist_idx = np.flatnonzero(
        (pre_ages >= 18) & (pre_ages <= 32) & (np.arange(N_PRE_WINDOW_CUST) != WITNESS_CUST_IDX - 1)
    )
    older_hist_idx = np.flatnonzero(pre_ages >= 33)

    # Jours éligibles dans [2026-08-15 .. 2026-11-12] :
    days_1_to_5: list[str] = []
    days_6_plus: list[str] = []
    cur = QUARTER_START_DATE
    while cur <= SNAPSHOT_DATE:
        if 1 <= cur.day <= 5:
            days_1_to_5.append(cur.strftime("%Y%m%d"))
        else:
            days_6_plus.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)

    # --- Poche A : 18-32 ans, jours 1..5 (135 000 virements + 2 virements témoin Lucas Martin)
    WITNESS_LEAK_CENTS = 90_000  # 2 x 450,00 € (2026-09-03 et 2026-10-03)
    N_LEAK_A = 134_998
    chosen_young_zero = rng.choice(young_hist_idx, size=N_LEAK_A, replace=True)
    dates_a = rng.choice(days_1_to_5, size=N_LEAK_A)
    weights_a = rng.lognormal(mean=9.05, sigma=0.72, size=N_LEAK_A)
    amounts_a = distribute_exact_cents(
        weights=weights_a,
        target_cents=YOUNG_1_TO_5_LEAK_90D_CENTS - WITNESS_LEAK_CENTS,
        min_cents=20_000,      # 200,00 €
        max_cents=9_200_000,   # 92 000,00 € (< plafond SCT Inst 100k€)
    )
    neo_idx_a = rng.choice(len(NEOBANK_DESTINATIONS), size=N_LEAK_A, p=[0.38, 0.32, 0.14, 0.10, 0.06])

    # --- Poche B : 32,0 % hors (18-32 ans & jours 1..5) -> 65 000 virements
    #     75 % chez les 33+ ans (tous jours), 25 % chez les 18-32 ans mais jours 6..31
    N_LEAK_B = 65_000
    N_LEAK_B_OLDER = 48_750
    N_LEAK_B_YOUNG_LATE = N_LEAK_B - N_LEAK_B_OLDER

    chosen_older_zero = rng.choice(older_hist_idx, size=N_LEAK_B_OLDER, replace=True)
    all_90_days = days_1_to_5 + days_6_plus
    dates_b_older = rng.choice(all_90_days, size=N_LEAK_B_OLDER)

    chosen_young_late_zero = rng.choice(young_hist_idx, size=N_LEAK_B_YOUNG_LATE, replace=True)
    dates_b_young_late = rng.choice(days_6_plus, size=N_LEAK_B_YOUNG_LATE)

    chosen_b_zero = np.concatenate([chosen_older_zero, chosen_young_late_zero])
    dates_b = np.concatenate([dates_b_older, dates_b_young_late])
    weights_b = rng.lognormal(mean=9.05, sigma=0.75, size=N_LEAK_B)
    amounts_b = distribute_exact_cents(
        weights=weights_b,
        target_cents=OTHER_LEAK_90D_CENTS,
        min_cents=20_000,
        max_cents=9_500_000,
    )
    neo_idx_b = rng.choice(len(NEOBANK_DESTINATIONS), size=N_LEAK_B, p=[0.24, 0.36, 0.10, 0.18, 0.12])

    # Assemblage incluant les 2 virements de fuite de Lucas Martin (M-2 et M-1)
    all_leak_zero = np.concatenate(
        [
            np.array([WITNESS_CUST_IDX - 1, WITNESS_CUST_IDX - 1], dtype=np.int32),
            chosen_young_zero,
            chosen_b_zero,
        ]
    )
    all_leak_dates = np.concatenate(
        [
            np.array(["20260903", "20261003"], dtype="U8"),
            dates_a,
            dates_b,
        ]
    )
    all_leak_cents = np.concatenate(
        [
            np.array([45_000, 45_000], dtype=np.int64),
            amounts_a,
            amounts_b,
        ]
    )
    all_neo_idx = np.concatenate([np.array([0, 0]), neo_idx_a, neo_idx_b])
    neo_bics = np.array([NEOBANK_DESTINATIONS[i][0] for i in all_neo_idx], dtype="U12")
    neo_labels = np.array([NEOBANK_DESTINATIONS[i][1] for i in all_neo_idx], dtype="U31")

    n_total_leaks = len(all_leak_cents)
    e2e_ids = np.array([f"E2E2026Q4LEAK{i:07d}" for i in range(1, n_total_leaks + 1)], dtype="U24")
    leak_days = np.array([int(d[6:8]) for d in all_leak_dates], dtype=np.int32)
    leak_ages = ages[all_leak_zero]

    leak_events_df = pl.DataFrame(
        {
            "end_to_end_id": e2e_ids,
            "acc_idx": all_leak_zero + 1,  # 1..80000 => compte courant principal du client
            "account_id": account_ids[all_leak_zero],
            "num_compte_11": num_comptes_11[all_leak_zero],
            "cust_idx": all_leak_zero + 1,
            "customer_id": customer_ids[all_leak_zero],
            "guichet_code_5": guichet_code_5_arr[cust_agency_idx[all_leak_zero]],
            "accounting_date": all_leak_dates,
            "amount_cents": all_leak_cents,  # Montant positif de la fuite (sera signé en débit '-' dans CFONB)
            "neobank_bic": neo_bics,
            "libelle": neo_labels,
            "customer_age": leak_ages,
            "is_young_18_32": (leak_ages >= 18) & (leak_ages <= 32),
            "is_day_1_to_5": (leak_days >= 1) & (leak_days <= 5),
        }
    )

    # Assertions immédiates sur les invariants universels
    assert int(leak_events_df["amount_cents"].sum()) == TOTAL_LEAK_90D_CENTS
    young_1_5_sum = int(
        leak_events_df.filter(pl.col("is_young_18_32") & pl.col("is_day_1_to_5"))["amount_cents"].sum()
    )
    assert young_1_5_sum == YOUNG_1_TO_5_LEAK_90D_CENTS
    assert int(accounts_df["is_opened_in_quarter"].sum()) == N_RECENT_ACCOUNT_OPENINGS
    assert int(accounts_df["is_aws_orphan"].sum()) == N_AWS_ORPHANS

    result = {
        "regions": regions_df,
        "agencies": agencies_df,
        "customers": customers_df,
        "accounts": accounts_df,
        "leak_events_90d": leak_events_df,
    }
    for key, df in result.items():
        df.write_parquet(paths[key])
    return result
