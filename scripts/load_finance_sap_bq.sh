#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Charge directement le silo Finance SAP / PCEC & ALM dans BigQuery
#   gs://<bucket>/RAW/FINANCE_SAP_ALM/raw_sap_gl_alm.parquet -> <projet>.raw_bank.raw_sap_gl_alm
# (préparé en coulisses : la Démo #1 ne met pas en scène l'ingestion de ce silo)
#
# Prérequis : ./scripts/generate_all_data.sh (génération + rsync GCS RAW/)
# Usage     : ./scripts/load_finance_sap_bq.sh
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_DIR="${ROOT_DIR}/00_data_generator/output/bq_schemas"
TABLE_NAME="raw_sap_gl_alm"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

GCP_PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"
BQ_LOCATION="${BQ_LOCATION:-europe-west1}"

SOURCE_URI="gs://${GCS_BUCKET_LANDING}/RAW/FINANCE_SAP_ALM/${TABLE_NAME}.parquet"
TARGET_TABLE="${GCP_PROJECT_ID}:${BQ_DATASET_RAW}.${TABLE_NAME}"

if [[ ! -f "${SCHEMA_DIR}/${TABLE_NAME}.json" ]]; then
  echo "[load_finance_sap_bq] Schéma absent (${SCHEMA_DIR}/${TABLE_NAME}.json) : lancer d'abord generate_finance_sap_alm.py"
  exit 1
fi

echo "[load_finance_sap_bq] bq load ${SOURCE_URI} -> ${TARGET_TABLE} (${BQ_LOCATION})..."
bq --location="${BQ_LOCATION}" load \
  --project_id="${GCP_PROJECT_ID}" \
  --label datacloud:antigravity \
  --replace \
  --source_format=PARQUET \
  "${TARGET_TABLE}" \
  "${SOURCE_URI}"

echo "[load_finance_sap_bq] Documentation des colonnes & de la table (Knowledge Catalog)..."
bq --location="${BQ_LOCATION}" update \
  --project_id="${GCP_PROJECT_ID}" \
  --set_label datacloud:antigravity \
  --set_label silo:finance_sap_alm \
  --description "$(cat "${SCHEMA_DIR}/${TABLE_NAME}.description.txt")" \
  --schema "${SCHEMA_DIR}/${TABLE_NAME}.json" \
  "${TARGET_TABLE}"

echo "[load_finance_sap_bq] Contrôle des invariants PNB dans BigQuery..."
bq --location="${BQ_LOCATION}" query \
  --project_id="${GCP_PROJECT_ID}" \
  --label datacloud:antigravity \
  --use_legacy_sql=false \
  "SELECT
     COUNT(*) AS n_rows,                                   -- 1 200 000
     SUM(gross_amount_eur) AS naive_sum_gross_eur,         -- +42 800 000.00
     SUM(IF(NOT STARTS_WITH(pcec_account, '58'),
            gross_amount_eur * IF(sens_dc = 'D', -1, 1), 0)) AS signed_gl_net_excl_58_eur  -- -24 120 000.00
   FROM \`${GCP_PROJECT_ID}.${BQ_DATASET_RAW}.${TABLE_NAME}\`"

echo "[load_finance_sap_bq] Table ${TARGET_TABLE} chargée."
