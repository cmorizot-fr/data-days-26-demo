#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Prépare les Topics, Subscriptions Pull et Subscriptions BigQuery natives
# (historisation temps réel sans serveur) sur data-days-demo (europe-west1).
#
# Usage :
#   ./scripts/setup_pubsub_queues.sh
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"

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
echo "[setup_pubsub_queues] Provisionnement Pub/Sub & BigQuery Sub (${PROJECT_ID} · ${REGION})"
echo "======================================================================"

run_gcloud services enable pubsub.googleapis.com bigquery.googleapis.com cloudresourcemanager.googleapis.com \
  --project="${PROJECT_ID}" >/dev/null

# 1. Topics Pub/Sub
create_topic_if_missing "${TOPIC_DLQ}"
create_topic_if_missing "${TOPIC_PAYMENTS}"
create_topic_if_missing "${TOPIC_IBAN}"

# 2. Dataset & Tables BigQuery d'historisation temps réel (enveloppe JSON + métadonnées Pub/Sub)
if ! bq --project_id="${PROJECT_ID}" show --dataset "${PROJECT_ID}:${BQ_DATASET_RAW}" >/dev/null 2>&1; then
  echo "[bigquery] Création du dataset ${PROJECT_ID}:${BQ_DATASET_RAW} (${REGION})..."
  bq --location="${REGION}" mk --dataset \
    --label datacloud:antigravity \
    --description="Couche RAW Banque Hexagone (Iceberg, Omni, Object Tables & Pub/Sub Stream)" \
    "${PROJECT_ID}:${BQ_DATASET_RAW}"
fi

echo "[bigquery] Vérification / création des tables d'historisation Pub/Sub..."
bq --location="${REGION}" query --project_id="${PROJECT_ID}" --use_legacy_sql=false --label datacloud:antigravity "
CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM}\` (
  subscription_name STRING,
  message_id STRING,
  publish_time TIMESTAMP,
  data JSON,
  attributes JSON
)
PARTITION BY DATE(publish_time)
OPTIONS (
  description = 'Historisation temps réel native via BigQuery Subscription du topic ${TOPIC_PAYMENTS} (ISO 20022 pacs.008)'
);

CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM}\` (
  subscription_name STRING,
  message_id STRING,
  publish_time TIMESTAMP,
  data JSON,
  attributes JSON
)
PARTITION BY DATE(publish_time)
OPTIONS (
  description = 'Historisation temps réel native via BigQuery Subscription du topic ${TOPIC_IBAN}'
);
" >/dev/null

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

# 5. Souscriptions BigQuery natives (écriture directe temps réel vers BigQuery !)
create_sub_if_missing "${SUB_BQ_HIST_PAYMENTS}" "${TOPIC_PAYMENTS}" \
  --bigquery-table="${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM}" \
  --write-metadata \
  --dead-letter-topic="${TOPIC_DLQ}" \
  --max-delivery-attempts=5 \
  --expiration-period=never

create_sub_if_missing "${SUB_BQ_HIST_IBAN}" "${TOPIC_IBAN}" \
  --bigquery-table="${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM}" \
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

echo "======================================================================"
echo "[setup_pubsub_queues] Files Pub/Sub & Souscriptions BigQuery opérationnelles !"
echo "  - Topic paiements : projects/${PROJECT_ID}/topics/${TOPIC_PAYMENTS}"
echo "      ├── ${SUB_BQ_HIST_PAYMENTS}  --> BigQuery ${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_PAYMENTS_STREAM} (auto-historisation)"
echo "      ├── ${SUB_ALLOYDB_OPS}       --> Temps réel <15ms vers AlloyDB (Démo #4)"
echo "      ├── ${SUB_DEMO_TAP}          --> Miroir d'inspection live"
echo "      └── ${SUB_BQ_RAW}            --> Pull backup / Spark Streaming"
echo "  - Topic IBAN      : projects/${PROJECT_ID}/topics/${TOPIC_IBAN}"
echo "      └── ${SUB_BQ_HIST_IBAN}      --> BigQuery ${PROJECT_ID}:${BQ_DATASET_RAW}.${BQ_TABLE_IBAN_STREAM} (auto-historisation)"
echo "======================================================================"
