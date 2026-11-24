"""
Publie le silo SaaS CRM & Call Center (Salesforce-like) en VRAIES tables Apache Iceberg sur GCS.

Simule le dépôt Iceberg qu'opère l'éditeur SaaS sur son object storage (en attendant la
fédération du catalogue AWS Glue / S3) : fichiers de données Parquet + métadonnées Iceberg
(metadata.json, manifest lists, manifests, snapshots) écrits avec PyIceberg directement sous
`gs://<bucket>/RAW/AWS_SAAS_ICEBERG/`, référencés par un catalogue SQL local (SQLite).

Source : les fichiers Parquet produits par `generate_aws_crm_s3.py` (alignés sur shared_universe).
Chaque exécution publie un nouveau snapshot (overwrite) : idempotent, historique Iceberg conservé.

Sortie : `00_data_generator/output/iceberg_catalog/aws_crm_iceberg_tables.json`
         (emplacement du metadata.json courant de chaque table, consommé par le script BigQuery).

Usage :
  uv run python 00_data_generator/publish_aws_crm_iceberg.py
  uv run python 00_data_generator/publish_aws_crm_iceberg.py --warehouse gs://mon-bucket/RAW/AWS_SAAS_ICEBERG
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
import polars as pl
import pyarrow as pa
from pyiceberg.catalog import Catalog
from pyiceberg.catalog.glue import GlueCatalog
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import NoSuchTableError

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_SOURCE_DIR = BASE_DIR / "output" / "RAW" / "AWS"
DEFAULT_CATALOG_DIR = BASE_DIR / "output" / "iceberg_catalog"
DEFAULT_BUCKET = os.getenv("GCS_BUCKET_LANDING", "data-days-demo-landing")
NAMESPACE = "crm_saas"

# table Iceberg -> (dossier Parquet source, colonnes horodatées à normaliser en UTC)
TABLES: dict[str, tuple[str, list[str]]] = {
    "crm_branches_ref": ("crm_branches_ref", []),
    "crm_customers": ("crm_customers", ["crm_updated_at"]),
    "crm_account_portfolio": ("crm_account_portfolio", []),
    "crm_interactions": ("crm_interactions", ["interaction_ts"]),
}


def gcloud_access_token() -> str | None:
    """Jeton OAuth2 de la session gcloud active (None si gcloud indisponible)."""
    try:
        res = subprocess.run(
            ["gcloud", "auth", "print-access-token", "--quiet"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout.strip() or None if res.returncode == 0 else None


def load_arrow(source_dir: Path, folder: str, ts_cols: list[str]) -> pa.Table:
    """Charge le Parquet source ; horodatages -> UTC (Iceberg timestamptz = BigQuery TIMESTAMP)."""
    df = pl.read_parquet(source_dir / folder / "*.parquet")
    if ts_cols:
        df = df.with_columns([pl.col(c).dt.replace_time_zone("UTC") for c in ts_cols])
    # Types Arrow standards (string plutôt que string_view) pour une compatibilité Iceberg maximale
    return df.to_arrow(compat_level=pl.CompatLevel.oldest())


def build_catalog(args: argparse.Namespace) -> tuple[Catalog, str, str]:
    """Construit le catalogue PyIceberg (SqlCatalog GCS ou GlueCatalog AWS S3)."""
    if args.catalog == "glue":
        aws_bucket = os.getenv("AWS_S3_BUCKET_CRM", "data-days-demo-aws-crm-835872720625")
        warehouse = args.warehouse or f"s3://{aws_bucket}/RAW/AWS_SAAS_ICEBERG"
        namespace = args.namespace or os.getenv("AWS_GLUE_DATABASE", "crm_callcenter_db")
        os.environ.setdefault("AWS_DEFAULT_REGION", args.aws_region)
        catalog = GlueCatalog(
            "aws_crm_saas",
            **{
                "warehouse": warehouse,
                "glue.region": args.aws_region,
                "s3.region": args.aws_region,
            },
        )
        return catalog, warehouse, namespace

    warehouse = args.warehouse or f"gs://{DEFAULT_BUCKET}/RAW/AWS_SAAS_ICEBERG"
    namespace = args.namespace or NAMESPACE
    args.catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_props = {
        "uri": f"sqlite:///{args.catalog_dir / 'aws_crm_saas_catalog.db'}",
        "warehouse": warehouse,
    }
    token = gcloud_access_token()
    if token:
        # Jeton OAuth de la session gcloud active (évite une ré-authentification ADC)
        catalog_props["gcs.oauth2.token"] = token
        catalog_props["gcs.oauth2.token-expires-at"] = str(int((time.time() + 3000) * 1000))
    return SqlCatalog("aws_crm_saas", **catalog_props), warehouse, namespace


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.aws.local", override=True)

    parser = argparse.ArgumentParser(description="Publie le CRM SaaS en tables Iceberg (GCS ou AWS S3/Glue).")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    parser.add_argument("--catalog", choices=["sqlite", "glue"], default="sqlite")
    parser.add_argument("--warehouse", default=None, help="Racine du warehouse Iceberg (gs://... ou s3://...)")
    parser.add_argument("--namespace", default=None, help="Namespace / base Glue cible")
    parser.add_argument("--aws-region", default=os.getenv("AWS_REGION", "eu-west-1"))
    args = parser.parse_args()

    t0 = time.perf_counter()
    catalog, warehouse, namespace = build_catalog(args)
    catalog.create_namespace_if_not_exists(namespace)

    published: dict[str, dict] = {}
    for table_name, (folder, ts_cols) in TABLES.items():
        arrow_tbl = load_arrow(args.source_dir, folder, ts_cols)
        identifier = f"{namespace}.{table_name}"
        try:
            table = catalog.load_table(identifier)
            try:
                table.overwrite(arrow_tbl)
                action = "overwrite (nouveau snapshot)"
            except ValueError:
                # Schéma source modifié : recréation propre de la table
                catalog.drop_table(identifier)
                table = catalog.create_table(identifier, schema=arrow_tbl.schema)
                table.append(arrow_tbl)
                action = "recreate (schéma modifié)"
        except NoSuchTableError:
            table = catalog.create_table(identifier, schema=arrow_tbl.schema)
            table.append(arrow_tbl)
            action = "create"

        table = catalog.load_table(identifier)
        snapshot = table.current_snapshot()
        published[table_name] = {
            "identifier": identifier,
            "location": table.location(),
            "metadata_location": table.metadata_location,
            "snapshot_id": snapshot.snapshot_id if snapshot else None,
            "snapshots_count": len(table.metadata.snapshots),
            "rows": arrow_tbl.num_rows,
            "action": action,
        }
        print(f"[iceberg] {identifier:<32} {arrow_tbl.num_rows:>8,} lignes · {action}")
        print(f"          {table.metadata_location}")

    args.catalog_dir.mkdir(parents=True, exist_ok=True)
    out_name = "aws_crm_glue_iceberg_tables.json" if args.catalog == "glue" else "aws_crm_iceberg_tables.json"
    out_file = args.catalog_dir / out_name
    out_file.write_text(json.dumps({"catalog": args.catalog, "warehouse": warehouse, "tables": published}, indent=2), encoding="utf-8")
    print(f"[iceberg] Publication terminée en {time.perf_counter() - t0:.2f}s -> {out_file}")


if __name__ == "__main__":
    main()
