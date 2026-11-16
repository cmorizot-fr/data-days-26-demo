#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Replay complet et idempotent — Démo #1 · Étape 4 :
#   1. Files Pub/Sub & BigQuery Subscriptions 100 % Nested STRUCT (--use-table-schema)
#   2. Injection temps réel (burst + témoin Lucas Martin CUST00002026)
#   3. Audit hybride PII sur les sous-champs STRUCT (sans extraction brute)
#   4. Taxonomie Policy Tags + 3 Data Policies CLS (LAST_FOUR_CHARACTERS, SHA256, ALWAYS_NULL)
#   5. Contrôle SQL du masquage dynamique granulaire en lecture
#
# Usage :
#   ./scripts/run_demo1_pubsub_bq_cls.sh
#   ./scripts/run_demo1_pubsub_bq_cls.sh --recreate-schema --burst 500
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"

RECREATE_FLAG=""
BURST_COUNT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recreate-schema)
      RECREATE_FLAG="--recreate-schema"
      shift
      ;;
    --burst)
      BURST_COUNT="${2:-500}"
      shift 2
      ;;
    *)
      echo "Option inconnue : $1"
      echo "Usage : $0 [--recreate-schema] [--burst N]"
      exit 1
      ;;
  esac
done

run_gcloud() {
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud --quiet "$@"
}

echo "======================================================================"
echo "[demo1-step4] 1/5 Activation des APIs Data Catalog & BigQuery Data Policy..."
echo "======================================================================"
run_gcloud services enable \
  datacatalog.googleapis.com \
  bigquerydatapolicy.googleapis.com \
  pubsub.googleapis.com \
  bigquery.googleapis.com \
  --project="${PROJECT_ID}"

echo "======================================================================"
echo "[demo1-step4] 2/5 Provisionnement Pub/Sub -> BigQuery Nested STRUCT..."
echo "======================================================================"
if [[ -n "${RECREATE_FLAG}" ]]; then
  "${ROOT_DIR}/scripts/setup_pubsub_queues.sh" "${RECREATE_FLAG}"
else
  "${ROOT_DIR}/scripts/setup_pubsub_queues.sh"
fi

if [[ "${BURST_COUNT}" -gt 0 ]]; then
  echo "[demo1-step4] Injection live de ${BURST_COUNT} paiements + événements témoin Lucas Martin..."
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/stream_payments_pubsub.py" \
    --project-id "${PROJECT_ID}" --region "${REGION}" --burst "${BURST_COUNT}"
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/stream_payments_pubsub.py" \
    --project-id "${PROJECT_ID}" --region "${REGION}" --witness-live
fi

echo "======================================================================"
echo "[demo1-step4] 3/5 Audit Hybride PII sur les chemins Nested STRUCT..."
echo "======================================================================"
sed \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
  "${ROOT_DIR}/01_demo1_raw_aggregation/sql/03_audit_pii_nested_pubsub.sql" \
  | bq --location="${REGION}" query \
      --project_id="${PROJECT_ID}" \
      --use_legacy_sql=false \
      --label datacloud:antigravity

echo "======================================================================"
echo "[demo1-step4] 4/5 Déploiement Taxonomie & Policy Tags CLS sur les STRUCT..."
echo "======================================================================"
uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/scripts/apply_pubsub_cls_policy_tags.py" \
  --project-id "${PROJECT_ID}" \
  --location "${REGION}" \
  --dataset "${BQ_DATASET_RAW}"

echo "======================================================================"
echo "[demo1-step4] 5/5 Vérification SQL du masquage dynamique CLS en direct..."
echo "======================================================================"
bq --location="${REGION}" query \
  --project_id="${PROJECT_ID}" \
  --use_legacy_sql=false \
  --label datacloud:antigravity \
  "SELECT
     header.end_to_end_id,
     settlement.payment_scheme,
     settlement.tx_status,
     instructed_amount.amount_eur,
     debtor.customer_id,
     debtor.iban AS debtor_iban_cls,
     SUBSTR(debtor.full_name, 1, 16) || '...' AS debtor_name_sha256,
     creditor.agent_bic,
     creditor.iban AS creditor_iban_cls,
     remittance.unstructured_info AS remittance_redacted
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.raw_sepa_payments_pubsub_stream\`
   WHERE debtor.customer_id = 'CUST00002026'
   ORDER BY header.end_to_end_id;"
