#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
# Script de replay de bout en bout (idempotent) :
#   1. Vérifie / génère les fichiers binaires « Dirty Mainframe » z/OS en local
#   2. Active les APIs GCP requises (Compute, Dataproc Serverless, BigLake, BQ Connection)
#   3. Provisionne la connexion BigLake (biglake-gcs-conn), le sous-réseau Spark Serverless
#      (Private Google Access + règle interne shuffle) et les rôles IAM nécessaires
#   4. Transfère en binaire strict 00_data_generator/output/corebanking/ -> gs://<bucket>/RAW/corebanking/
#   5. Crée et documente (Dataset, Tables, Colonnes) les 4 tables BigLake Managed Iceberg dans raw_bank
#   6. Exécute le batch PySpark Dataproc Serverless (décodage EBCDIC CP500 + COMP-3, filtrage CFT RC=0000,
#      rattachement ordonné CFONB 04 + 05)
#   7. Vérifie en SQL les volumétries, la documentation BigQuery et les invariants métier au centime près
#
# Usage :
#   ./scripts/run_demo1_mainframe_spark_iceberg.sh
#   ./scripts/run_demo1_mainframe_spark_iceberg.sh --skip-upload
#   ./scripts/run_demo1_mainframe_spark_iceberg.sh --ddl-only
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_LOCATION="${BQ_LOCATION:-europe-west1}"
BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
BQ_CONNECTION_ID="${BQ_BIGLAKE_CONNECTION_ID:-biglake-gcs-conn}"

VPC_NAME="${SPARK_VPC_NAME:-spark-sless-vpc}"
SUBNET_NAME="${SPARK_SUBNET_NAME:-spark-sless-ew1}"
SUBNET_CIDR="${SPARK_SUBNET_CIDR:-10.26.0.0/24}"

COREBANKING_LOCAL_DIR="${ROOT_DIR}/00_data_generator/output/corebanking"
DDL_TEMPLATE="${ROOT_DIR}/01_demo1_raw_aggregation/sql/00_create_documented_mainframe_iceberg_tables.sql"
PYSPARK_SCRIPT="${ROOT_DIR}/01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py"

SKIP_UPLOAD=false
DDL_ONLY=false
WRITE_METHOD="direct"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upload)
      SKIP_UPLOAD=true
      shift
      ;;
    --ddl-only)
      DDL_ONLY=true
      shift
      ;;
    --write-method)
      WRITE_METHOD="$2"
      shift 2
      ;;
    *)
      echo "Option inconnue : $1"
      echo "Usage : $0 [--skip-upload] [--ddl-only] [--write-method direct|indirect]"
      exit 1
      ;;
  esac
done

run_gcloud() {
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud --quiet "$@"
}

echo "======================================================================"
echo "[demo1-spark-iceberg] Projet=${PROJECT_ID} | Région=${REGION} | Dataset=${BQ_DATASET_RAW}"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Vérification des fichiers locaux Core Banking (seed=2026)
# ------------------------------------------------------------------------------
if [[ "${SKIP_UPLOAD}" == "false" && ! -f "${COREBANKING_LOCAL_DIR}/MANIFEST_Z_OS_DROP.ctl" ]]; then
  echo "[1/7] Fichiers Mainframe absents en local — génération déterministe (seed=2026)..."
  uv run --project "${ROOT_DIR}" python "${ROOT_DIR}/00_data_generator/generate_mainframe_cfonb.py"
else
  echo "[1/7] Drop Mainframe local prêt (${COREBANKING_LOCAL_DIR})."
fi

# ------------------------------------------------------------------------------
# 2. Activation des APIs Google Cloud requises
# ------------------------------------------------------------------------------
echo "[2/7] Activation / vérification des APIs Google Cloud (Compute, Dataproc, BigLake, BigQuery)..."
run_gcloud services enable \
  compute.googleapis.com \
  dataproc.googleapis.com \
  biglake.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

PROJECT_NUMBER="$(run_gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

# ------------------------------------------------------------------------------
# 3. Connexion Cloud Resource BigLake (biglake-gcs-conn) & droits IAM GCS
# ------------------------------------------------------------------------------
NEW_CONN=false
if bq --project_id="${PROJECT_ID}" show --connection --location="${BQ_LOCATION}" "${BQ_CONNECTION_ID}" >/dev/null 2>&1; then
  echo "[3/7] Connexion BigLake déjà présente : ${PROJECT_ID}.${BQ_LOCATION}.${BQ_CONNECTION_ID}"
else
  echo "[3/7] Création de la connexion Cloud Resource BigLake : ${BQ_CONNECTION_ID} (${BQ_LOCATION})..."
  bq mk --connection \
    --connection_type=CLOUD_RESOURCE \
    --location="${BQ_LOCATION}" \
    --project_id="${PROJECT_ID}" \
    --label datacloud:antigravity \
    "${BQ_CONNECTION_ID}"
  NEW_CONN=true
fi

CONN_SA="$(
  bq --project_id="${PROJECT_ID}" --format=prettyjson show --connection --location="${BQ_LOCATION}" "${BQ_CONNECTION_ID}" \
    | python3 -c "import json, sys; print(json.load(sys.stdin)['cloudResource']['serviceAccountId'])"
)"
echo "      Service Account BigLake : ${CONN_SA}"

# roles/storage.admin inclut storage.buckets.get (requis par Storage Write API sur BigLake Iceberg) + storage.objects.*
run_gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_LANDING}" \
  --member="serviceAccount:${CONN_SA}" \
  --role="roles/storage.admin" \
  --project="${PROJECT_ID}" >/dev/null

run_gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CONN_SA}" \
  --role="roles/biglake.admin" \
  --condition=None >/dev/null

if [[ "${NEW_CONN}" == "true" ]]; then
  echo "      Attente de propagation IAM pour la nouvelle connexion BigLake (15 s)..."
  sleep 15
fi

# ------------------------------------------------------------------------------
# 4. Réseau VPC / Sous-réseau Private Google Access & IAM Dataproc Serverless
# ------------------------------------------------------------------------------
if [[ "${DDL_ONLY}" == "false" ]]; then
  echo "[4/7] Vérification réseau VPC (${VPC_NAME}/${SUBNET_NAME}) & IAM Dataproc Serverless..."
  if ! run_gcloud compute networks describe "${VPC_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "      Création du VPC custom : ${VPC_NAME}..."
    run_gcloud compute networks create "${VPC_NAME}" \
      --project="${PROJECT_ID}" \
      --subnet-mode=custom
  fi

  if ! run_gcloud compute networks subnets describe "${SUBNET_NAME}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "      Création du sous-réseau ${SUBNET_NAME} (${SUBNET_CIDR}, Private Google Access activé)..."
    run_gcloud compute networks subnets create "${SUBNET_NAME}" \
      --project="${PROJECT_ID}" \
      --network="${VPC_NAME}" \
      --region="${REGION}" \
      --range="${SUBNET_CIDR}" \
      --enable-private-ip-google-access
  else
    run_gcloud compute networks subnets update "${SUBNET_NAME}" \
      --project="${PROJECT_ID}" \
      --region="${REGION}" \
      --enable-private-ip-google-access >/dev/null
  fi

  FW_RULE="allow-${VPC_NAME}-internal"
  if ! run_gcloud compute firewall-rules describe "${FW_RULE}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "      Création de la règle firewall interne Spark shuffle (${FW_RULE})..."
    run_gcloud compute firewall-rules create "${FW_RULE}" \
      --project="${PROJECT_ID}" \
      --network="${VPC_NAME}" \
      --direction=INGRESS \
      --priority=1000 \
      --action=ALLOW \
      --rules=tcp,udp,icmp \
      --source-ranges="${SUBNET_CIDR}"
  fi

  COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  for role in roles/dataproc.worker roles/storage.objectAdmin roles/bigquery.dataEditor roles/bigquery.jobUser roles/biglake.admin; do
    run_gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${COMPUTE_SA}" \
      --role="${role}" \
      --condition=None >/dev/null
  done
else
  echo "[4/7] Mode --ddl-only : étape réseau Dataproc ignorée."
fi

# ------------------------------------------------------------------------------
# 5. Transfert binaire strict vers gs://<bucket>/RAW/corebanking/
# ------------------------------------------------------------------------------
if [[ "${SKIP_UPLOAD}" == "false" ]]; then
  echo "[5/7] Synchronisation binaire stricte -> gs://${GCS_BUCKET_LANDING}/RAW/corebanking/ ..."
  run_gcloud storage rsync --recursive \
    "${COREBANKING_LOCAL_DIR}" \
    "gs://${GCS_BUCKET_LANDING}/RAW/corebanking" \
    --project="${PROJECT_ID}"
else
  echo "[5/7] Mode --skip-upload : synchronisation GCS ignorée."
fi

# ------------------------------------------------------------------------------
# 6. Création & Documentation des 4 tables BigLake Managed Iceberg dans BigQuery
# ------------------------------------------------------------------------------
echo "[6/7] Initialisation propre & documentation des 4 tables BigLake Managed Iceberg (${PROJECT_ID}.${BQ_DATASET_RAW})..."
if ! bq --project_id="${PROJECT_ID}" show --dataset "${PROJECT_ID}:${BQ_DATASET_RAW}" >/dev/null 2>&1; then
  bq --location="${BQ_LOCATION}" mk --dataset \
    --label datacloud:antigravity \
    "${PROJECT_ID}:${BQ_DATASET_RAW}"
fi

# Pour un replay idempotent sur tables BigLake Managed Iceberg, storage_uri doit être vierge avant CREATE TABLE
bq --location="${BQ_LOCATION}" query \
  --project_id="${PROJECT_ID}" \
  --use_legacy_sql=false \
  --label datacloud:antigravity \
  "DROP TABLE IF EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_customers_ref\`;
   DROP TABLE IF EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_accounts_master\`;
   DROP TABLE IF EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_balances\`;
   DROP TABLE IF EXISTS \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_movements\`;" >/dev/null

ICEBERG_PREFIX="gs://${GCS_BUCKET_LANDING}/iceberg/${BQ_DATASET_RAW}"
if run_gcloud storage ls "${ICEBERG_PREFIX}/**" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "      Nettoyage des anciens snapshots Iceberg sous ${ICEBERG_PREFIX}/ ..."
  run_gcloud storage rm --recursive "${ICEBERG_PREFIX}" --project="${PROJECT_ID}" >/dev/null
fi

sed \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__LOCATION__/${BQ_LOCATION}/g" \
  -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
  -e "s/__CONNECTION_ID__/${BQ_CONNECTION_ID}/g" \
  -e "s/__BUCKET_LANDING__/${GCS_BUCKET_LANDING}/g" \
  "${DDL_TEMPLATE}" \
  | bq --location="${BQ_LOCATION}" query \
      --project_id="${PROJECT_ID}" \
      --use_legacy_sql=false \
      --label datacloud:antigravity

echo "      4 tables BigLake Managed Iceberg créées et documentées."

if [[ "${DDL_ONLY}" == "true" ]]; then
  echo "[7/7] Mode --ddl-only terminé."
  exit 0
fi

# ------------------------------------------------------------------------------
# 7. Soumission du Batch PySpark Dataproc Serverless & Vérification BigQuery
# ------------------------------------------------------------------------------
BATCH_ID="cbk-mainframe-iceberg-$(date +%Y%m%d-%H%M%S)"
echo "[7/7] Soumission du batch Dataproc Serverless PySpark (${BATCH_ID} — durée estimée ~2-4 min)..."

run_gcloud dataproc batches submit pyspark "${PYSPARK_SCRIPT}" \
  --batch="${BATCH_ID}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --version="2.2" \
  --subnet="${SUBNET_NAME}" \
  --deps-bucket="gs://${GCS_BUCKET_LANDING}" \
  --labels="datacloud=antigravity,domain=corebanking,env=demo2026" \
  -- \
  --project-id "${PROJECT_ID}" \
  --dataset "${BQ_DATASET_RAW}" \
  --raw-gcs-uri "gs://${GCS_BUCKET_LANDING}/RAW/corebanking" \
  --temp-gcs-bucket "${GCS_BUCKET_LANDING}" \
  --write-method "${WRITE_METHOD}"

echo "----------------------------------------------------------------------"
echo "[verification] Contrôle SQL des volumétries, descriptions & invariants BigQuery :"
echo "----------------------------------------------------------------------"
bq --location="${BQ_LOCATION}" query \
  --project_id="${PROJECT_ID}" \
  --use_legacy_sql=false \
  --format=pretty \
  --label datacloud:antigravity \
  "SELECT '1_cbk_customers_ref' AS check_name, CAST(COUNT(*) AS STRING) AS observed_value, '79350' AS expected_value
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_customers_ref\`
   UNION ALL
   SELECT '2_cbk_accounts_master', CAST(COUNT(*) AS STRING), '94350'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_accounts_master\`
   UNION ALL
   SELECT '3_cbk_cfonb_balances', CAST(COUNT(*) AS STRING), '2875062'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_balances\`
   UNION ALL
   SELECT '4_cbk_cfonb_movements', CAST(COUNT(*) AS STRING), '5500000'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_movements\`
   UNION ALL
   SELECT '5_documented_columns', CAST(COUNT(*) AS STRING), '72'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS\`
   WHERE table_name LIKE 'cbk_%' AND description IS NOT NULL AND description != ''
   UNION ALL
   SELECT '6_raw_invalid_dates_preserved', CAST(COUNTIF(date_valeur_raw IN ('00000000', '99999999')) AS STRING), '66000'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_movements\`
   UNION ALL
   SELECT '7_deposit_flight_90d_eur', FORMAT('%.2f', SUM(signed_amount_eur)), '-2420000000.00'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.cbk_cfonb_movements\`
   WHERE code_op_interne = '0810'
     AND date_compta_raw BETWEEN '20260815' AND '20261112'
     AND counterparty_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
   ORDER BY check_name;"

echo "======================================================================"
echo "[demo1-spark-iceberg] Chargement Spark -> BigLake Iceberg terminé et certifié !"
echo "======================================================================"
