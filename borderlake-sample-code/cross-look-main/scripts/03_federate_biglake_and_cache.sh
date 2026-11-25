#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Step 3: Configure keyless OIDC Web Identity federation between AWS IAM and the
#         Lakehouse runtime catalog, enable background metadata refresh (300s),
#         enable Cross-Cloud Caching (Intelligent Caching), and wait for sync.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_common.sh"

preflight_checks
enable_required_gcp_apis

_TMP_ROOT="${TMPDIR:-/tmp}"
TMP_POLICY_DIR="$(mktemp -d "${_TMP_ROOT%/}/crosslook-iam.XXXXXX")"
trap 'rm -rf "${TMP_POLICY_DIR}" || true' EXIT

log_step "3.1 Creating/updating least-privilege AWS IAM role '${AWS_ROLE_NAME}'..."
cat > "${TMP_POLICY_DIR}/trust_placeholder.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "accounts.google.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "accounts.google.com:aud": ["PLACEHOLDER_VALUE"],
          "accounts.google.com:sub": ["PLACEHOLDER_VALUE"]
        }
      }
    }
  ]
}
EOF

aws iam get-role --role-name "${AWS_ROLE_NAME}" >/dev/null 2>&1 || \
  aws iam create-role \
    --role-name "${AWS_ROLE_NAME}" \
    --assume-role-policy-document "file://${TMP_POLICY_DIR}/trust_placeholder.json" \
    --max-session-duration 43200 >/dev/null

cat > "${TMP_POLICY_DIR}/permissions.json" << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlueCatalogReadOnly",
      "Effect": "Allow",
      "Action": [
        "glue:GetCatalog",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables"
      ],
      "Resource": [
        "arn:aws:glue:${AWS_REGION}:${AWS_ACCOUNT_ID}:catalog",
        "arn:aws:glue:${AWS_REGION}:${AWS_ACCOUNT_ID}:database/${GLUE_DB}",
        "arn:aws:glue:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${GLUE_DB}/*"
      ]
    },
    {
      "Sid": "S3IcebergBucketReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET}",
        "arn:aws:s3:::${S3_BUCKET}/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name "${AWS_ROLE_NAME}" \
  --policy-name "thelook_glue_s3_read_policy" \
  --policy-document "file://${TMP_POLICY_DIR}/permissions.json"

log_step "3.2 Creating/verifying federated catalog '${FEDERATED_CATALOG}' in ${GCP_PROJECT} (${GCP_REGION}) with Cross-Cloud Cache enabled..."
CREATE_HELP="$(gcloud_biglake_catalogs create --help 2>&1 || true)"

if ! gcloud_biglake_catalogs describe "${FEDERATED_CATALOG}" --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1; then
  if grep -q -- '--cross-cloud-cache' <<< "${CREATE_HELP}"; then
    gcloud_biglake_catalogs create "${FEDERATED_CATALOG}" \
      --project="${GCP_PROJECT}" \
      --primary-location="${GCP_REGION}" \
      --catalog-type="federated" \
      --federated-catalog-type="glue" \
      --glue-warehouse="${AWS_ACCOUNT_ID}" \
      --glue-aws-region="${AWS_REGION}" \
      --glue-aws-role-arn="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${AWS_ROLE_NAME}" \
      --namespace-filters="${GLUE_DB}" \
      --cross-cloud-cache="enabled" \
      --quiet
  else
    gcloud_biglake_catalogs create "${FEDERATED_CATALOG}" \
      --project="${GCP_PROJECT}" \
      --primary-location="${GCP_REGION}" \
      --catalog-type="federated" \
      --federated-catalog-type="glue" \
      --glue-warehouse="${AWS_ACCOUNT_ID}" \
      --glue-aws-region="${AWS_REGION}" \
      --glue-aws-role-arn="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${AWS_ROLE_NAME}" \
      --namespace-filters="${GLUE_DB}" \
      --quiet
  fi
fi

# Extract BigLake service agent subject ID (supports both gcloud CLI format variants + REST fallback)
LAKEHOUSE_SA_ID="$(gcloud_biglake_catalogs describe "${FEDERATED_CATALOG}" \
  --project="${GCP_PROJECT}" \
  --format="value(biglake-service-account-id)" \
  --quiet 2>/dev/null | tr -d '\r\n' || true)"

if [[ -z "${LAKEHOUSE_SA_ID}" ]]; then
  ACCESS_TOKEN="$(gcloud auth print-access-token)"
  CATALOG_JSON="$(curl -fsSL \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "x-goog-user-project: ${GCP_PROJECT}" \
    "https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/${GCP_PROJECT}/catalogs/${FEDERATED_CATALOG}?alt=json")"
  LAKEHOUSE_SA_ID="$(python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("biglake-service-account-id") or d.get("biglake_service_account_id") or d.get("biglakeServiceAccountId") or "")' <<< "${CATALOG_JSON}")"
fi

if [[ -z "${LAKEHOUSE_SA_ID}" ]]; then
  log_err "Could not resolve the BigLake service agent ID from catalog '${FEDERATED_CATALOG}'."
  exit 1
fi
log_info "Resolved Lakehouse Service Agent ID: ${LAKEHOUSE_SA_ID}"

log_step "3.3 Completing OIDC Web Identity trust handshake on AWS IAM role '${AWS_ROLE_NAME}'..."
cat > "${TMP_POLICY_DIR}/trust_final.json" << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "accounts.google.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "accounts.google.com:aud": ["${LAKEHOUSE_SA_ID}"],
          "accounts.google.com:sub": ["${LAKEHOUSE_SA_ID}"]
        }
      }
    }
  ]
}
EOF

aws iam update-assume-role-policy \
  --role-name "${AWS_ROLE_NAME}" \
  --policy-document "file://${TMP_POLICY_DIR}/trust_final.json"

log_info "Waiting 15s for AWS IAM trust policy propagation..."
sleep 15

log_step "3.4 Activating 5-minute background metadata refresh (300s) & verifying Cross-Cloud Cache..."
UPDATE_HELP="$(gcloud_biglake_catalogs update --help 2>&1 || true)"
if grep -q -- '--cross-cloud-cache' <<< "${UPDATE_HELP}"; then
  gcloud_biglake_catalogs update "${FEDERATED_CATALOG}" \
    --project="${GCP_PROJECT}" \
    --refresh-interval="300s" \
    --cross-cloud-cache="enabled" \
    --quiet
else
  gcloud_biglake_catalogs update "${FEDERATED_CATALOG}" \
    --project="${GCP_PROJECT}" \
    --refresh-interval="300s" \
    --quiet
  # Fallback for older Cloud SDK builds without --cross-cloud-cache (uses Iceberg OpenAPI kebab-case JSON keys)
  ACCESS_TOKEN="$(gcloud auth print-access-token)"
  curl -fsSL -X PATCH \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "x-goog-user-project: ${GCP_PROJECT}" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"projects/${GCP_PROJECT}/catalogs/${FEDERATED_CATALOG}\", \"catalog-type\": \"CATALOG_TYPE_FEDERATED\", \"cross-cloud-cache-options\": {\"enabled\": true}}" \
    "https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/${GCP_PROJECT}/catalogs/${FEDERATED_CATALOG}?alt=json&updateMask=cross_cloud_cache_options.enabled" >/dev/null
fi

log_step "3.5 Waiting for initial AWS Glue -> BigQuery metadata sync (typically 30-120s)..."
MAX_ATTEMPTS=24
ATTEMPT=1
while (( ATTEMPT <= MAX_ATTEMPTS )); do
  if bq query --project_id="${GCP_PROJECT}" --location="${GCP_REGION}" --use_legacy_sql=false --quiet --format=none \
    "SELECT COUNT(*) FROM \`${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}.distribution_centers\`" >/dev/null 2>&1; then
    log_ok "Federated AWS Glue Iceberg tables are live and queryable in BigQuery (${GCP_REGION})!"
    break
  fi
  if (( ATTEMPT == MAX_ATTEMPTS )); then
    log_err "Timed out waiting for '${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}.distribution_centers' to finish syncing."
    log_info "Wait 1-2 minutes for the 300s refresh cycle and re-run ./scripts/04_create_bq_graph.sh."
    exit 1
  fi
  log_info "[Attempt ${ATTEMPT}/${MAX_ATTEMPTS}] Waiting 15s for catalog metadata sync..."
  sleep 15
  ATTEMPT=$(( ATTEMPT + 1 ))
done

log_ok "Step 3 complete — federated catalog '${FEDERATED_CATALOG}' synced and verified."
