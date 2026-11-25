#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Step 4: Create the companion BigQuery dataset (${BQ_DEMO_DATASET}) and the
#         native ISO GQL Property Graph (${BQ_DEMO_DATASET}.ecommerce_graph)
#         wrapping the 4-part federated Iceberg tables directly.
#
# Because the federated runtime catalog uses a neutral name ('thelook_catalog'),
# SQL, GIS, and AI.* queries read `${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}.*`
# directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_common.sh"

preflight_gcp_only
enable_required_gcp_apis

log_step "4.1 Ensuring BigQuery graph dataset '${GCP_PROJECT}:${BQ_DEMO_DATASET}' exists in ${GCP_REGION}..."
if ! bq --project_id="${GCP_PROJECT}" show --dataset "${GCP_PROJECT}:${BQ_DEMO_DATASET}" >/dev/null 2>&1; then
  bq --project_id="${GCP_PROJECT}" --location="${GCP_REGION}" mk --dataset \
    --description="TheLook omnichannel e-commerce customer journey and supply-chain Property Graph." \
    "${GCP_PROJECT}:${BQ_DEMO_DATASET}"
else
  bq --project_id="${GCP_PROJECT}" update --dataset \
    --description="TheLook omnichannel e-commerce customer journey and supply-chain Property Graph." \
    "${GCP_PROJECT}:${BQ_DEMO_DATASET}" >/dev/null
fi

FED_PREFIX="${GCP_PROJECT}.${FEDERATED_CATALOG}.${GLUE_DB}"
DEMO_PREFIX="${GCP_PROJECT}.${BQ_DEMO_DATASET}"

log_step "4.2 Creating native ISO GQL Property Graph '${DEMO_PREFIX}.ecommerce_graph' directly over '${FED_PREFIX}.*'..."
bq query --project_id="${GCP_PROJECT}" --location="${GCP_REGION}" --use_legacy_sql=false --quiet <<EOF
CREATE OR REPLACE PROPERTY GRAPH \`${DEMO_PREFIX}.ecommerce_graph\`
NODE TABLES (
  \`${FED_PREFIX}.products\` AS Product
    KEY (id)
    LABEL Product PROPERTIES (
      id OPTIONS (description="Unique identifier for the product."),
      cost OPTIONS (description="Cost to produce the product."),
      category OPTIONS (description="Category of the product (e.g., Tops, Sets, Accessories)."),
      name OPTIONS (description="Full name/title of the product."),
      brand OPTIONS (description="Brand name of the product."),
      retail_price OPTIONS (description="Price at which the product is sold."),
      department OPTIONS (description="Department target (e.g., Men, Women)."),
      sku OPTIONS (description="Stock Keeping Unit."),
      distribution_center_id OPTIONS (description="ID of the distribution center where stocked."),
      MEASURE(SUM(cost)) AS total_cost OPTIONS (description="Total cost of products."),
      MEASURE(COUNT(id)) AS product_count OPTIONS (description="Total count of products.")
    ),

  \`${FED_PREFIX}.distribution_centers\` AS DistributionCenter
    KEY (id)
    LABEL DistributionCenter PROPERTIES (
      id OPTIONS (description="Unique identifier for the distribution center."),
      name OPTIONS (description="Name of the distribution center."),
      latitude OPTIONS (description="Latitude coordinate."),
      longitude OPTIONS (description="Longitude coordinate."),
      distribution_center_geom OPTIONS (description="Geospatial WKT point of the distribution center.")
    ),

  \`${FED_PREFIX}.orders\` AS \`Order\`
    KEY (order_id)
    LABEL \`Order\` PROPERTIES (
      order_id OPTIONS (description="Unique identifier for the order."),
      user_id OPTIONS (description="ID of the user who placed the order."),
      status OPTIONS (description="Current status of the order (e.g., Cancelled, Complete)."),
      gender OPTIONS (description="Gender associated with the order/user."),
      created_at OPTIONS (description="Timestamp when order was created."),
      returned_at OPTIONS (description="Timestamp when returned, if applicable."),
      shipped_at OPTIONS (description="Timestamp when shipped."),
      delivered_at OPTIONS (description="Timestamp when delivered."),
      num_of_item OPTIONS (description="Number of items in the order."),
      MEASURE(COUNT(order_id)) AS order_count OPTIONS (description="Total count of orders.")
    ),

  \`${FED_PREFIX}.order_items\` AS OrderItem
    KEY (id)
    LABEL OrderItem PROPERTIES (
      id OPTIONS (description="Unique identifier for the line item."),
      order_id OPTIONS (description="ID of the order this item belongs to."),
      user_id OPTIONS (description="ID of the user who placed the order."),
      product_id OPTIONS (description="ID of the product ordered."),
      inventory_item_id OPTIONS (description="ID of the specific inventory item."),
      status OPTIONS (description="Status of this item (e.g., Cancelled, Complete)."),
      created_at OPTIONS (description="Timestamp when added to order."),
      shipped_at OPTIONS (description="Timestamp when shipped."),
      delivered_at OPTIONS (description="Timestamp when delivered."),
      returned_at OPTIONS (description="Timestamp when returned."),
      sale_price OPTIONS (description="Actual price at which sold."),
      MEASURE(SUM(sale_price)) AS total_revenue OPTIONS (description="Total revenue from sold items."),
      MEASURE(COUNT(id)) AS item_count OPTIONS (description="Total count of order items.")
    ),

  \`${FED_PREFIX}.users\` AS User
    KEY (id)
    LABEL User PROPERTIES (
      id OPTIONS (description="Unique identifier for the user."),
      first_name OPTIONS (description="First name of the user."),
      last_name OPTIONS (description="Last name of the user."),
      email OPTIONS (description="Email address of the user."),
      age OPTIONS (description="Age of the user."),
      gender OPTIONS (description="Gender of the user."),
      state OPTIONS (description="State where the user resides."),
      street_address OPTIONS (description="Street address of the user."),
      postal_code OPTIONS (description="Postal code of the user."),
      city OPTIONS (description="City where the user resides."),
      country OPTIONS (description="Country where the user resides."),
      latitude OPTIONS (description="Latitude coordinate of the user's location."),
      longitude OPTIONS (description="Longitude coordinate of the user's location."),
      traffic_source OPTIONS (description="Acquisition channel (e.g., Search, Organic, Email)."),
      created_at OPTIONS (description="Timestamp when account was created."),
      user_geom OPTIONS (description="Geospatial WKT point of the user's location."),
      CONCAT(first_name, ' ', last_name) AS full_name OPTIONS (description="Concatenated full name."),
      MEASURE(COUNT(id)) AS user_count OPTIONS (description="Total count of users.")
    )
)
EDGE TABLES (
  \`${FED_PREFIX}.orders\` AS placed_order
    KEY (order_id)
    SOURCE KEY (order_id) REFERENCES \`Order\` (order_id)
    DESTINATION KEY (user_id) REFERENCES User (id)
    LABEL placed_order NO PROPERTIES,

  \`${FED_PREFIX}.products\` AS product_stocked_at
    KEY (id)
    SOURCE KEY (id) REFERENCES Product (id)
    DESTINATION KEY (distribution_center_id) REFERENCES DistributionCenter (id)
    LABEL product_stocked_at NO PROPERTIES,

  \`${FED_PREFIX}.order_items\` AS belongs_to_order
    KEY (id)
    SOURCE KEY (id) REFERENCES OrderItem (id)
    DESTINATION KEY (order_id) REFERENCES \`Order\` (order_id)
    LABEL belongs_to_order NO PROPERTIES,

  \`${FED_PREFIX}.order_items\` AS includes_product
    KEY (id)
    SOURCE KEY (id) REFERENCES OrderItem (id)
    DESTINATION KEY (product_id) REFERENCES Product (id)
    LABEL includes_product NO PROPERTIES
);
EOF

log_ok "Step 4 complete — zero-copy Property Graph '${DEMO_PREFIX}.ecommerce_graph' ready."
