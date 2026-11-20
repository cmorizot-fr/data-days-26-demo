#!/usr/bin/env bash
# Démo #4 · branche Pub/Sub sepa-payments-alloydb-ops-sub -> Cloud Run -> AlloyDB (idempotent).
set -euo pipefail
source "$(dirname "$0")/config.sh"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

exists() { "$@" >/dev/null 2>&1; }
sa_email() { echo "$1@${PROJECT_ID}.iam.gserviceaccount.com"; }

# 1. Comptes de service
for sa in "$INGEST_SA" "$PUSH_SA"; do
  exists gcloud iam service-accounts describe "$(sa_email "$sa")" --project "$PROJECT_ID" ||
    gcloud iam service-accounts create "$sa" --project "$PROJECT_ID" --display-name="Démo 4 · $sa" --quiet
done

# 2. Droits du service d'ingestion : se connecter à AlloyDB en IAM, rien d'autre.
for role in roles/alloydb.client roles/alloydb.databaseUser roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(sa_email "$INGEST_SA")" \
    --role="$role" --condition=None --quiet >/dev/null
done

# 3. Image et déploiement Cloud Run (privé)
exists gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" ||
  gcloud artifacts repositories create "$AR_REPO" --project "$PROJECT_ID" --location "$REGION" \
    --repository-format=docker --labels="$LABELS" --quiet

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${INGEST_SERVICE}:latest"
# Compte de build dédié : le compte Compute par défaut n'a pas le droit de pousser dans Artifact Registry,
# et on préfère ne pas élargir un compte partagé avec les démos 1 à 3.
BUILD_SA="hexagone-d4-build"
exists gcloud iam service-accounts describe "$(sa_email "$BUILD_SA")" --project "$PROJECT_ID" ||
  gcloud iam service-accounts create "$BUILD_SA" --project "$PROJECT_ID" --display-name="Démo 4 · build" --quiet
gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:$(sa_email "$BUILD_SA")" --role=roles/artifactregistry.writer --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(sa_email "$BUILD_SA")" \
  --role=roles/logging.logWriter --condition=None --quiet >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}_cloudbuild" \
  --member="serviceAccount:$(sa_email "$BUILD_SA")" --role=roles/storage.objectViewer --quiet >/dev/null
gcloud builds submit "$HERE/services/payments_ingest" --project "$PROJECT_ID" --region "$REGION" \
  --config "$HERE/services/payments_ingest/cloudbuild.yaml" --substitutions="_IMAGE=${IMAGE}" \
  --service-account="projects/${PROJECT_ID}/serviceAccounts/$(sa_email "$BUILD_SA")" \
  --gcs-source-staging-dir="gs://${PROJECT_ID}_cloudbuild/source" --quiet

gcloud run deploy "$INGEST_SERVICE" --project "$PROJECT_ID" --region "$REGION" --image "$IMAGE" \
  --service-account="$(sa_email "$INGEST_SA")" --no-allow-unauthenticated --ingress=all \
  --min-instances=1 --max-instances=3 --cpu=1 --memory=512Mi --concurrency=40 \
  --set-env-vars="ALLOYDB_INSTANCE_URI=${ALLOYDB_INSTANCE_URI},ALLOYDB_DB=${ALLOYDB_DB},ALLOYDB_IAM_USER=${INGEST_SA}@${PROJECT_ID}.iam,ALLOYDB_IP_TYPE=PUBLIC" \
  --labels="$LABELS" --quiet

# 4. Seul le compte de push Pub/Sub peut appeler le service.
gcloud run services add-iam-policy-binding "$INGEST_SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --member="serviceAccount:$(sa_email "$PUSH_SA")" --role=roles/run.invoker --quiet >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$(sa_email "$PUSH_SA")" --project "$PROJECT_ID" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role=roles/iam.serviceAccountTokenCreator --quiet >/dev/null

# 5. La souscription réservée à la démo 4 passe de pull à push (jeton OIDC).
URL="$(gcloud run services describe "$INGEST_SERVICE" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
gcloud pubsub subscriptions modify-push-config "$OPS_SUBSCRIPTION" --project "$PROJECT_ID" \
  --push-endpoint="${URL}/pubsub/push" --push-auth-service-account="$(sa_email "$PUSH_SA")" \
  --push-auth-token-audience="${URL}" --quiet

echo "Branché : ${OPS_SUBSCRIPTION} -> ${URL}/pubsub/push -> AlloyDB ${ALLOYDB_DB}.live_movements"
