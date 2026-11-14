"""
Générateur déterministe du silo SaaS CRM & Call Center (AWS S3 Iceberg / Parquet)
adossé au socle partagé `shared_universe.py` (seed=2026) pour garantir un alignement
à l'ID et à l'IBAN près avec le Mainframe Core Banking (`generate_mainframe_cfonb.py`).

Tables générées dans `00_data_generator/output/RAW/AWS/` (et synchronisées sur GCS `RAW/AWS/`) :
  1. crm_customers          : 80 000 clients particuliers (dont les 650 récents absents du batch Mainframe J-1)
  2. crm_account_portfolio  : 95 000 comptes (0 clôture, +15 000 ouvertures trimestre, 650 orphelins Mainframe)
  3. crm_interactions       : 320 000 comptes-rendus de RDV agences & verbatims Call Center
  4. crm_branches_ref       : 450 agences réparties sur les 8 régions commerciales
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from shared_universe import (
    DEMO_LIVE_DATE,
    DEMO_SEED,
    N_ACCOUNTS_TOTAL,
    N_AGENCIES,
    N_AWS_ORPHANS,
    N_CUSTOMERS_TOTAL,
    N_RECENT_ACCOUNT_OPENINGS,
    N_REGIONS,
    WITNESS_CUST_IDX,
    build_or_load_universe,
)

NUM_CRM_INTERACTIONS: int = 320_000
NUM_PROMO_PDF_CONTRACTS: int = 250

VERBATIM_SILENT_CHURN_YOUNG = np.array([
    "Appel client : demande le relèvement immédiat du plafond de virement SEPA Instant en début de mois vers son compte Revolut (REVOLT21XXX). Conserve son compte courant chez nous pour la domiciliation du salaire.",
    "RDV agence : le client indique transférer chaque mois entre le 1er et le 5 l'essentiel de ses liquidités vers Trade Republic (TRBKDEBBXXX) rémunéré à taux court terme. Aucune demande de clôture du compte courant.",
    "Contact messagerie mobile : question sur l'absence de notification budget temps réel dans l'application mobile par rapport à N26 / BoursoBank ; réalise un virement instantané sortant juste après réception paie.",
    "Appel Call Center : vérification d'ajout de bénéficiaire IBAN externe néobanque pour virement SEPA Instant récurrent post-salaire. Compte courant principal maintenu actif.",
])

VERBATIM_PROMO_CONTRACTS = np.array([
    "Ouverture / équipement en agence : application des conditions dérogatoires prévues à l'avenant promotionnel agence (prime de bienvenue et taux livret boosté sur 6 mois). Dossier PDF signé.",
    "Appel suivi commercial : le client demande confirmation de la date de versement de la prime promotionnelle et de la bonification tarifaire engagée lors de la campagne agence.",
    "RDV conquête réseau : souscription validée avec remise commerciale première année et offre d'épargne boostée rattachée au contrat cadre promotionnel de l'agence.",
])

VERBATIM_STANDARD_RETAIL = np.array([
    "Appel Call Center : demande d'information sur le plafond de paiement carte lors d'un déplacement en Europe. Résolu en ligne.",
    "RDV agence annuel : point patrimonial courant, client satisfait de la relation conseiller, aucune anomalie signalée sur le compte à vue.",
    "Messagerie sécurisée : demande d'attestation de RIB et suivi d'un remboursement complémentaire santé attendu sur le mois en cours.",
    "Appel conseiller : simulation de capacité d'emprunt auto / projet personnel, compte courant mouvementé régulièrement.",
    "Contact agence : renouvellement anticipé de carte bancaire sans contact et mise à jour du numéro de téléphone mobile.",
])


def build_aws_branches_table(
    agencies_df: pl.DataFrame, regions_df: pl.DataFrame
) -> pl.DataFrame:
    """Enrichit le référentiel des 450 agences avec le libellé région et le contrat PDF promo par défaut."""
    promo_ids = [
        f"PROMO-2026-{(i % NUM_PROMO_PDF_CONTRACTS) + 1:03d}"
        for i in range(agencies_df.height)
    ]
    return (
        agencies_df.join(regions_df.select(["region_code", "region_name"]), on="region_code", how="left")
        .with_columns(pl.Series("default_promo_contract_id", promo_ids))
        .select([
            "agency_num",
            "agency_code_4",
            "guichet_code_5",
            "city",
            "region_code",
            "region_name",
            "default_promo_contract_id",
        ])
    )


def build_aws_customers_table(
    rng: np.random.Generator,
    customers_df: pl.DataFrame,
    branches_df: pl.DataFrame,
) -> pl.DataFrame:
    """Construit la table CRM SaaS des 80 000 clients alignée à 100 % sur shared_universe."""
    n = customers_df.height
    ages = customers_df["age"].to_numpy()
    age_segments = np.where(
        ages <= 32,
        "18-32",
        np.where(ages <= 50, "33-50", np.where(ages <= 65, "51-65", "66+")),
    )

    incomes = np.where(
        ages <= 32,
        rng.normal(2350, 550, size=n).clip(1350, 5200),
        rng.normal(3400, 1100, size=n).clip(1500, 12000),
    ).round(0).astype(np.int64)
    incomes[WITNESS_CUST_IDX - 1] = 1850  # Lucas Martin (salaire net 1 850 €)

    digital_opt_in = rng.random(n) < 0.88
    digital_opt_in[WITNESS_CUST_IDX - 1] = True

    return (
        customers_df.join(
            branches_df.select(["guichet_code_5", "region_name", "city"]),
            on="guichet_code_5",
            how="left",
        )
        .with_columns([
            pl.Series("age_segment", age_segments),
            pl.Series("declared_monthly_income_eur", incomes),
            pl.col("birth_date").str.strptime(pl.Date, "%Y%m%d").alias("birth_date_iso"),
            pl.col("onboarding_date").str.strptime(pl.Date, "%Y%m%d").alias("onboarding_date_iso"),
            pl.lit(None, dtype=pl.Date).alias("closed_date"),
            pl.Series("digital_opt_in", digital_opt_in),
            pl.lit(datetime(2026, 11, 13, 14, 0, 0)).alias("crm_updated_at"),
        ])
        .select([
            "customer_id",
            "first_name",
            "last_name",
            "birth_date_iso",
            "age",
            "age_segment",
            "segment",
            "csp",
            "declared_monthly_income_eur",
            "region_code",
            "region_name",
            "agency_code_4",
            "guichet_code_5",
            "city",
            "onboarding_date_iso",
            "status",
            "closed_date",
            "digital_opt_in",
            "crm_updated_at",
        ])
        .rename({
            "birth_date_iso": "birth_date",
            "onboarding_date_iso": "onboarding_date",
            "status": "commercial_status",
        })
    )


def build_aws_account_portfolio(
    accounts_df: pl.DataFrame,
    branches_df: pl.DataFrame,
) -> pl.DataFrame:
    """
    Construit le portefeuille CRM des 95 000 comptes :
      - Mêmes account_id (ACC00000001..ACC00095000) et IBAN que le Mainframe
      - Exactement +15 000 ouvertures sur le trimestre, 0 clôture
      - Exactement 650 comptes récents créés sur AWS S3 pas encore réconciliés dans le Mainframe J-1
    """
    guichet_to_promo = dict(
        zip(
            branches_df["guichet_code_5"].to_list(),
            branches_df["default_promo_contract_id"].to_list(),
        )
    )

    guichets = accounts_df["guichet_code_5"].to_list()
    opened_in_q = accounts_df["is_opened_in_quarter"].to_list()
    is_orphan = accounts_df["is_aws_orphan"].to_list()

    promo_ids = [
        guichet_to_promo[g] if is_q else None
        for g, is_q in zip(guichets, opened_in_q)
    ]
    sources = [
        "SALESFORCE_BRANCH_REALTIME_PENDING_MF" if orph else "SALESFORCE_CRM_SYNC"
        for orph in is_orphan
    ]

    return (
        accounts_df.with_columns([
            pl.col("opening_date").str.strptime(pl.Date, "%Y%m%d").alias("opened_date"),
            pl.lit(None, dtype=pl.Date).alias("closed_date"),
            pl.Series("promo_contract_id", promo_ids),
            pl.Series("crm_sync_source", sources),
        ])
        .select([
            "account_id",
            "num_compte_11",
            "iban",
            "customer_id",
            "agency_code_4",
            "guichet_code_5",
            "account_type",
            "product_label",
            "rate_bps",
            "status",
            "opened_date",
            "closed_date",
            "is_opened_in_quarter",
            "promo_contract_id",
            "crm_sync_source",
        ])
        .rename({
            "status": "account_status",
            "is_opened_in_quarter": "opened_in_current_quarter",
        })
    )


def build_aws_interactions(
    rng: np.random.Generator,
    customers_raw_df: pl.DataFrame,
    leak_events_df: pl.DataFrame,
) -> pl.DataFrame:
    """Génère les 320 000 comptes-rendus de RDV agence & verbatims d'appels Call Center."""
    n = NUM_CRM_INTERACTIONS
    interaction_ids = [f"INT{i:08d}" for i in range(1, n + 1)]

    # Sur-pondération réaliste des clients qui effectuent effectivement des virements néobanques
    leaker_cust_indices = leak_events_df["cust_idx"].unique().to_numpy() - 1
    n_from_leakers = int(n * 0.35)
    n_from_all = n - n_from_leakers

    chosen_leakers = rng.choice(leaker_cust_indices, size=n_from_leakers, replace=True)
    chosen_general = rng.integers(0, N_CUSTOMERS_TOTAL, size=n_from_all)
    cust_zero_idx = np.concatenate([chosen_leakers, chosen_general])
    rng.shuffle(cust_zero_idx)

    # Forcer les 2 premières interactions sur Lucas Martin (CUST00002026)
    cust_zero_idx[0] = WITNESS_CUST_IDX - 1
    cust_zero_idx[1] = WITNESS_CUST_IDX - 1

    cust_ids = customers_raw_df["customer_id"].to_numpy()[cust_zero_idx]
    cust_ages = customers_raw_df["age"].to_numpy()[cust_zero_idx]
    cust_guichets = customers_raw_df["guichet_code_5"].to_numpy()[cust_zero_idx]

    channels = rng.choice(
        ["CALL_CENTER", "AGENCE_RDV", "MESSAGERIE_APP"],
        size=n,
        p=[0.46, 0.32, 0.22],
    )

    roll = rng.random(n)
    is_silent_churn_topic = np.where(cust_ages <= 32, roll < 0.44, roll < 0.09)
    is_promo_topic = (~is_silent_churn_topic) & (rng.random(n) < 0.18)

    topics = np.where(
        is_silent_churn_topic,
        "VIREMENT_INSTANTANE_PLAFOND_EPARGNE_EXTERNE",
        np.where(is_promo_topic, "OFFRE_PROMO_TAUX_BOOSTE_AGENCE", "SUIVI_COURANT_RELATION"),
    )

    verbatims = np.where(
        is_silent_churn_topic,
        VERBATIM_SILENT_CHURN_YOUNG[rng.integers(0, len(VERBATIM_SILENT_CHURN_YOUNG), size=n)],
        np.where(
            is_promo_topic,
            VERBATIM_PROMO_CONTRACTS[rng.integers(0, len(VERBATIM_PROMO_CONTRACTS), size=n)],
            VERBATIM_STANDARD_RETAIL[rng.integers(0, len(VERBATIM_STANDARD_RETAIL), size=n)],
        ),
    )

    # Verbatims témoin Lucas Martin (CUST00002026)
    channels[0] = "CALL_CENTER"
    topics[0] = "VIREMENT_INSTANTANE_PLAFOND_EPARGNE_EXTERNE"
    verbatims[0] = (
        "Appel Lucas Martin (27 ans, CUST00002026) : effectue chaque début de mois un virement SEPA Instant "
        "de 450 EUR vers Revolut (REVOLT21XXX) faute de suivi prédictif du budget et de livret boosté accessible en 1 clic."
    )
    channels[1] = "MESSAGERIE_APP"
    topics[1] = "SUIVI_COURANT_RELATION"
    verbatims[1] = (
        "Message application mobile : signale une hausse de +4 EUR sur son abonnement streaming (15,99 -> 19,99 EUR) "
        "et vérifie la réception d'un remboursement santé de +42 EUR."
    )

    end_ts = int(datetime.combine(DEMO_LIVE_DATE, datetime.min.time()).replace(hour=13, minute=45).timestamp())
    start_ts = int((datetime(2026, 11, 13, 13, 45) - timedelta(days=530)).timestamp())
    random_epoch_sec = rng.integers(start_ts, end_ts, size=n)
    random_epoch_sec.sort()

    sentiment = np.where(
        is_silent_churn_topic,
        "AT_RISK_LIQUIDITY_OUTFLOW",
        np.where(is_promo_topic, "PROMO_SENSITIVE", "NEUTRAL_SATISFIED"),
    )

    return pl.DataFrame({
        "interaction_id": interaction_ids,
        "customer_id": cust_ids,
        "guichet_code_5": cust_guichets,
        "interaction_ts": pl.from_epoch(pl.Series(random_epoch_sec), time_unit="s"),
        "channel": channels,
        "topic_code": topics,
        "advisor_sentiment_tag": sentiment,
        "verbatim_note": verbatims,
    })


def verify_aws_invariants(
    customers_df: pl.DataFrame,
    accounts_df: pl.DataFrame,
    interactions_df: pl.DataFrame,
    universe_accounts_df: pl.DataFrame,
) -> dict:
    """Vérifie strictement tous les invariants métier et l'alignement avec le Mainframe."""
    orphan_count = int((~universe_accounts_df["in_mainframe"]).sum())
    stats = {
        "seed": DEMO_SEED,
        "aligned_with_shared_universe": True,
        "witness_customer_id": "CUST00002026",
        "customers_count": customers_df.height,
        "distinct_regions": customers_df["region_code"].n_unique(),
        "distinct_branches": customers_df["guichet_code_5"].n_unique(),
        "customer_closures_quarter": customers_df.filter(pl.col("closed_date").is_not_null()).height,
        "young_18_32_customers": customers_df.filter(pl.col("age_segment") == "18-32").height,
        "accounts_total": accounts_df.height,
        "new_openings_quarter": accounts_df.filter(pl.col("opened_in_current_quarter")).height,
        "account_closures_quarter": accounts_df.filter(pl.col("closed_date").is_not_null()).height,
        "aws_orphan_accounts_vs_mainframe": orphan_count,
        "interactions_count": interactions_df.height,
        "distinct_promo_contracts_referenced": accounts_df.filter(
            pl.col("promo_contract_id").is_not_null()
        )["promo_contract_id"].n_unique(),
    }

    assert stats["customers_count"] == N_CUSTOMERS_TOTAL
    assert stats["distinct_regions"] == N_REGIONS
    assert stats["distinct_branches"] == N_AGENCIES
    assert stats["customer_closures_quarter"] == 0
    assert stats["accounts_total"] == N_ACCOUNTS_TOTAL
    assert stats["new_openings_quarter"] == N_RECENT_ACCOUNT_OPENINGS
    assert stats["account_closures_quarter"] == 0
    assert stats["aws_orphan_accounts_vs_mainframe"] == N_AWS_ORPHANS
    assert stats["interactions_count"] == NUM_CRM_INTERACTIONS
    assert stats["distinct_promo_contracts_referenced"] == NUM_PROMO_PDF_CONTRACTS

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère les fichiers Parquet du silo AWS CRM & Call Center (alignés sur shared_universe)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output" / "RAW" / "AWS",
        help="Répertoire local de sortie avant synchronisation GCS RAW/AWS",
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    universe = build_or_load_universe()
    rng = np.random.default_rng(DEMO_SEED + 101)

    out_dir: Path = args.output_dir
    for sub in ("crm_customers", "crm_account_portfolio", "crm_interactions", "crm_branches_ref"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    print(f"[generate_aws_crm_s3] Génération déterministe alignée sur shared_universe (seed={DEMO_SEED})...")
    branches_df = build_aws_branches_table(universe["agencies"], universe["regions"])
    customers_df = build_aws_customers_table(rng, universe["customers"], branches_df)
    accounts_df = build_aws_account_portfolio(universe["accounts"], branches_df)
    interactions_df = build_aws_interactions(rng, universe["customers"], universe["leak_events_90d"])

    stats = verify_aws_invariants(customers_df, accounts_df, interactions_df, universe["accounts"])

    branches_df.write_parquet(out_dir / "crm_branches_ref" / "part-00000.parquet", compression="zstd")
    customers_df.write_parquet(out_dir / "crm_customers" / "part-00000.parquet", compression="zstd")
    accounts_df.write_parquet(out_dir / "crm_account_portfolio" / "part-00000.parquet", compression="zstd")
    interactions_df.write_parquet(out_dir / "crm_interactions" / "part-00000.parquet", compression="zstd")

    (out_dir / "_manifest_aws_silo.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    elapsed = time.perf_counter() - t0
    print(f"[generate_aws_crm_s3] Terminé en {elapsed:.2f}s dans {out_dir}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
