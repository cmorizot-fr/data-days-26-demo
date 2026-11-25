#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Interactive provisioning orchestrator for the Cross-Look Lakehouse Demo:
#   0. Auto-detects parameters from active `gcloud` & `aws` CLI configs, asks to
#      confirm (or enter another existing GCP project ID), saves `.env`, and runs
#      a full GCP + AWS + CLI pre-flight check (asking permission to enable/grant
#      any missing services or IAM roles).
#   1. Exports bigquery-public-data.thelook_ecommerce -> GCS staging -> Amazon S3
#   2. Materializes 7 managed Apache Iceberg tables in AWS Glue via Amazon Athena
#   3. Configures keyless OIDC federation + Cross-Cloud Caching on neutral catalog 'thelook_catalog'
#   4. Creates the zero-copy BigQuery ISO GQL Property Graph
#   5. Runs live SQL + Property Graph verification checks
#
# Usage:
#   ./deploy.sh                             # Interactive confirmation + pre-flight + deploy
#   ./deploy.sh --yes                       # Non-interactive (auto-confirm detected config & fixes)
#   ./deploy.sh --skip-export               # Reuse existing raw Parquet files in S3
#   ./deploy.sh --skip-glue                 # Reuse existing AWS Glue Iceberg tables

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/00_common.sh"

AUTO_APPROVE="false"
SKIP_EXPORT="false"
SKIP_GLUE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      AUTO_APPROVE="true"
      shift
      ;;
    --skip-export)
      SKIP_EXPORT="true"
      shift
      ;;
    --skip-glue)
      SKIP_GLUE="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--yes] [--skip-export] [--skip-glue]"
      exit 0
      ;;
    *)
      log_err "Unknown option: $1"
      exit 1
      ;;
  esac
done

# 1. Auto-detect CLI config, display summary, ask for confirmation (or another existing GCP project), & save .env
confirm_parameters_interactively "${AUTO_APPROVE}"

# 2. Run full read-only pre-flight across CLI, GCP & AWS; ask permission before enabling APIs or granting roles
run_full_preflight "${AUTO_APPROVE}" "${SKIP_EXPORT}" "${SKIP_GLUE}"

# 3. Display the AWS & Google Cloud resource creation plan and ask for final 'go' before provisioning
confirm_resource_plan "${AUTO_APPROVE}" "${SKIP_EXPORT}" "${SKIP_GLUE}"

if [[ "${SKIP_EXPORT}" == "false" ]]; then
  "${REPO_ROOT}/scripts/01_export_public_bq_to_s3.sh"
else
  log_info "Skipping Step 1 (--skip-export)."
fi

if [[ "${SKIP_GLUE}" == "false" ]]; then
  "${REPO_ROOT}/scripts/02_build_glue_iceberg.sh"
else
  log_info "Skipping Step 2 (--skip-glue)."
fi

"${REPO_ROOT}/scripts/03_federate_biglake_and_cache.sh"
"${REPO_ROOT}/scripts/04_create_bq_graph.sh"
"${REPO_ROOT}/scripts/verify_setup.sh"

cat <<EOF

==============================================================================
 🎉 Deployment Complete!
==============================================================================
  Notebook : notebooks/thelook_analytics_ai_demo.ipynb
  Tables   : ${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}.* (Location: ${GCP_REGION})
  Graph    : ${GCP_PROJECT}.${BQ_DEMO_DATASET}.ecommerce_graph
  Catalog  : https://console.cloud.google.com/dataplex/search?project=${GCP_PROJECT}

  Live Demo Flow:
    1. Analytics & AI (Cells 0–4)           : Run 15 concurrent SQL + GIS + AI.* + Graph queries
                                              directly on '${FEDERATED_CATALOG}.${GLUE_DB}.*'.
    2. Conversational Graph Agent (Cell 5)  : Click the BigQuery Studio deep-link -> "Chat" ->
                                              "Create Agent" on 'ecommerce_graph' for Q&A.
    3. Storage & Telemetry (Cells 6–7)      : Reveal 0 bytes in BigQuery, live S3 Iceberg URIs behind
                                              '${FEDERATED_CATALOG}', and Cache Analysis.
    4. Knowledge Catalog (Cell 8)           : Inspect automatic cross-cloud cataloging & live
                                              ':lookupContext' YAML across S3 Iceberg + Property Graph.

  Next Steps:
    • Run in BigQuery Studio:
        1. Open https://console.cloud.google.com/bigquery?project=${GCP_PROJECT}
        2. In Explorer -> Notebooks -> ⋮ -> Upload notebook:
           select notebooks/thelook_analytics_ai_demo.ipynb and click Upload.
        3. Click "Run all" and approve the one-time Sign-in prompt.
==============================================================================
EOF
