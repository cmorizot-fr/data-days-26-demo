"""
Fédération Borderless Lakehouse sans clé (OIDC Web Identity + Cross-Cloud Caching)
entre BigQuery (`europe-west1`) et AWS Glue Data Catalog (`eu-west-1` · `crm_callcenter_db`).
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import time
import urllib.request
from pathlib import Path

import boto3
import certifi
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
BIGLAKE_EXT_URL = "https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions"


def build_oidc_trust_policy(subject_id: str) -> dict:
    """Construit la trust policy OIDC Web Identity verrouillée sur le Service Agent BigLake."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": "accounts.google.com"},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        "accounts.google.com:aud": [subject_id],
                        "accounts.google.com:sub": [subject_id],
                    }
                },
            }
        ],
    }


def ensure_aws_readonly_role(
    aws_account: str, aws_region: str, glue_db: str, s3_bucket: str, role_name: str
) -> str:
    """Crée ou met à jour le rôle IAM AWS least-privilege en lecture seule (Glue + S3)."""
    iam = boto3.client("iam")
    try:
        role_arn = iam.get_role(RoleName=role_name)["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        role_arn = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(build_oidc_trust_policy("PLACEHOLDER_VALUE")),
            MaxSessionDuration=43200,
            Description="Keyless OIDC federation role for GCP BigLake Cross-Cloud Lakehouse",
        )["Role"]["Arn"]

    permissions = {
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
                    "glue:GetTables",
                ],
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
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="crm_glue_s3_readonly_policy",
        PolicyDocument=json.dumps(permissions),
    )
    return role_arn


def complete_oidc_and_enable_cache(
    project_id: str, catalog_id: str, role_name: str, service_agent_id: str
) -> dict:
    """Verrouille l'OIDC AWS sur le Service Agent BigLake et active le Cross-Cloud Caching."""
    boto3.client("iam").update_assume_role_policy(
        RoleName=role_name,
        PolicyDocument=json.dumps(build_oidc_trust_policy(service_agent_id)),
    )
    time.sleep(15)

    env = {**os.environ, "CLOUDSDK_METRICS_ENVIRONMENT": "datacloud.antigravity"}
    subprocess.run(
        [
            "gcloud", "beta", "biglake", "iceberg", "catalogs", "update", catalog_id,
            f"--project={project_id}", "--refresh-interval=300s", "--quiet",
        ],
        check=True,
        env=env,
    )

    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    url = (
        f"{BIGLAKE_EXT_URL}/projects/{project_id}/catalogs/{catalog_id}"
        "?alt=json&updateMask=cross_cloud_cache_options.enabled"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps({
            "name": f"projects/{project_id}/catalogs/{catalog_id}",
            "catalog-type": "CATALOG_TYPE_FEDERATED",
            "cross-cloud-cache-options": {"enabled": True},
        }).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "x-goog-user-project": project_id,
            "Content-Type": "application/json",
        },
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.aws.local", override=True)
    project = os.getenv("GCP_PROJECT_ID", "data-days-demo")
    catalog = os.getenv("BIGLAKE_AWS_CATALOG_ID", "aws_crm_catalog")
    role = os.getenv("AWS_FEDERATED_ROLE_NAME", "biglake-aws-crm-federated-role")
    ensure_aws_readonly_role(
        aws_account=os.getenv("AWS_ACCOUNT_ID", "835872720625"),
        aws_region=os.getenv("AWS_REGION", "eu-west-1"),
        glue_db=os.getenv("AWS_GLUE_DATABASE", "crm_callcenter_db"),
        s3_bucket=os.getenv("AWS_S3_BUCKET_CRM", "data-days-demo-aws-crm-835872720625"),
        role_name=role,
    )
    sa_id = subprocess.check_output(
        [
            "gcloud", "beta", "biglake", "iceberg", "catalogs", "describe", catalog,
            f"--project={project}", "--format=value(biglake-service-account-id)",
        ],
        text=True,
    ).strip()
    status = complete_oidc_and_enable_cache(project, catalog, role, sa_id)
    print(json.dumps(status, indent=2))
