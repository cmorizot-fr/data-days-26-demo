#!/usr/bin/env bash
# Démo #4 · configuration partagée par les scripts infra/.
export PROJECT_ID="${PROJECT_ID:-data-days-demo}"
export PROJECT_NUMBER="${PROJECT_NUMBER:-1051798075322}"
export REGION="${REGION:-europe-west1}"

export VPC="hexagone-d4-vpc"
export PSA_RANGE="hexagone-d4-psa-range"
export ALLOYDB_CLUSTER="hexagone-d4-alloydb"
export ALLOYDB_PRIMARY="hexagone-d4-primary"
export ALLOYDB_DB="hexagone"
export ALLOYDB_ADMIN_SECRET="hexagone-d4-alloydb-admin"
export ALLOYDB_INSTANCE_URI="projects/${PROJECT_ID}/locations/${REGION}/clusters/${ALLOYDB_CLUSTER}/instances/${ALLOYDB_PRIMARY}"

export INGEST_SERVICE="hexagone-d4-payments-ingest"
export INGEST_SA="hexagone-d4-ingest"
export PUSH_SA="hexagone-d4-pubsub-push"
export OPS_SUBSCRIPTION="sepa-payments-alloydb-ops-sub"
export AR_REPO="hexagone-d4"

export LABELS="env=demo2026,demo=d4,datacloud=antigravity"
# Attribution DAK (skill enforcing-resource-attribution)
export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"
