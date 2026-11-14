#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
# Découverte automatique sans DDL des PDF sur GCS via Dataplex / Knowledge Catalog
# Cloud Storage Discovery (`hexagone-raw-pdf-discovery`) :
#   1. Vérifie que les 250 PDF agences + 6 PDF réglementaires CFO sont sur GCS
#   2. Provisionne l'identité Service Agent Dataplex et lui accorde les 3 rôles
#      requis (`discoveryServiceAgent`, `discoveryPublishingServiceAgent`,
#      `discoveryBigLakePublishingServiceAgent`) — zéro clic manuel en console
#   3. Crée ou met à jour le DataScan `data-discovery` ciblant uniquement :
#        - RAW/PROMO_CONTRACTS_PDF/** (250 avenants agences -> -14,30 M€)
#        - RAW/REGULATORY_CFO_PDF/**  (6 normes CFO / ACPR / ILAAP / PCEC)
#      en réutilisant la connexion BigLake `biglake-gcs-conn` (`europe-west1`)
#   4. Déclenche un job de scan immédiat, attend sa complétion et vérifie les
#      BigLake Object Tables automatiquement publiées dans BigQuery.
#
# Usage :
#   ./scripts/run_demo1_gcs_pdf_discovery.sh
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
REGION="${GCP_REGION:-europe-west1}"
BQ_LOCATION="${BQ_LOCATION:-europe-west1}"
GCS_BUCKET_LANDING="${GCS_BUCKET_LANDING:-data-days-demo-landing}"
BQ_CONNECTION_ID="${BQ_BIGLAKE_CONNECTION_ID:-biglake-gcs-conn}"
DATASCAN_ID="${DATAPLEX_PDF_SCAN_ID:-hexagone-raw-pdf-discovery}"

run_gcloud() {
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud --quiet "$@"
}

echo "======================================================================"
echo "[demo1-pdf-discovery] Projet=${PROJECT_ID} | Région=${REGION} | Scan=${DATASCAN_ID}"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Activation API Dataplex & vérification des PDF sur GCS
# ------------------------------------------------------------------------------
echo "[1/5] Vérification de l'API Dataplex et des dossiers PDF dans gs://${GCS_BUCKET_LANDING}/RAW/ ..."
run_gcloud services enable dataplex.googleapis.com bigquery.googleapis.com bigqueryconnection.googleapis.com biglake.googleapis.com \
  --project="${PROJECT_ID}"

PROMO_COUNT="$(run_gcloud storage ls "gs://${GCS_BUCKET_LANDING}/RAW/PROMO_CONTRACTS_PDF/*.pdf" --project="${PROJECT_ID}" | wc -l | tr -d ' ')"
REG_COUNT="$(run_gcloud storage ls "gs://${GCS_BUCKET_LANDING}/RAW/REGULATORY_CFO_PDF/*.pdf" --project="${PROJECT_ID}" | wc -l | tr -d ' ')"
echo "      Objets GCS détectés : PROMO_CONTRACTS_PDF=${PROMO_COUNT} PDF | REGULATORY_CFO_PDF=${REG_COUNT} PDF"

if [[ "${PROMO_COUNT}" -ne 250 || "${REG_COUNT}" -ne 6 ]]; then
  echo "ERREUR : attendu 250 et 6 PDF dans GCS (trouvé ${PROMO_COUNT} et ${REG_COUNT})."
  exit 1
fi

# ------------------------------------------------------------------------------
# 2. Connexion BigLake & Rôles IAM du Service Agent Dataplex Discovery
# ------------------------------------------------------------------------------
echo "[2/5] Configuration IAM du Service Agent Dataplex Cloud Storage Discovery..."
PROJECT_NUMBER="$(run_gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

# Génère l'identité managée Dataplex si elle n'existe pas encore
run_gcloud beta services identity create --service=dataplex.googleapis.com --project="${PROJECT_ID}" >/dev/null 2>&1 || true
DATAPLEX_SA="service-${PROJECT_NUMBER}@gcp-sa-dataplex.iam.gserviceaccount.com"
echo "      Service Agent Dataplex : ${DATAPLEX_SA}"

# Droit de lecture/scan sur le bucket GCS source
run_gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_LANDING}" \
  --member="serviceAccount:${DATAPLEX_SA}" \
  --role="roles/dataplex.discoveryServiceAgent" \
  --project="${PROJECT_ID}" >/dev/null

# Droits de publication BigQuery + délégation de la connexion BigLake
for role in roles/dataplex.discoveryPublishingServiceAgent roles/dataplex.discoveryBigLakePublishingServiceAgent; do
  run_gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DATAPLEX_SA}" \
    --role="${role}" \
    --condition=None >/dev/null
done

# ------------------------------------------------------------------------------
# 3. Création ou mise à jour du DataScan Dataplex `data-discovery`
# ------------------------------------------------------------------------------
BUCKET_RESOURCE="//storage.googleapis.com/projects/${PROJECT_ID}/buckets/${GCS_BUCKET_LANDING}"
CONN_RESOURCE="projects/${PROJECT_ID}/locations/${BQ_LOCATION}/connections/${BQ_CONNECTION_ID}"
INCLUDE_PATTERNS="RAW/PROMO_CONTRACTS_PDF/**,RAW/REGULATORY_CFO_PDF/**"

if run_gcloud dataplex datascans describe "${DATASCAN_ID}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "[3/5] DataScan ${DATASCAN_ID} déjà présent — mise à jour de la configuration..."
  run_gcloud dataplex datascans update data-discovery "${DATASCAN_ID}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --display-name="Banque Hexagone — Discovery PDF Agences & Réglementaire CFO" \
    --description="Découverte automatique sans DDL des 250 PDF d'avenants promotionnels agences et des 6 PDF réglementaires CFO vers des BigLake Object Tables." \
    --bigquery-publishing-table-type="BIGLAKE" \
    --bigquery-publishing-connection="${CONN_RESOURCE}" \
    --bigquery-publishing-dataset-project="projects/${PROJECT_ID}" \
    --bigquery-publishing-dataset-location="${BQ_LOCATION}" \
    --storage-include-patterns="${INCLUDE_PATTERNS}" \
    --schedule="CRON_TZ=Europe/Paris 0 6 * * *" \
    --labels="datacloud=antigravity,domain=pdf_discovery,env=demo2026"
else
  echo "[3/5] Création du DataScan Cloud Storage Discovery : ${DATASCAN_ID}..."
  for iam_try in 1 2 3 4; do
    if run_gcloud dataplex datascans create data-discovery "${DATASCAN_ID}" \
      --location="${REGION}" \
      --project="${PROJECT_ID}" \
      --display-name="Banque Hexagone — Discovery PDF Agences & Réglementaire CFO" \
      --description="Découverte automatique sans DDL des 250 PDF d'avenants promotionnels agences et des 6 PDF réglementaires CFO vers des BigLake Object Tables." \
      --data-source-resource="${BUCKET_RESOURCE}" \
      --bigquery-publishing-table-type="BIGLAKE" \
      --bigquery-publishing-connection="${CONN_RESOURCE}" \
      --bigquery-publishing-dataset-project="projects/${PROJECT_ID}" \
      --bigquery-publishing-dataset-location="${BQ_LOCATION}" \
      --storage-include-patterns="${INCLUDE_PATTERNS}" \
      --schedule="CRON_TZ=Europe/Paris 0 6 * * *" \
      --labels="datacloud=antigravity,domain=pdf_discovery,env=demo2026"; then
      break
    fi
    if [[ "${iam_try}" -eq 4 ]]; then
      echo "ERREUR : impossible de créer le DataScan après propagation IAM."
      exit 1
    fi
    echo "      Attente de propagation IAM du Service Agent Dataplex (10 s, essai ${iam_try}/4)..."
    sleep 10
  done
fi

# ------------------------------------------------------------------------------
# 4. Exécution immédiate du job de scan & suivi jusqu'à SUCCEEDED
# ------------------------------------------------------------------------------
echo "[4/5] Déclenchement immédiat du scan Discovery (${DATASCAN_ID})..."
JOB_NAME="$(
  run_gcloud dataplex datascans run "${DATASCAN_ID}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(job.name)"
)"
JOB_ID="${JOB_NAME##*/}"
echo "      Job Discovery lancé : ${JOB_ID}"

STATE="RUNNING"
for attempt in {1..90}; do
  STATE="$(
    run_gcloud dataplex datascans jobs describe "${JOB_ID}" \
      --datascan="${DATASCAN_ID}" \
      --location="${REGION}" \
      --project="${PROJECT_ID}" \
      --format="value(state)"
  )"
  echo "      [${attempt}/90] État du job Discovery : ${STATE}"
  if [[ "${STATE}" == "SUCCEEDED" ]]; then
    break
  elif [[ "${STATE}" == "FAILED" || "${STATE}" == "CANCELLED" ]]; then
    echo "ERREUR : le job Discovery s'est terminé à l'état ${STATE}."
    run_gcloud dataplex datascans jobs describe "${JOB_ID}" \
      --datascan="${DATASCAN_ID}" \
      --location="${REGION}" \
      --project="${PROJECT_ID}" \
      --format="yaml"
    exit 1
  fi
  sleep 5
done

if [[ "${STATE}" != "SUCCEEDED" ]]; then
  echo "ERREUR : timeout en attendant la fin du job Discovery (${STATE})."
  exit 1
fi

echo "----------------------------------------------------------------------"
echo "[5/5] Résultat détaillé du job Discovery & Object Tables publiées :"
echo "----------------------------------------------------------------------"
run_gcloud dataplex datascans jobs describe "${JOB_ID}" \
  --datascan="${DATASCAN_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="yaml(state,startTime,endTime,dataDiscoveryResult)"

BQ_DATASET_RAW="${BQ_DATASET_RAW:-raw_bank}"
VIEWS_DDL="${ROOT_DIR}/01_demo1_raw_aggregation/sql/01_expose_discovered_pdf_views.sql"
DISCOVERED_DATASET="$(echo "${GCS_BUCKET_LANDING}" | tr '-' '_')"

echo ""
echo "Publication des 2 vues gouvernées dans ${PROJECT_ID}.${BQ_DATASET_RAW} (au-dessus de ${DISCOVERED_DATASET}.raw) :"
sed \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__DATASET_RAW__/${BQ_DATASET_RAW}/g" \
  -e "s/__DISCOVERED_DATASET__/${DISCOVERED_DATASET}/g" \
  -e "s/__BUCKET_LANDING__/${GCS_BUCKET_LANDING}/g" \
  "${VIEWS_DDL}" \
  | bq --location="${BQ_LOCATION}" query \
      --project_id="${PROJECT_ID}" \
      --use_legacy_sql=false \
      --label datacloud:antigravity

bq --location="${BQ_LOCATION}" query \
  --project_id="${PROJECT_ID}" \
  --use_legacy_sql=false \
  --format=pretty \
  --label datacloud:antigravity \
  "SELECT '1_object_table_discovered' AS check_name, table_name AS target, CAST(COUNT(*) AS STRING) AS observed_rows, '287' AS note
   FROM \`${PROJECT_ID}.${DISCOVERED_DATASET}.INFORMATION_SCHEMA.TABLES\`
   CROSS JOIN \`${PROJECT_ID}.${DISCOVERED_DATASET}.raw\`
   WHERE table_name = 'raw'
   GROUP BY table_name
   UNION ALL
   SELECT '2_promo_contracts_view', 'raw_bank.raw_promo_contracts_pdf', CAST(COUNT(*) AS STRING), '250 PDF (-14.30 M EUR)'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.raw_promo_contracts_pdf\`
   UNION ALL
   SELECT '3_cfo_regulatory_view', 'raw_bank.raw_cfo_regulatory_pdf', CAST(COUNT(*) AS STRING), '6 PDF (ANC/ALM/ACPR)'
   FROM \`${PROJECT_ID}.${BQ_DATASET_RAW}.raw_cfo_regulatory_pdf\`
   ORDER BY check_name;"

echo "======================================================================"
echo "[demo1-pdf-discovery] Découverte automatique GCS -> BigLake Object Tables terminée !"
echo "======================================================================"
