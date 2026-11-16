#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Prépare les Topics, Subscriptions Pull et Subscriptions BigQuery natives
# (`--use-table-schema` + `--write-metadata`) en schéma 100 % Nested (STRUCT)
# sur data-days-demo (europe-west1).
#
# Usage :
#   ./scripts/setup_pubsub_queues.sh                    # Idempotent (auto-migre si legacy JSON détecté)
#   ./scripts/setup_pubsub_queues.sh --recreate-schema  # Force la recréation des tables & BQ Subscriptions
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"
DDL_TEMPLATE="${ROOT_DIR}/01_demo1_raw_aggregation/sql/02_create_documented_pubsub_nested_tables.sql"

RECREATE_SCHEMA=false
for arg in "$@"; do
  case "$arg" in
    --recreate-schema)
      RECREATE_SCHEMA=true
      ;;
    *)
      echo "Option inconnue : $arg"
      echo "Usage : $0 [--recreate-schema]"
      exit 1
      ;;
  esac
done

TOPIC_PAYMENTS="sepa-payments-pacs008-topic"
TOPIC_IBAN="iban-beneficiary-events-topic"
TOPIC_DLQ="sepa-payments-dlq-topic"

SUB_BQ_HIST_PAYMENTS="sepa-payments-bq-historization-sub"
SUB_BQ_HIST_IBAN="iban-beneficiary-bq-historization-sub"
SUB_BQ_RAW="sepa-payments-bq-raw-sub"
SUB_ALLOYDB_OPS="sepa-payments-alloydb-ops-sub"
SUB_DEMO_TAP="sepa-payments-demo-tap-sub"
SUB_IBAN_RAW="iban-beneficiary-bq-raw-sub"
SUB_DLQ="sepa-payments-dlq-sub"

BQ_TABLE_PAYMENTS_STREAM="raw_sepa_payments_pubsub_stream"
BQ_TABLE_IBAN_STREAM="raw_iban_events_pubsub_stream"

run_gcloud() {
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud --quiet "$@"
}

create_topic_if_missing() {
  local topic_name="$1"
  if run_gcloud pubsub topics describe "${topic_name}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "[pubsub] Topic déjà présent : ${topic_name}"
  else
    echo "[pubsub] Création du topic : ${topic_name} (région ${REGION})..."
    run_gcloud pubsub topics create "${topic_name}" \
      --project="${PROJECT_ID}" \
      --message-storage-policy-allowed-regions="${REGION}" \
      --labels="datacloud=antigravity,domain=payments,env=demo2026"
  fi
}

create_sub_if_missing() {
  local sub_name="$1"
  local topic_name="$2"
  shift 2
  if run_gcloud pubsub subscriptions describe "${sub_name}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "[pubsub] Subscription déjà présente : ${sub_name}"
  else
    echo "[pubsub] Création de la file (subscription) : ${sub_name} -> ${topic_name}..."
    run_gcloud pubsub subscriptions create "${sub_name}" \
      --project="${PROJECT_ID}" \
      --topic="${topic_name}" \
      --labels="datacloud=antigravity,domain=payments,env=demo2026" \
      "$@"
  fi
}

echo "======================================================================"
echo "[setup_pubsub_queues] Provisionnement Pub/Sub & BigQuery Nested STRUCT (${PROJECT_ID} · ${REGION})"
echo "======================================================================"

run_gcloud services enable pubsub.googleapis.com bigquery.googleapis.com cloudresourcemanager.googleapis.com \
  --project="${PROJECT_ID}" >/dev/null

# 1. Topics Pub/Sub
create_topic_if_missing "${TOPIC_DLQ}"
create_topic_if_missing "${TOPIC_PAYMENTS}"
create_topic_if_missing "${TOPIC_IBAN}"

# 2. Dataset BigQuery RAW
if ! bq --project_id="${PROJECT_ID}" show --dataset "${PROJECT_ID}:${BQ_DATASET_RAW}" >/dev/null 2>&1; then
  echo "[bigquery] Création du dataset ${PROJECT_ID}:${BQ_DATASET_RAW} (${REGION})..."
  bq --location="${REGION}" mk --dataset \
    --label datacloud:antigravity \
    --description="Couche RAW Banque Hexagone (Iceberg, Omni, Object Tables & Pub/Sub Nested Stream)" \
    "${PROJECT_ID}:${BQ_DATASET_RAW}"
fi

# Auto-détection d'une éventuelle table absente ou en ancien schéma legacy `data JSON`
NEEDS_DDL=false
if [[ "${RECREATE_SCHEMA}" == "true" ]]; then
  NEEDS_DDL=true
elif ! bq --project_id="${PROJECT_ID}" show "${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM}" >/dev/null 2>&1; then
  NEEDS_DDL=true
elif ! bq --project_id="${PROJECT_ID}" show "${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM}" >/dev/null 2>&1; then
  NEEDS_DDL=true
elif bq --project_id="${PROJECT_ID}" show --schema --format=json "${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM}" | grep -q '"name":"data"'; then
  echo "[bigquery] Ancien schéma enveloppe 'data JSON' détecté -> migration vers 100 % Nested STRUCT..."
  NEEDS_DDL=true
fi

if [[ "${NEEDS_DDL}" == "true" ]]; then
  # Détacher d'abord les BigQuery Subscriptions existantes avant de remplacer les tables
  for bq_sub in "${SUB_BQ_HIST_PAYMENTS}" "${SUB_BQ_HIST_IBAN}"; do
    if run_gcloud pubsub subscriptions describe "${bq_sub}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
      echo "[pubsub] Suppression temporaire de ${bq_sub} avant recréation du schéma Nested STRUCT..."
      run_gcloud pubsub subscriptions delete "${bq_sub}" --project="${PROJECT_ID}"
    fi
  done

  echo "[bigquery] Création & documentation des 2 tables 100 % Nested STRUCT (${DDL_TEMPLATE})..."
  sed \
    -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
    -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
    "${DDL_TEMPLATE}" | bq --location="${REGION}" query \
    --project_id="${PROJECT_ID}" \
    --use_legacy_sql=false \
    --label datacloud:antigravity
else
  echo "[bigquery] Tables Nested STRUCT déjà en place (${BQ_TABLE_PAYMENTS_STREAM}, ${BQ_TABLE_IBAN_STREAM})."
fi

# 3. Droits IAM obligatoires pour le Service Agent Pub/Sub vers BigQuery + DLQ
PROJECT_NUMBER="$(run_gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

echo "[iam] Attribution des rôles BigQuery (metadataViewer + dataEditor) au Service Agent Pub/Sub..."
run_gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/bigquery.metadataViewer" \
  --condition=None >/dev/null

run_gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/bigquery.dataEditor" \
  --condition=None >/dev/null

# 4. Subscriptions Pull & Opérationnelles
create_sub_if_missing "${SUB_DLQ}" "${TOPIC_DLQ}" \
  --message-retention-duration=7d \
  --expiration-period=never

create_sub_if_missing "${SUB_BQ_RAW}" "${TOPIC_PAYMENTS}" \
  --ack-deadline=60 \
  --message-retention-duration=7d \
  --expiration-period=never \
  --dead-letter-topic="${TOPIC_DLQ}" \
  --max-delivery-attempts=5

create_sub_if_missing "${SUB_ALLOYDB_OPS}" "${TOPIC_PAYMENTS}" \
  --ack-deadline=30 \
  --message-retention-duration=24h \
  --expiration-period=never

create_sub_if_missing "${SUB_DEMO_TAP}" "${TOPIC_PAYMENTS}" \
  --ack-deadline=60 \
  --message-retention-duration=24h \
  --retain-acked-messages \
  --expiration-period=never

create_sub_if_missing "${SUB_IBAN_RAW}" "${TOPIC_IBAN}" \
  --ack-deadline=60 \
  --message-retention-duration=7d \
  --expiration-period=never

# 5. Souscriptions BigQuery natives (--use-table-schema + --drop-unknown-fields + --write-metadata)
create_sub_if_missing "${SUB_BQ_HIST_PAYMENTS}" "${TOPIC_PAYMENTS}" \
  --bigquery-table="${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM}" \
  --use-table-schema \
  --drop-unknown-fields \
  --write-metadata \
  --dead-letter-topic="${TOPIC_DLQ}" \
  --max-delivery-attempts=5 \
  --expiration-period=never

create_sub_if_missing "${SUB_BQ_HIST_IBAN}" "${TOPIC_IBAN}" \
  --bigquery-table="${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM}" \
  --use-table-schema \
  --drop-unknown-fields \
  --write-metadata \
  --dead-letter-topic="${TOPIC_DLQ}" \
  --max-delivery-attempts=5 \
  --expiration-period=never

# Autoriser le service account Pub/Sub sur la DLQ et les souscriptions avec DLQ
run_gcloud pubsub topics add-iam-policy-binding "${TOPIC_DLQ}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher" >/dev/null

for dlq_sub in "${SUB_BQ_RAW}" "${SUB_BQ_HIST_PAYMENTS}" "${SUB_BQ_HIST_IBAN}"; do
  run_gcloud pubsub subscriptions add-iam-policy-binding "${dlq_sub}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${PUBSUB_SA}" \
    --role="roles/pubsub.subscriber" >/dev/null
done

# Purger les anciens messages plats éventuellement en attente sur les souscriptions Pull annexes
if [[ "${NEEDS_DDL}" == "true" ]]; then
  NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  for pull_sub in "${SUB_BQ_RAW}" "${SUB_ALLOYDB_OPS}" "${SUB_DEMO_TAP}" "${SUB_IBAN_RAW}"; do
    run_gcloud pubsub subscriptions seek "${pull_sub}" --time="${NOW_UTC}" --project="${PROJECT_ID}" >/dev/null 2>&1 || true
  done
fi

echo "======================================================================"
echo "[setup_pubsub_queues] Files Pub/Sub & Souscriptions BigQuery Nested STRUCT opérationnelles !"
echo "  - Topic paiements : projects/${PROJECT_ID}/topics/${TOPIC_PAYMENTS}"
echo "      ├── ${SUB_BQ_HIST_PAYMENTS}  --> BigQuery ${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM} (--use-table-schema STRUCT)"
echo "      ├── ${SUB_ALLOYDB_OPS}       --> Temps réel <15ms vers AlloyDB (Démo #4)"
echo "      ├── ${SUB_DEMO_TAP}          --> Miroir d'inspection live"
echo "      └── ${SUB_BQ_RAW}            --> Pull backup / Spark Streaming"
echo "  - Topic IBAN      : projects/${PROJECT_ID}/topics/${TOPIC_IBAN}"
echo "      └── ${SUB_BQ_HIST_IBAN}      --> BigQuery ${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM} (--use-table-schema STRUCT)"
echo "======================================================================"
