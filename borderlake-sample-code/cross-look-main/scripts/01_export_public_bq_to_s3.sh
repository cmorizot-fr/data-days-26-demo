#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Step 1: Export all 7 tables from bigquery-public-data.thelook_ecommerce (US)
#         to Snappy Parquet in Cloud Storage staging and upload to Amazon S3
#         (GCS staging bucket is cleaned up by ./cleanup.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_common.sh"

preflight_checks
enable_required_gcp_apis

GCS_STAGE_BUCKET="${GCS_STAGE_BUCKET:-gs://${GCP_PROJECT}-crosslook-stage-${AWS_ACCOUNT_ID}}"
_TMP_ROOT="${TMPDIR:-/tmp}"
LOCAL_STAGE_DIR="$(mktemp -d "${_TMP_ROOT%/}/crosslook-parquet.XXXXXX")"

cleanup_local_staging() {
  if [[ -d "${LOCAL_STAGE_DIR}" ]]; then
    rm -rf "${LOCAL_STAGE_DIR}" || true
  fi
}
trap cleanup_local_staging EXIT

log_step "1.1 Ensuring US Cloud Storage staging bucket (${GCS_STAGE_BUCKET}) exists..."
gcloud storage buckets describe "${GCS_STAGE_BUCKET}" --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1 || \
  gcloud storage buckets create "${GCS_STAGE_BUCKET}" \
    --project="${GCP_PROJECT}" \
    --location="US" \
    --uniform-bucket-level-access \
    --quiet

SRC="${SOURCE_BQ_PROJECT}.${SOURCE_BQ_DATASET}"
log_step "1.2 Exporting all 7 public tables from '${SRC}' to Snappy Parquet..."
log_info "Formatting TIMESTAMP -> UTC ISO microsecond string and GEOGRAPHY -> WKT string for clean Athena -> Apache Iceberg TIMESTAMP(6) serialization."

export_table() {
  local tbl="$1"
  local select_sql="$2"
  log_info "Exporting ${tbl}..."
  bq query --project_id="${GCP_PROJECT}" --location="US" --use_legacy_sql=false --quiet \
    "EXPORT DATA OPTIONS (
       uri = '${GCS_STAGE_BUCKET}/${tbl}/*.parquet',
       format = 'PARQUET',
       compression = 'SNAPPY',
       overwrite = true
     ) AS ${select_sql};"
}

export_table "products" \
  "SELECT * FROM \`${SRC}.products\`"

export_table "distribution_centers" \
  "SELECT * REPLACE (
     ST_ASTEXT(distribution_center_geom) AS distribution_center_geom
   ) FROM \`${SRC}.distribution_centers\`"

export_table "users" \
  "SELECT * REPLACE (
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', created_at, 'UTC') AS created_at,
     ST_ASTEXT(user_geom) AS user_geom
   ) FROM \`${SRC}.users\`"

export_table "events" \
  "SELECT * REPLACE (
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', created_at, 'UTC') AS created_at
   ) FROM \`${SRC}.events\`"

export_table "inventory_items" \
  "SELECT * REPLACE (
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', created_at, 'UTC') AS created_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', sold_at, 'UTC') AS sold_at
   ) FROM \`${SRC}.inventory_items\`"

export_table "orders" \
  "SELECT * REPLACE (
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', created_at, 'UTC') AS created_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', returned_at, 'UTC') AS returned_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', shipped_at, 'UTC') AS shipped_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', delivered_at, 'UTC') AS delivered_at
   ) FROM \`${SRC}.orders\`"

export_table "order_items" \
  "SELECT * REPLACE (
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', created_at, 'UTC') AS created_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', shipped_at, 'UTC') AS shipped_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', delivered_at, 'UTC') AS delivered_at,
     FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', returned_at, 'UTC') AS returned_at
   ) FROM \`${SRC}.order_items\`"

log_step "1.3 Downloading staged Parquet files (~115 MB) to temporary local folder..."
gcloud storage cp -r "${GCS_STAGE_BUCKET}/*" "${LOCAL_STAGE_DIR}/" --project="${GCP_PROJECT}" --quiet

for tbl in distribution_centers products users events inventory_items orders order_items; do
  if [[ -z "$(find "${LOCAL_STAGE_DIR}/${tbl}" -name '*.parquet' -print -quit 2>/dev/null)" ]]; then
    log_err "No .parquet files downloaded for table '${tbl}'."
    exit 1
  fi
done

log_step "1.4 Ensuring Amazon S3 bucket 's3://${S3_BUCKET}' (${AWS_REGION}) exists and syncing raw Parquet..."
if ! aws s3api head-bucket --bucket "${S3_BUCKET}" --region "${AWS_REGION}" >/dev/null 2>&1; then
  aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"
fi

# Block public access on the S3 bucket as a security best practice
aws s3api put-public-access-block \
  --bucket "${S3_BUCKET}" \
  --region "${AWS_REGION}" \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" >/dev/null 2>&1 || true

aws s3 sync "${LOCAL_STAGE_DIR}/" "s3://${S3_BUCKET}/raw/" --delete --region "${AWS_REGION}"

log_step "1.5 Verifying uploaded S3 Parquet objects under s3://${S3_BUCKET}/raw/..."
aws s3 ls "s3://${S3_BUCKET}/raw/" --recursive --human-readable --summarize --region "${AWS_REGION}" | tail -n 5

log_ok "Step 1 complete — all 7 tables staged in s3://${S3_BUCKET}/raw/."
