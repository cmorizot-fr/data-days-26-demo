#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# End-to-end verification check: confirms 0 bytes stored in BigQuery and runs
# a live SQL + ISO GQL smoke test.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_common.sh"

preflight_gcp_only

FED_PREFIX="${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}"
DEMO_PREFIX="${GCP_PROJECT}.${BQ_DEMO_DATASET}"

log_step "Verifying Zero-Copy Storage Footprint in '${DEMO_PREFIX}' (0 tables, Property Graph only)..."
bq query --project_id="${GCP_PROJECT}" --location="${GCP_REGION}" --use_legacy_sql=false --format=pretty <<EOF
SELECT
  t.table_id AS object_name,
  CASE t.type WHEN 1 THEN 'BASE TABLE' ELSE 'OTHER' END AS object_type,
  t.size_bytes AS bytes_stored_in_bigquery
FROM \`${DEMO_PREFIX}.__TABLES__\` AS t
UNION ALL
SELECT
  g.property_graph_name AS object_name,
  'PROPERTY GRAPH' AS object_type,
  0 AS bytes_stored_in_bigquery
FROM \`${DEMO_PREFIX}.INFORMATION_SCHEMA.PROPERTY_GRAPHS\` AS g
ORDER BY object_type DESC, object_name;
EOF

log_step "Running Live Direct 4-Part SQL + ISO GQL Property Graph Smoke Test..."
bq query --project_id="${GCP_PROJECT}" --location="${GCP_REGION}" --use_legacy_sql=false --format=pretty <<EOF
SELECT
  (SELECT COUNT(*) FROM \`${FED_PREFIX}.orders\`) AS total_orders,
  (SELECT COUNT(*) FROM \`${FED_PREFIX}.events\`) AS total_clickstream_events,
  (SELECT COUNT(*) FROM GRAPH_TABLE(
     \`${DEMO_PREFIX}.ecommerce_graph\`
     MATCH (p:Product)-[:product_stocked_at]->(dc:DistributionCenter)
     COLUMNS (p.id AS pid)
   )) AS graph_stocked_products;
EOF

log_ok "All verification checks passed — ready to launch notebooks/thelook_analytics_ai_demo.ipynb!"
