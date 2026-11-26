"""
Génère et publie à la volée une table Apache Iceberg de 100 000 000 de lignes
(`crm_digital_clickstream_events`) directement sur AWS S3 (`eu-west-1`) et AWS Glue
(`crm_callcenter_db`), hors flux SILVER/dbt, pour démontrer en direct dans BigQuery Studio
la capacité à requêter et joindre de gros volumes cross-cloud (AWS S3 <-> GCP BigQuery)
et l'effet du Cross-Cloud Caching.

Usage :
  uv run python 01_demo1_raw_aggregation/publish_aws_clickstream_100m.py
  uv run python 01_demo1_raw_aggregation/publish_aws_clickstream_100m.py --rows 100000000 --batch-rows 5000000
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv
import numpy as np
import pyarrow as pa
from pyiceberg.catalog.glue import GlueCatalog
from pyiceberg.exceptions import NoSuchTableError

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLE_NAME = "crm_digital_clickstream_events"

CHANNELS = pa.array(["MOBILE_IOS", "MOBILE_ANDROID", "WEB_DESKTOP"])
EVENT_TYPES = pa.array(
    [
        "VIEW_BALANCE",
        "COMPARE_SAVINGS_RATE",
        "SIMULATE_LIVRET",
        "ADD_EXTERNAL_NEOBANK_IBAN",
        "INITIATE_SEPA_TRANSFER",
        "VIEW_FEE_SCHEDULE",
    ]
)
COMPETITORS = pa.array(["NONE", "REVOLUT", "TRADE_REPUBLIC", "N26", "BOURSO", "DEGIRO"])
MONTHS = pa.array(
    [
        "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
        "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05",
        "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11",
    ]
)
COUNTRIES = pa.array(["FR", "BE", "LU", "DE", "ES"])

# Pool pré-calculé des 80 000 identifiants clients (CUST00000001..CUST00080000)
# pour permettre une jointure 100 % réelle avec raw_bank.cbk_customers_ref sur GCP !
CUSTOMER_POOL = pa.array([f"CUST{i:08d}" for i in range(1, 80_001)])

ARROW_SCHEMA = pa.schema(
    [
        pa.field("event_seq_id", pa.int64(), nullable=False),
        pa.field("event_ts", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("event_month", pa.string(), nullable=False),
        pa.field("customer_id", pa.string(), nullable=False),
        pa.field("channel", pa.string(), nullable=False),
        pa.field("event_type", pa.string(), nullable=False),
        pa.field("target_competitor", pa.string(), nullable=False),
        pa.field("simulated_amount_eur", pa.float64(), nullable=False),
        pa.field("latency_ms", pa.int32(), nullable=False),
        pa.field("country_iso", pa.string(), nullable=False),
    ]
)

COLUMN_DOCS = {
    "event_seq_id": "Identifiant séquentiel unique de l'événement digital (1 à 100 000 000).",
    "event_ts": "Horodatage UTC de l'événement web/mobile enregistré sur AWS.",
    "event_month": "Mois de l'événement au format AAAA-MM ('2025-06' à '2026-11').",
    "customer_id": "Identifiant client Banque Hexagone (CUST00000001..CUST00080000), joignable avec GCP raw_bank.cbk_customers_ref.",
    "channel": "Canal digital ('MOBILE_IOS', 'MOBILE_ANDROID', 'WEB_DESKTOP').",
    "event_type": "Type d'action ('VIEW_BALANCE', 'COMPARE_SAVINGS_RATE', 'SIMULATE_LIVRET', 'ADD_EXTERNAL_NEOBANK_IBAN', 'INITIATE_SEPA_TRANSFER', 'VIEW_FEE_SCHEDULE').",
    "target_competitor": "Néobanque ou courtier consulté/ciblé ('REVOLUT', 'TRADE_REPUBLIC', 'N26', 'BOURSO', 'DEGIRO', ou 'NONE').",
    "simulated_amount_eur": "Montant simulé ou préparé en euros (0.0 si simple consultation).",
    "latency_ms": "Temps de réponse API front-end en millisecondes.",
    "country_iso": "Pays de connexion ISO-2 ('FR', 'BE', 'LU', 'DE', 'ES').",
}


def generate_batch(offset: int, n: int, seed: int) -> pa.Table:
    """Génère en mémoire un bloc vectorisé de `n` lignes (~110 Mo compressé)."""
    rng = np.random.default_rng(seed)

    seq = np.arange(offset + 1, offset + n + 1, dtype=np.int64)
    # Plage 2025-06-01T00:00:00Z (1748736000s) -> 2026-11-12T23:59:59Z (1794527999s)
    ts_us = rng.integers(1_748_736_000, 1_794_528_000, size=n, dtype=np.int64) * 1_000_000
    month_idx = ((ts_us // 1_000_000 - 1_748_736_000) * 18 // (1_794_528_000 - 1_748_736_000)).clip(0, 17).astype(np.int32)

    cust_idx = rng.integers(0, 80_000, size=n, dtype=np.int32)
    chan_idx = rng.choice(3, size=n, p=[0.48, 0.37, 0.15]).astype(np.int32)
    evt_idx = rng.choice(6, size=n, p=[0.52, 0.16, 0.12, 0.06, 0.08, 0.06]).astype(np.int32)
    comp_idx = np.where(
        evt_idx >= 2,
        rng.choice(6, size=n, p=[0.40, 0.22, 0.21, 0.07, 0.06, 0.04]),
        0,
    ).astype(np.int32)

    amt = np.where(
        (evt_idx == 2) | (evt_idx == 4),
        np.round(rng.lognormal(mean=7.2, sigma=1.1, size=n).clip(50.0, 50_000.0), 2),
        0.0,
    )
    latency = rng.integers(14, 480, size=n, dtype=np.int32)
    country_idx = rng.choice(5, size=n, p=[0.91, 0.03, 0.02, 0.02, 0.02]).astype(np.int32)

    return pa.Table.from_arrays(
        [
            pa.array(seq, type=pa.int64()),
            pa.array(ts_us, type=pa.timestamp("us", tz="UTC")),
            MONTHS.take(pa.array(month_idx)),
            CUSTOMER_POOL.take(pa.array(cust_idx)),
            CHANNELS.take(pa.array(chan_idx)),
            EVENT_TYPES.take(pa.array(evt_idx)),
            COMPETITORS.take(pa.array(comp_idx)),
            pa.array(amt, type=pa.float64()),
            pa.array(latency, type=pa.int32()),
            COUNTRIES.take(pa.array(country_idx)),
        ],
        schema=ARROW_SCHEMA,
    )


def document_in_glue(aws_region: str, glue_db: str) -> None:
    """Ajoute la description de table et des 10 colonnes dans AWS Glue Data Catalog."""
    glue = boto3.client("glue", region_name=aws_region)
    tbl = glue.get_table(DatabaseName=glue_db, Name=TABLE_NAME)["Table"]
    table_input = {
        k: tbl[k]
        for k in (
            "Name",
            "Description",
            "Owner",
            "Retention",
            "StorageDescriptor",
            "PartitionKeys",
            "TableType",
            "Parameters",
        )
        if k in tbl
    }
    desc = (
        "Télémétrie digitale web & mobile Banque Hexagone sur AWS S3 (100 000 000 d'événements Iceberg) — "
        "table de benchmark volumétrique Cross-Cloud Lakehouse (AWS eu-west-1 <-> GCP europe-west1)."
    )
    table_input["Description"] = desc
    table_input.setdefault("Parameters", {})["comment"] = desc
    for col in table_input.get("StorageDescriptor", {}).get("Columns", []):
        if col["Name"] in COLUMN_DOCS:
            col["Comment"] = COLUMN_DOCS[col["Name"]]
    glue.update_table(DatabaseName=glue_db, TableInput=table_input)


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.aws.local", override=True)

    parser = argparse.ArgumentParser(description="Publie 100M de lignes Iceberg sur AWS S3 / Glue.")
    parser.add_argument("--rows", type=int, default=100_000_000)
    parser.add_argument("--batch-rows", type=int, default=5_000_000)
    parser.add_argument("--aws-region", default=os.getenv("AWS_REGION", "eu-west-1"))
    parser.add_argument("--glue-db", default=os.getenv("AWS_GLUE_DATABASE", "crm_callcenter_db"))
    parser.add_argument("--s3-bucket", default=os.getenv("AWS_S3_BUCKET_CRM", "data-days-demo-aws-crm-835872720625"))
    args = parser.parse_args()

    os.environ.setdefault("AWS_DEFAULT_REGION", args.aws_region)
    warehouse = f"s3://{args.s3_bucket}/RAW/AWS_SAAS_ICEBERG"
    catalog = GlueCatalog(
        "aws_crm_saas",
        **{
            "warehouse": warehouse,
            "glue.region": args.aws_region,
            "s3.region": args.aws_region,
            "write.parquet.compression-codec": "zstd",
        },
    )

    identifier = f"{args.glue_db}.{TABLE_NAME}"
    try:
        catalog.drop_table(identifier)
        print(f"♻️  Ancienne table {identifier} supprimée du catalogue Glue.")
    except NoSuchTableError:
        pass

    tbl = catalog.create_table(
        identifier=identifier,
        schema=ARROW_SCHEMA,
        location=f"{warehouse}/{args.glue_db}.db/{TABLE_NAME}",
        properties={
            "write.parquet.compression-codec": "zstd",
            "comment": "Télémétrie digitale 100M événements (benchmark Cross-Cloud AWS S3 <-> BigQuery).",
        },
    )
    print(f"🚀 Table Iceberg créée : {identifier} -> écriture de {args.rows:,} lignes par lots de {args.batch_rows:,}...")

    t0 = time.time()
    written = 0
    batch_idx = 0
    while written < args.rows:
        chunk_n = min(args.batch_rows, args.rows - written)
        t_batch = time.time()
        pa_batch = generate_batch(offset=written, n=chunk_n, seed=2026 + batch_idx)
        tbl.append(pa_batch)
        written += chunk_n
        batch_idx += 1
        elapsed = time.time() - t0
        rate = written / max(elapsed, 0.1)
        print(
            f"  ✅ Lot {batch_idx:02d} : +{chunk_n:,} lignes uploadées en {time.time() - t_batch:.1f}s "
            f"(cumul : {written:,} / {args.rows:,} · {rate:,.0f} lignes/s)"
        )

    document_in_glue(args.aws_region, args.glue_db)
    print(f"\n🎉 Terminé en {time.time() - t0:.1f}s : {written:,} lignes publiées et documentées dans AWS Glue ({identifier}) !")


if __name__ == "__main__":
    main()
