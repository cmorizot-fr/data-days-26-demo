#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Lance toutes les générations déterministes de données (seed=2026)
# Usage :
#   ./scripts/generate_all_data.sh              # Génère en local + pousse dans GCS RAW/
#   ./scripts/generate_all_data.sh --local-only # Génère uniquement dans 00_data_generator/output/
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_RAW_DIR="${ROOT_DIR}/00_data_generator/output/RAW"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

GCP_PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
SYNC_GCS=true

for arg in "$@"; do
  case "$arg" in
    --local-only)
      SYNC_GCS=false
      ;;
    *)
      echo "Option inconnue : $arg"
      echo "Usage : $0 [--local-only]"
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo "[generate_all_data] Démarrage des générateurs Couche 0 (seed=2026)"
echo "======================================================================"

# 1. Silo AWS CRM & Call Center (Parquet / Iceberg)
uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_aws_crm_s3.py"

# 2. Silo Mainframe Core Banking CFONB 120 (branché dès création)
if [[ -f "${ROOT_DIR}/00_data_generator/generate_mainframe_cfonb.py" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_mainframe_cfonb.py"
fi

# 3. Silo Paiements Temps Réel SEPA Instant ISO 20022 (branché dès création)
if [[ -f "${ROOT_DIR}/00_data_generator/generate_payments_stream.py" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_payments_stream.py"
  # Cohérence historique <-> temps réel (contrat partagé payments_contract.py)
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/validate_payments_coherence.py"
fi

# 4. Silo Finance SAP / PCEC & ALM (branché dès création)
if [[ -f "${ROOT_DIR}/00_data_generator/generate_finance_sap_alm.py" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_finance_sap_alm.py"
fi

# 5. Silo Contrats & Avenants Promotionnels PDF (branché dès création)
if [[ -f "${ROOT_DIR}/00_data_generator/generate_promo_pdfs.py" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_promo_pdfs.py"
fi

# 6. Vérification croisée globale des invariants si disponible
if [[ -f "${ROOT_DIR}/00_data_generator/verify_invariants.py" ]]; then
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/verify_invariants.py"
fi

if [[ "${SYNC_GCS}" == "true" ]]; then
  echo "----------------------------------------------------------------------"
  echo "[generate_all_data] Synchronisation vers gs://${GCS_BUCKET_LANDING}/RAW/ (projet: ${GCP_PROJECT_ID})..."
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud storage rsync --recursive "${OUTPUT_RAW_DIR}" "gs://${GCS_BUCKET_LANDING}/RAW" --project="${GCP_PROJECT_ID}"
  echo "[generate_all_data] Synchronisation GCS terminée."

  # Silo Finance SAP / PCEC & ALM : chargement direct dans BigQuery raw_bank.raw_sap_gl_alm
  if [[ -f "${OUTPUT_RAW_DIR}/FINANCE_SAP_ALM/raw_sap_gl_alm.parquet" ]]; then
    "${ROOT_DIR}/scripts/load_finance_sap_bq.sh"
  fi

  # Silo SaaS CRM publié en vraies tables Apache Iceberg sur GCS (simulation du dépôt AWS Glue / S3)
  GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING}" uv run --project "${ROOT_DIR}" python \
    "${ROOT_DIR}/00_data_generator/publish_aws_crm_iceberg.py" \
    --warehouse "gs://${GCS_BUCKET_LANDING}/RAW/AWS_SAAS_ICEBERG"

  if [[ -x "${ROOT_DIR}/scripts/setup_pubsub_queues.sh" ]]; then
    "${ROOT_DIR}/scripts/setup_pubsub_queues.sh"
    uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/stream_payments_pubsub.py" --project-id "${GCP_PROJECT_ID}" --burst 300
    uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/stream_payments_pubsub.py" --project-id "${GCP_PROJECT_ID}" --witness-live
  fi
else
  echo "[generate_all_data] Mode --local-only : synchronisation GCS et Pub/Sub ignorées."
fi

echo "======================================================================"
echo "[generate_all_data] Toutes les données disponibles ont été générées."
echo "======================================================================"
