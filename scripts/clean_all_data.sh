#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Nettoie toutes les données générées (localement et optionnellement sur GCS RAW/)
# Usage :
#   ./scripts/clean_all_data.sh              # Supprime output/ et data/universe/ en local
#   ./scripts/clean_all_data.sh --all        # Supprime local + gs://<bucket>/RAW/ (avec confirmation)
#   ./scripts/clean_all_data.sh --all --yes  # Supprime local + gs://<bucket>/RAW/ (sans prompt)
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/00_data_generator/output"
UNIVERSE_CACHE_DIR="${ROOT_DIR}/00_data_generator/data/universe"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

GCP_PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
CLEAN_GCS=false
AUTO_YES=false

for arg in "$@"; do
  case "$arg" in
    --all|--gcs)
      CLEAN_GCS=true
      ;;
    --yes|-y)
      AUTO_YES=true
      ;;
    *)
      echo "Option inconnue : $arg"
      echo "Usage : $0 [--all] [--yes]"
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo "[clean_all_data] Nettoyage des données générées"
echo "======================================================================"

if [[ -d "${OUTPUT_DIR}" ]]; then
  rm -rf "${OUTPUT_DIR}"
  echo "[clean_all_data] Dossier local supprimé : ${OUTPUT_DIR}"
else
  echo "[clean_all_data] Aucun dossier output/ à supprimer."
fi

if [[ -d "${UNIVERSE_CACHE_DIR}" ]]; then
  rm -rf "${UNIVERSE_CACHE_DIR}"
  echo "[clean_all_data] Cache univers supprimé : ${UNIVERSE_CACHE_DIR}"
fi

if [[ "${CLEAN_GCS}" == "true" ]]; then
  TARGET_URI="gs://${GCS_BUCKET_LANDING}/RAW"
  if [[ "${AUTO_YES}" != "true" ]]; then
    read -r -p "Confirmer la suppression de tous les objets sous ${TARGET_URI}/ (projet ${GCP_PROJECT_ID}) ? [y/N] " reply
    if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
      echo "[clean_all_data] Suppression GCS annulée."
      exit 0
    fi
  fi

  echo "[clean_all_data] Nettoyage GCS sous ${TARGET_URI}/..."
  if CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud storage ls "${TARGET_URI}/**" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
      gcloud storage rm --recursive "${TARGET_URI}" --project="${GCP_PROJECT_ID}"
    echo "[clean_all_data] Objets GCS sous ${TARGET_URI}/ supprimés."
  else
    echo "[clean_all_data] Aucun objet trouvé sous ${TARGET_URI}/."
  fi

  echo "[clean_all_data] Purge des files Cloud Pub/Sub (seek à maintenant)..."
  NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  for sub in sepa-payments-bq-historization-sub iban-beneficiary-bq-historization-sub sepa-payments-bq-raw-sub sepa-payments-alloydb-ops-sub sepa-payments-demo-tap-sub iban-beneficiary-bq-raw-sub sepa-payments-dlq-sub; do
    if CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
      gcloud pubsub subscriptions describe "${sub}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
      CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
        gcloud pubsub subscriptions seek "${sub}" --time="${NOW_UTC}" --project="${GCP_PROJECT_ID}" >/dev/null
      echo "  - File vidée : ${sub}"
    fi
  done

  echo "[clean_all_data] Purge des tables BigQuery d'historisation temps réel Pub/Sub..."
  bq --location=europe-west1 query --project_id="${GCP_PROJECT_ID}" --use_legacy_sql=false --label datacloud:antigravity \
    "TRUNCATE TABLE \`${GCP_PROJECT_ID}.raw_bank.raw_sepa_payments_pubsub_stream\`; TRUNCATE TABLE \`${GCP_PROJECT_ID}.raw_bank.raw_iban_events_pubsub_stream\`;" >/dev/null 2>&1 || true

  echo "[clean_all_data] Suppression de la table Finance SAP / ALM chargée directement (raw_bank.raw_sap_gl_alm)..."
  bq --location=europe-west1 rm -f -t "${GCP_PROJECT_ID}:raw_bank.raw_sap_gl_alm" >/dev/null 2>&1 || true
fi

echo "======================================================================"
echo "[clean_all_data] Nettoyage terminé."
echo "======================================================================"
