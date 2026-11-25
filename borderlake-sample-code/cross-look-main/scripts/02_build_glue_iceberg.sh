#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Step 2: Materialize all 7 raw Parquet tables on Amazon S3 as native managed
#         Apache Iceberg tables in AWS Glue Data Catalog via Amazon Athena CTAS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_common.sh"

preflight_checks

run_athena_sql() {
  local sql="$1"
  local qid
  qid="$(aws athena start-query-execution \
    --region "${AWS_REGION}" \
    --work-group "${ATHENA_WORKGROUP}" \
    --query-string "${sql}" \
    --result-configuration "OutputLocation=s3://${S3_BUCKET}/athena-results/" \
    --query 'QueryExecutionId' --output text | tr -d '\r\n')"

  while true; do
    local state
    state="$(aws athena get-query-execution \
      --region "${AWS_REGION}" \
      --query-execution-id "${qid}" \
      --query 'QueryExecution.Status.State' --output text | tr -d '\r\n')"
    if [[ "${state}" == "SUCCEEDED" ]]; then
      printf "%s" "${qid}"
      return 0
    elif [[ "${state}" == "FAILED" || "${state}" == "CANCELLED" ]]; then
      local reason
      reason="$(aws athena get-query-execution \
        --region "${AWS_REGION}" \
        --query-execution-id "${qid}" \
        --query 'QueryExecution.Status.StateChangeReason' --output text)"
      log_err "Athena query (${qid}) ${state}: ${reason}"
      log_info "SQL was: ${sql}"
      exit 1
    fi
    sleep 2
  done
}

log_step "2.1 Ensuring AWS Glue database '${GLUE_DB}' exists in ${AWS_REGION}..."
aws glue get-database --region "${AWS_REGION}" --name "${GLUE_DB}" >/dev/null 2>&1 || \
  aws glue create-database \
    --region "${AWS_REGION}" \
    --database-input "{\"Name\": \"${GLUE_DB}\", \"Description\": \"TheLook eCommerce Apache Iceberg tables federated to Lakehouse for Apache Iceberg\"}"

log_step "2.2 Verifying raw Parquet staging files exist in s3://${S3_BUCKET}/raw/..."
for tbl in distribution_centers products users events inventory_items orders order_items; do
  s3_listing="$(aws s3 ls "s3://${S3_BUCKET}/raw/${tbl}/" --region "${AWS_REGION}" 2>/dev/null || true)"
  if ! grep -q "\.parquet" <<< "${s3_listing}"; then
    log_err "No Parquet files found under s3://${S3_BUCKET}/raw/${tbl}/ — run ./scripts/01_export_public_bq_to_s3.sh first."
    exit 1
  fi
done

log_step "2.3 Materializing all 7 managed Apache Iceberg tables in AWS Glue (${GLUE_DB})..."

create_iceberg_table() {
  local table="$1"
  local staging_cols="$2"
  local select_expr="$3"

  log_info "Building Apache Iceberg table ${GLUE_DB}.${table}..."
  run_athena_sql "DROP TABLE IF EXISTS ${GLUE_DB}.${table}_staging" >/dev/null
  run_athena_sql "DROP TABLE IF EXISTS ${GLUE_DB}.${table}" >/dev/null
  aws s3 rm "s3://${S3_BUCKET}/iceberg/${table}/" --recursive --region "${AWS_REGION}" >/dev/null 2>&1 || true

  run_athena_sql "CREATE EXTERNAL TABLE ${GLUE_DB}.${table}_staging (${staging_cols})
    STORED AS PARQUET
    LOCATION 's3://${S3_BUCKET}/raw/${table}/'" >/dev/null

  run_athena_sql "CREATE TABLE ${GLUE_DB}.${table}
    WITH (
      table_type = 'ICEBERG',
      is_external = false,
      location = 's3://${S3_BUCKET}/iceberg/${table}/',
      format = 'PARQUET'
    ) AS
    SELECT ${select_expr} FROM ${GLUE_DB}.${table}_staging" >/dev/null

  # Remove Hive external staging table so AWS Glue exposes pure Apache Iceberg tables
  run_athena_sql "DROP TABLE ${GLUE_DB}.${table}_staging" >/dev/null
}

create_iceberg_table "distribution_centers" \
  "id BIGINT, name STRING, latitude DOUBLE, longitude DOUBLE, distribution_center_geom STRING" \
  "id, name, latitude, longitude, distribution_center_geom"

create_iceberg_table "products" \
  "id BIGINT, cost DOUBLE, category STRING, name STRING, brand STRING, retail_price DOUBLE, department STRING, sku STRING, distribution_center_id BIGINT" \
  "id, cost, category, name, brand, retail_price, department, sku, distribution_center_id"

create_iceberg_table "users" \
  "id BIGINT, first_name STRING, last_name STRING, email STRING, age BIGINT, gender STRING, state STRING, street_address STRING, postal_code STRING, city STRING, country STRING, latitude DOUBLE, longitude DOUBLE, traffic_source STRING, created_at STRING, user_geom STRING" \
  "id, first_name, last_name, email, age, gender, state, street_address, postal_code, city, country, latitude, longitude, traffic_source, CAST(created_at AS TIMESTAMP(6)) AS created_at, user_geom"

create_iceberg_table "events" \
  "id BIGINT, user_id BIGINT, sequence_number BIGINT, session_id STRING, created_at STRING, ip_address STRING, city STRING, state STRING, postal_code STRING, browser STRING, traffic_source STRING, uri STRING, event_type STRING" \
  "id, user_id, sequence_number, session_id, CAST(created_at AS TIMESTAMP(6)) AS created_at, ip_address, city, state, postal_code, browser, traffic_source, uri, event_type"

create_iceberg_table "inventory_items" \
  "id BIGINT, product_id BIGINT, created_at STRING, sold_at STRING, cost DOUBLE, product_category STRING, product_name STRING, product_brand STRING, product_retail_price DOUBLE, product_department STRING, product_sku STRING, product_distribution_center_id BIGINT" \
  "id, product_id, CAST(created_at AS TIMESTAMP(6)) AS created_at, CAST(sold_at AS TIMESTAMP(6)) AS sold_at, cost, product_category, product_name, product_brand, product_retail_price, product_department, product_sku, product_distribution_center_id"

create_iceberg_table "orders" \
  "order_id BIGINT, user_id BIGINT, status STRING, gender STRING, created_at STRING, returned_at STRING, shipped_at STRING, delivered_at STRING, num_of_item BIGINT" \
  "order_id, user_id, status, gender, CAST(created_at AS TIMESTAMP(6)) AS created_at, CAST(returned_at AS TIMESTAMP(6)) AS returned_at, CAST(shipped_at AS TIMESTAMP(6)) AS shipped_at, CAST(delivered_at AS TIMESTAMP(6)) AS delivered_at, num_of_item"

create_iceberg_table "order_items" \
  "id BIGINT, order_id BIGINT, user_id BIGINT, product_id BIGINT, inventory_item_id BIGINT, status STRING, created_at STRING, shipped_at STRING, delivered_at STRING, returned_at STRING, sale_price DOUBLE" \
  "id, order_id, user_id, product_id, inventory_item_id, status, CAST(created_at AS TIMESTAMP(6)) AS created_at, CAST(shipped_at AS TIMESTAMP(6)) AS shipped_at, CAST(delivered_at AS TIMESTAMP(6)) AS delivered_at, CAST(returned_at AS TIMESTAMP(6)) AS returned_at, sale_price"

log_step "2.4 Verifying registered Apache Iceberg tables and row counts in AWS Glue..."
aws glue get-tables \
  --region "${AWS_REGION}" \
  --database-name "${GLUE_DB}" \
  --query "TableList[].{Table:Name, Type:Parameters.table_type}" \
  --output table

COUNT_QID="$(run_athena_sql "SELECT 'events' AS table_name, COUNT(*) AS row_count FROM ${GLUE_DB}.events
  UNION ALL SELECT 'inventory_items', COUNT(*) FROM ${GLUE_DB}.inventory_items
  UNION ALL SELECT 'order_items', COUNT(*) FROM ${GLUE_DB}.order_items
  UNION ALL SELECT 'orders', COUNT(*) FROM ${GLUE_DB}.orders
  UNION ALL SELECT 'users', COUNT(*) FROM ${GLUE_DB}.users
  UNION ALL SELECT 'products', COUNT(*) FROM ${GLUE_DB}.products
  UNION ALL SELECT 'distribution_centers', COUNT(*) FROM ${GLUE_DB}.distribution_centers
  ORDER BY row_count DESC")"

aws athena get-query-results \
  --region "${AWS_REGION}" \
  --query-execution-id "${COUNT_QID}" \
  --query "ResultSet.Rows[].Data[].VarCharValue" \
  --output table

log_ok "Step 2 complete — all 7 Apache Iceberg tables registered in AWS Glue (${GLUE_DB})."
