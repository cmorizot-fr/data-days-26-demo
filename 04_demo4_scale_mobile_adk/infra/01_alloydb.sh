#!/usr/bin/env bash
# Démo #4 · réseau + cluster AlloyDB PostgreSQL 18 + primaire (idempotent).
# gcloud est utilisé ici car l'outil MCP create_cluster ne permet pas de choisir la
# version PostgreSQL (alloydb_sync exige PG18) ni les flags de l'instance.
set -euo pipefail
source "$(dirname "$0")/config.sh"

exists() { "$@" >/dev/null 2>&1; }

exists gcloud compute networks describe "$VPC" --project "$PROJECT_ID" ||
  gcloud compute networks create "$VPC" --project "$PROJECT_ID" --subnet-mode=custom --quiet

exists gcloud compute addresses describe "$PSA_RANGE" --global --project "$PROJECT_ID" ||
  gcloud compute addresses create "$PSA_RANGE" --project "$PROJECT_ID" --global \
    --purpose=VPC_PEERING --prefix-length=20 --network="$VPC" --quiet

gcloud services vpc-peerings connect --project "$PROJECT_ID" --service=servicenetworking.googleapis.com \
  --ranges="$PSA_RANGE" --network="$VPC" --quiet 2>/dev/null || true

if ! exists gcloud secrets describe "$ALLOYDB_ADMIN_SECRET" --project "$PROJECT_ID"; then
  openssl rand -base64 30 | tr -d '/+=\n' | gcloud secrets create "$ALLOYDB_ADMIN_SECRET" \
    --project "$PROJECT_ID" --replication-policy=user-managed --locations="$REGION" \
    --labels=env=demo2026,demo=d4 --data-file=- --quiet
fi

exists gcloud alloydb clusters describe "$ALLOYDB_CLUSTER" --region "$REGION" --project "$PROJECT_ID" ||
  gcloud alloydb clusters create "$ALLOYDB_CLUSTER" --project "$PROJECT_ID" --region "$REGION" \
    --database-version=POSTGRES_18 --network="$VPC" --allocated-ip-range-name="$PSA_RANGE" \
    --password="$(gcloud secrets versions access latest --secret="$ALLOYDB_ADMIN_SECRET" --project "$PROJECT_ID")" \
    --quiet

# IP publique sans réseau autorisé : seul le connecteur AlloyDB (mTLS + IAM) peut entrer.
exists gcloud alloydb instances describe "$ALLOYDB_PRIMARY" --cluster "$ALLOYDB_CLUSTER" --region "$REGION" --project "$PROJECT_ID" ||
  gcloud alloydb instances create "$ALLOYDB_PRIMARY" --project "$PROJECT_ID" --region "$REGION" \
    --cluster="$ALLOYDB_CLUSTER" --instance-type=PRIMARY --cpu-count=2 --availability-type=ZONAL \
    --database-flags="alloydb.iam_authentication=on,alloydb_sync.enabled=on,bigquery_fdw.enabled=on,google_ml_integration.enable_model_support=on,password.enforce_complexity=on" \
    --assign-inbound-public-ip=ASSIGN_IPV4 --quiet

ALLOYDB_READ_POOL="${ALLOYDB_READ_POOL:-hexagone-d4-read-pool}"
exists gcloud alloydb instances describe "$ALLOYDB_READ_POOL" --cluster "$ALLOYDB_CLUSTER" --region "$REGION" --project "$PROJECT_ID" ||
  gcloud alloydb instances create "$ALLOYDB_READ_POOL" --project "$PROJECT_ID" --region "$REGION" \
    --cluster="$ALLOYDB_CLUSTER" --instance-type=READ_POOL --cpu-count=2 --read-pool-node-count=1 \
    --database-flags="alloydb.iam_authentication=on,password.enforce_complexity=on" \
    --assign-inbound-public-ip=ASSIGN_IPV4 --quiet

# Rôles BigQuery pour le compte de service du cluster AlloyDB (bigquery_fdw + alloydb_sync)
ALLOYDB_SA="$(gcloud alloydb clusters describe "$ALLOYDB_CLUSTER" --region "$REGION" --project "$PROJECT_ID" --format='value(serviceAccountEmail)')"
for role in roles/bigquery.dataViewer roles/bigquery.jobUser roles/bigquery.readSessionUser; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${ALLOYDB_SA}" \
    --role="$role" --condition=None --quiet >/dev/null
done

echo "AlloyDB prêt : ${ALLOYDB_INSTANCE_URI} (+ read pool ${ALLOYDB_READ_POOL})"
# Étapes suivantes via MCP AlloyDB : create_user (IAM) puis execute_sql
#   CREATE DATABASE hexagone;  puis sql/alloydb/00_base.sql, 01_federation_and_sync.sql, 02_action_schema.sql.
