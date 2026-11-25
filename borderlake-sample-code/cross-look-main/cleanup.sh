#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Cleanly removes all AWS and Google Cloud resources provisioned by deploy.sh.
#
# Usage:
#   ./cleanup.sh                   # Interactive confirmation prompt
#   ./cleanup.sh --yes             # Non-interactive teardown
#   ./cleanup.sh --keep-s3-bucket  # Keep the S3 bucket & Iceberg files

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/00_common.sh"

AUTO_APPROVE="false"
KEEP_S3_BUCKET="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      AUTO_APPROVE="true"
      shift
      ;;
    --keep-s3-bucket)
      KEEP_S3_BUCKET="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--yes] [--keep-s3-bucket]"
      exit 0
      ;;
    *)
      log_err "Unknown option: $1"
      exit 1
      ;;
  esac
done

preflight_checks

printf "\n==============================================================================\n"
printf " Cross-Look Teardown Plan\n"
printf "==============================================================================\n"
printf "  [GCP] BigQuery Dataset   : %s:%s\n" "${GCP_PROJECT}" "${BQ_DEMO_DATASET}"
printf "  [GCP] Federated Catalog  : %s.%s\n" "${GCP_PROJECT}" "${FEDERATED_CATALOG}"
printf "  [GCP] GCS Staging Bucket : %s (recursive delete)\n" "${GCS_STAGE_BUCKET}"
printf "  [AWS] Glue Database      : %s (%s)\n" "${GLUE_DB}" "${AWS_REGION}"
printf "  [AWS] IAM Role           : %s\n" "${AWS_ROLE_NAME}"
if [[ "${KEEP_S3_BUCKET}" == "false" ]]; then
  printf "  [AWS] Amazon S3 Bucket   : s3://%s (recursive delete)\n" "${S3_BUCKET}"
else
  printf "  [AWS] Amazon S3 Bucket   : s3://%s (RETAINED via --keep-s3-bucket)\n" "${S3_BUCKET}"
fi
printf "==============================================================================\n"

if [[ "${AUTO_APPROVE}" != "true" ]]; then
  read -r -p "Proceed with deleting these resources? [y/N] " REPLY
  if [[ ! "${REPLY}" =~ ^[Yy]$ ]]; then
    log_info "Teardown cancelled."
    exit 0
  fi
fi

log_step "1. Removing BigQuery dataset '${GCP_PROJECT}:${BQ_DEMO_DATASET}'..."
bq --project_id="${GCP_PROJECT}" rm -r -f -d "${GCP_PROJECT}:${BQ_DEMO_DATASET}" >/dev/null 2>&1 || true

log_step "2. Deleting federated catalog '${FEDERATED_CATALOG}'..."
gcloud_biglake_catalogs delete "${FEDERATED_CATALOG}" \
  --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1 || true

log_step "3. Deleting Cloud Storage staging bucket '${GCS_STAGE_BUCKET}'..."
if [[ -n "${GCS_STAGE_BUCKET:-}" ]] && gcloud storage buckets describe "${GCS_STAGE_BUCKET}" --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1; then
  gcloud storage rm --recursive "${GCS_STAGE_BUCKET}" --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1 || true
fi

log_step "4. Deleting AWS Glue database '${GLUE_DB}' (${AWS_REGION})..."
aws glue delete-database --region "${AWS_REGION}" --name "${GLUE_DB}" >/dev/null 2>&1 || true

log_step "5. Deleting AWS IAM inline policy & role '${AWS_ROLE_NAME}'..."
aws iam delete-role-policy \
  --role-name "${AWS_ROLE_NAME}" \
  --policy-name "thelook_glue_s3_read_policy" >/dev/null 2>&1 || true
aws iam delete-role --role-name "${AWS_ROLE_NAME}" >/dev/null 2>&1 || true

if [[ "${KEEP_S3_BUCKET}" == "false" ]]; then
  log_step "6. Deleting Amazon S3 bucket 's3://${S3_BUCKET}'..."
  aws s3 rb "s3://${S3_BUCKET}" --force --region "${AWS_REGION}" >/dev/null 2>&1 || true
fi

log_ok "Teardown complete."
