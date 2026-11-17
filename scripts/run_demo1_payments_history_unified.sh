#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Replay complet et idempotent — Historique Paiements 18 mois ↔ Temps réel Pub/Sub
#   1. Synchronisation de l'archive Parquet 100 % Nested STRUCT vers GCS RAW/PAYMENTS/
#   2. Exposition sans copie (BigLake) + vues unifiées raw_sepa_payments_unified / raw_iban_events_unified
#   3. Flux temps réel Pub/Sub + audit PII + CLS (appliqué aux 4 tables : historique & temps réel)
#   4. Certification SQL de la cohérence (continuité, fuite 2,42 Md€, rapprochement Mainframe CFONB)
#
# Usage :
#   ./scripts/run_demo1_payments_history_unified.sh                               # Tout rejouer (sans purge du temps réel)
#   ./scripts/run_demo1_payments_history_unified.sh --recreate-schema --burst 500 # Purge + nouveau tir temps réel
#   ./scripts/run_demo1_payments_history_unified.sh --skip-upload                 # Parquet déjà présent sur GCS
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
LOCAL_PAYMENTS_DIR="${ROOT_DIR}/00_data_generator/output/RAW/PAYMENTS"

SKIP_UPLOAD=false
PUBSUB_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upload)
      SKIP_UPLOAD=true
      shift
      ;;
    --recreate-schema)
      PUBSUB_ARGS+=("--recreate-schema")
      shift
      ;;
    --burst)
      PUBSUB_ARGS+=("--burst" "${2:-500}")
      shift 2
      ;;
    *)
      echo "Option inconnue : $1"
      echo "Usage : $0 [--skip-upload] [--recreate-schema] [--burst N]"
      exit 1
      ;;
  esac
done

render_sql() {
  sed \
    -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
    -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
    -e "s/__CONNECTION_ID__/${CONNECTION_ID}/g" \
    -e "s/__BUCKET_LANDING__/${GCS_BUCKET_LANDING}/g" \
    "$1"
}

run_bq_file() {
  render_sql "$1" | bq --location="${REGION}" query \
    --project_id="${PROJECT_ID}" \
    --use_legacy_sql=false \
    --label datacloud:antigravity
}

echo "======================================================================"
echo "[payments-unified] 1/4 Archive historique Parquet -> gs://${GCS_BUCKET_LANDING}/RAW/PAYMENTS/"
echo "======================================================================"
if [[ "${SKIP_UPLOAD}" == "true" ]]; then
  echo "[payments-unified] --skip-upload : synchronisation GCS ignorée."
else
  if [[ ! -d "${LOCAL_PAYMENTS_DIR}/sepa_payment_events" ]]; then
    uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_payments_stream.py"
  fi
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/validate_payments_coherence.py"
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud storage rsync --recursive --delete-unmatched-destination-objects \
    "${LOCAL_PAYMENTS_DIR}" "gs://${GCS_BUCKET_LANDING}/RAW/PAYMENTS" --project="${PROJECT_ID}"
fi

echo "======================================================================"
echo "[payments-unified] 2/4 Tables BigLake (zéro copie) + vues unifiées dans ${BQ_DATASET_RAW}"
echo "======================================================================"
run_bq_file "${ROOT_DIR}/01_demo1_raw_aggregation/sql/04_create_payments_history_biglake_unified.sql" >/dev/null
echo "[payments-unified] raw_sepa_payments_history, raw_iban_events_history, raw_sepa_payments_unified, raw_iban_events_unified OK"

echo "======================================================================"
echo "[payments-unified] 3/4 Temps réel Pub/Sub + audit PII + CLS (4 tables)"
echo "======================================================================"
"${ROOT_DIR}/scripts/run_demo1_pubsub_bq_cls.sh" "${PUBSUB_ARGS[@]+"${PUBSUB_ARGS[@]}"}"

echo "======================================================================"
echo "[payments-unified] 4/4 Certification de la cohérence Historique <-> Temps réel <-> Mainframe"
echo "======================================================================"
run_bq_file "${ROOT_DIR}/01_demo1_raw_aggregation/sql/05_verify_payments_unified.sql"
