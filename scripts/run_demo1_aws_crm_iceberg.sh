#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Replay complet et idempotent — Silo SaaS CRM & Call Center en Apache Iceberg sur GCS
# (simulation du dépôt Iceberg de l'éditeur SaaS, en attendant la fédération AWS Glue / S3)
#   1. Génération des Parquet sources alignés sur shared_universe (si absents)
#   2. Publication en vraies tables Iceberg (PyIceberg) sous gs://<bucket>/RAW/AWS_SAAS_ICEBERG/
#   3. Exposition dans BigQuery en tables BigLake Iceberg (lecture seule, zéro copie) : raw_bank.aws_crm_*
#   4. Certification SQL (invariants CRM + alignement Mainframe)
#
# Usage :
#   ./scripts/run_demo1_aws_crm_iceberg.sh
#   ./scripts/run_demo1_aws_crm_iceberg.sh --regenerate   # Régénère aussi les Parquet sources
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
CONNECTION_ID="${PROJECT_ID}.${REGION}.biglake-gcs-conn"
SOURCE_DIR="${ROOT_DIR}/00_data_generator/output/RAW/AWS"
TABLES_JSON="${ROOT_DIR}/00_data_generator/output/iceberg_catalog/aws_crm_iceberg_tables.json"

REGENERATE=false
for arg in "$@"; do
  case "$arg" in
    --regenerate) REGENERATE=true ;;
    *) echo "Option inconnue : $arg"; echo "Usage : $0 [--regenerate]"; exit 1 ;;
  esac
done

echo "======================================================================"
echo "[aws-crm-iceberg] 1/4 Parquet sources CRM (shared_universe, seed=2026)"
echo "======================================================================"
if [[ "${REGENERATE}" == "true" || ! -f "${SOURCE_DIR}/crm_customers/part-00000.parquet" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_aws_crm_s3.py"
else
  echo "[aws-crm-iceberg] Parquet sources déjà présents (${SOURCE_DIR})."
fi

echo "======================================================================"
echo "[aws-crm-iceberg] 2/4 Publication Iceberg -> gs://${GCS_BUCKET_LANDING}/RAW/AWS_SAAS_ICEBERG/"
echo "======================================================================"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING}" uv run --project "${ROOT_DIR}" python \
  "${ROOT_DIR}/00_data_generator/publish_aws_crm_iceberg.py" \
  --warehouse "gs://${GCS_BUCKET_LANDING}/RAW/AWS_SAAS_ICEBERG"

echo "======================================================================"
echo "[aws-crm-iceberg] 3/4 Tables BigLake Iceberg (lecture seule) dans ${BQ_DATASET_RAW}"
echo "======================================================================"
DDL="$(uv run --project "${ROOT_DIR}" python - "${TABLES_JSON}" "${PROJECT_ID}" "${BQ_DATASET_RAW}" "${CONNECTION_ID}" <<'PY'
import json, sys
tables_json, project, dataset, connection = sys.argv[1:5]
descriptions = {
    "crm_customers": "Clients du SaaS CRM (80 000, dont 650 créés en agence absents du Mainframe J-1). Table Apache Iceberg déposée par l'éditeur SaaS sur GCS (simulation du catalogue AWS Glue / S3).",
    "crm_account_portfolio": "Portefeuille de comptes du SaaS CRM (95 000 : 0 clôture, +15 000 ouvertures trimestre, 650 orphelins vs Mainframe). Table Apache Iceberg (simulation AWS Glue / S3).",
    "crm_interactions": "320 000 comptes-rendus de RDV agence et verbatims Call Center (texte libre, données personnelles). Table Apache Iceberg (simulation AWS Glue / S3).",
    "crm_branches_ref": "Référentiel des 450 agences et 8 régions commerciales du SaaS CRM. Table Apache Iceberg (simulation AWS Glue / S3).",
}
meta = json.load(open(tables_json))["tables"]
stmts = []
for name, info in meta.items():
    stmts.append(
        f"CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.aws_{name}`\n"
        f"WITH CONNECTION `{connection}`\n"
        f"OPTIONS (format = 'ICEBERG', uris = ['{info['metadata_location']}'], "
        f"description = \"{descriptions[name]} Snapshot Iceberg {info['snapshot_id']}.\");"
    )
print("\n".join(stmts))
PY
)"
echo "${DDL}" | bq --location="${REGION}" query \
  --project_id="${PROJECT_ID}" \
  --use_legacy_sql=false \
  --label datacloud:antigravity >/dev/null
echo "[aws-crm-iceberg] aws_crm_customers, aws_crm_account_portfolio, aws_crm_interactions, aws_crm_branches_ref OK"

echo "======================================================================"
echo "[aws-crm-iceberg] 4/4 Certification CRM Iceberg <-> Mainframe"
echo "======================================================================"
sed \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
  "${ROOT_DIR}/01_demo1_raw_aggregation/sql/06_verify_aws_crm_iceberg.sql" \
  | bq --location="${REGION}" query \
      --project_id="${PROJECT_ID}" \
      --use_legacy_sql=false \
      --label datacloud:antigravity
