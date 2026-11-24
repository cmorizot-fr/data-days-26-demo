#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Démo #1 · Étape 3 — Fédération Borderless Lakehouse (BigQuery europe-west1 <-> AWS Glue eu-west-1)
#   1. Rôle IAM AWS least-privilege (Glue crm_callcenter_db + S3 data-days-demo-aws-crm-835872720625)
#   2. Catalogue BigLake fédéré `aws_crm_catalog` en `europe-west1` (sans clés statiques, sans Omni)
#   3. Handshake OIDC Web Identity (`accounts.google.com:sub/aud` = `biglake-service-account-id`)
#   4. Synchro métadonnées automatique (`300s`) + Cross-Cloud Caching (`enabled: true`)
#   5. Audit SQL inter-clouds (4 tables Iceberg + détection des 650 ouvertures J0 hors Mainframe J-1)
# ==============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "${ROOT_DIR}/.env" ]] && source "${ROOT_DIR}/.env"
[[ -f "${ROOT_DIR}/.env.aws.local" ]] && source "${ROOT_DIR}/.env.aws.local"

PROJECT_ID="${GCP_PROJECT_ID:-data-days-demo}"
GCP_REGION="${GCP_REGION:-europe-west1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-835872720625}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
S3_BUCKET="${AWS_S3_BUCKET_CRM:-data-days-demo-aws-crm-835872720625}"
GLUE_DB="${AWS_GLUE_DATABASE:-crm_callcenter_db}"
AWS_ROLE_NAME="${AWS_FEDERATED_ROLE_NAME:-biglake-aws-crm-federated-role}"
CATALOG_ID="${BIGLAKE_AWS_CATALOG_ID:-aws_crm_catalog}"

echo "[1/5] Rôle IAM AWS OIDC (placeholder) + policy lecture seule (${GLUE_DB} & s3://${S3_BUCKET})"
uv run --project "${ROOT_DIR}" python - "${AWS_ACCOUNT_ID}" "${AWS_REGION}" "${GLUE_DB}" "${S3_BUCKET}" "${AWS_ROLE_NAME}" <<'PY'
import boto3, json, sys
aws_account, aws_region, glue_db, s3_bucket, role_name = sys.argv[1:6]
iam = boto3.client("iam")
trust = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": "accounts.google.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {"StringEquals": {
            "accounts.google.com:aud": ["PLACEHOLDER_VALUE"],
            "accounts.google.com:sub": ["PLACEHOLDER_VALUE"],
        }},
    }],
}
try:
    iam.get_role(RoleName=role_name)
except iam.exceptions.NoSuchEntityException:
    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust),
        MaxSessionDuration=43200,
    )
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "GlueCatalogReadOnly",
            "Effect": "Allow",
            "Action": ["glue:GetCatalog", "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables"],
            "Resource": [
                f"arn:aws:glue:{aws_region}:{aws_account}:catalog",
                f"arn:aws:glue:{aws_region}:{aws_account}:database/{glue_db}",
                f"arn:aws:glue:{aws_region}:{aws_account}:table/{glue_db}/*",
            ],
        },
        {
            "Sid": "S3IcebergBucketReadOnly",
            "Effect": "Allow",
            "Action": ["s3:ListBucket", "s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{s3_bucket}", f"arn:aws:s3:::{s3_bucket}/*"],
        },
    ],
}
iam.put_role_policy(RoleName=role_name, PolicyName="crm_glue_s3_readonly_policy", PolicyDocument=json.dumps(policy))
PY

echo "[2/5] Création / vérification du catalogue BigLake fédéré ${CATALOG_ID} (${GCP_REGION})"
if ! CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
  gcloud beta biglake iceberg catalogs describe "${CATALOG_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
    gcloud beta biglake iceberg catalogs create "${CATALOG_ID}" \
      --project="${PROJECT_ID}" \
      --primary-location="${GCP_REGION}" \
      --catalog-type="federated" \
      --federated-catalog-type="glue" \
      --glue-warehouse="${AWS_ACCOUNT_ID}" \
      --glue-aws-region="${AWS_REGION}" \
      --glue-aws-role-arn="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${AWS_ROLE_NAME}" \
      --namespace-filters="${GLUE_DB}"
fi

LAKEHOUSE_SA_ID="$(CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
  gcloud beta biglake iceberg catalogs describe "${CATALOG_ID}" \
    --project="${PROJECT_ID}" \
    --format="value(biglake-service-account-id)" | tr -d '\r\n')"
echo "      BigLake OIDC Service Agent ID = ${LAKEHOUSE_SA_ID}"

echo "[3/5] Finalisation du handshake OIDC Web Identity sur ${AWS_ROLE_NAME}"
uv run --project "${ROOT_DIR}" python - "${AWS_ROLE_NAME}" "${LAKEHOUSE_SA_ID}" <<'PY'
import boto3, json, sys
role_name, sa_id = sys.argv[1:3]
trust_final = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": "accounts.google.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {"StringEquals": {
            "accounts.google.com:aud": [sa_id],
            "accounts.google.com:sub": [sa_id],
        }},
    }],
}
boto3.client("iam").update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(trust_final))
PY

sleep 15

echo "[4/5] Activation refresh-interval=300s & Cross-Cloud Caching"
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" \
  gcloud beta biglake iceberg catalogs update "${CATALOG_ID}" \
    --project="${PROJECT_ID}" \
    --refresh-interval="300s" >/dev/null

uv run --project "${ROOT_DIR}" python - "${PROJECT_ID}" "${CATALOG_ID}" <<'PY'
import certifi, json, ssl, subprocess, sys, urllib.request
project_id, catalog_id = sys.argv[1:3]
token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
url = f"https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/{project_id}/catalogs/{catalog_id}?alt=json&updateMask=cross_cloud_cache_options.enabled"
req = urllib.request.Request(
    url,
    data=json.dumps({
        "name": f"projects/{project_id}/catalogs/{catalog_id}",
        "catalog-type": "CATALOG_TYPE_FEDERATED",
        "cross-cloud-cache-options": {"enabled": True},
    }).encode("utf-8"),
    method="PATCH",
    headers={"Authorization": f"Bearer {token}", "x-goog-user-project": project_id, "Content-Type": "application/json"},
)
urllib.request.urlopen(req, context=ssl.create_default_context(cafile=certifi.where()), timeout=20).read()
PY

echo "[5/5] Audit SQL inter-clouds (${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.* <-> raw_bank.cbk_*)"
bq --location="${GCP_REGION}" query --project_id="${PROJECT_ID}" --use_legacy_sql=false --label datacloud:antigravity \
  "SELECT
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.crm_branches_ref\`) AS branches_450,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.crm_customers\`) AS aws_customers_80k,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.crm_account_portfolio\`) AS aws_accounts_95k,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.crm_interactions\`) AS aws_interactions_320k,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${CATALOG_ID}.${GLUE_DB}.crm_account_portfolio\` a
      LEFT JOIN \`${PROJECT_ID}.raw_bank.cbk_accounts_master\` m USING (account_id)
      WHERE m.account_id IS NULL) AS j0_orphan_accounts_650"
