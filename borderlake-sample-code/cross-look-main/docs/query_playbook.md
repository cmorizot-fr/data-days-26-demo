# Cross-Look Query Playbook — 15 Parallel Queries + Zero-Copy Cross-Cloud Reveal

This playbook documents every SQL and ISO GQL statement executed by [`notebooks/thelook_analytics_ai_demo.ipynb`](../notebooks/thelook_analytics_ai_demo.ipynb), along with sample outputs and presenter notes for running the **"Zero-Spoiler Live Reveal"** storyline.

- **On-Screen Catalog & Graph (Part 1 — Analytics & AI + Part 2 — Agent)**: `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.*` *(7 tables queried directly)* + `<PROJECT_ID>.thelook_commerce.ecommerce_graph` *(zero-copy ISO GQL Property Graph in `us-east4` — behaves identically to native BigQuery tables and property graphs with zero mention of Amazon S3, AWS Glue, or Apache Iceberg)*
- **Physical Storage Layer (Revealed in Part 3 — The Twist)**: Managed Apache Iceberg tables on Amazon S3 (`s3://<S3_BUCKET>/iceberg/<table>`) + AWS Glue Data Catalog in `us-east-1`, federated directly into `<PROJECT_ID>.thelook_catalog.thelook_ecommerce` via a Lakehouse runtime catalog with regional Intelligent caching (`0 bytes` stored in BigQuery)
- **Dynamic Date Windows**: In [`notebooks/thelook_analytics_ai_demo.ipynb`](../notebooks/thelook_analytics_ai_demo.ipynb), Setup Cell `0` automatically detects `MAX(created_at)` from your exported `thelook_ecommerce` snapshot and parameterizes all rolling 14d / 30d / 90d / 180d, forecast, anomaly, and YoY windows. The standalone SQL snippets below show concrete example dates (`2026-06-30` snapshot anchor) so you can also paste any query directly into the BigQuery Studio SQL editor after replacing `<PROJECT_ID>`.

---

## Presenter Pre-Flight (30 Seconds)

1. **BigQuery Studio Explorer Sidebar**: Because the federated runtime catalog uses the neutral name **`thelook_catalog`**, both `<PROJECT_ID>.thelook_catalog.thelook_ecommerce` and `<PROJECT_ID>.thelook_commerce.ecommerce_graph` appear completely neutral on screen — simply avoid clicking into an individual table's **Details** tab (which lists its `s3://` URI) until Part 3 (The Twist).
2. **Query Location**: Leave BigQuery Studio query settings on **Auto-select** (or `us-east4` / your configured `GCP_REGION`).
3. **Warm vs. Cold Regional Block Cache**:
   - Cross-Cloud Cache (`--cross-cloud-cache=enabled`) is automatically enabled when `thelook_catalog` is created.
   - The first run of Step 2 reads compressed Parquet blocks from Amazon S3 (`~117 MB`) and populates the regional block cache; subsequent runs serve `~100%` from local regional cache (`0.00 MB` sent over the wire) even with `use_query_cache=False`.

---

## 4-Part Demo & 15-Query Storyline Matrix

| Part | Engine / Focus | # | Capability Showcased | Typical Compute | Business Question |
| :--- | :--- | :- | :--- | :--- | :--- |
| **Part 1: Analytics & AI** | **`SQL`** | **Q1** | 4-table full-funnel join (2.42M clicks + 490k stock + orders) + `QUALIFY` | ~7 slot-s (~3 slots) | Which top 3 brands per department convert product views into the highest gross profit? |
| **Part 1: Analytics & AI** | **`SQL`** | **Q2** | 2.42M `events` × 1,826 daily rolling 14d regional funnels | **~1,190 slot-s (~119 slots)** | How efficiently does each acquisition channel convert product views to carts and purchases? |
| **Part 1: Analytics & AI** | **`SQL`** | **Q3** | 490k physical SKUs × 2,373 daily snapshots (~600M SKU-days) | **~460 slot-s (~70 slots)** | How much working capital is tied up in unsold warehouse stock and rolling 30d turnover? |
| **Part 1: Analytics & AI** | **`SQL`** | **Q4** | 2.42M `events` × 1,826 daily rolling 30d windows | **~1,060 slot-s (~145 slots)** | How do rolling 30-day cart abandonment and conversion volatility behave across channels & browsers? |
| **Part 1: Analytics & AI** | **`SQL`** | **Q5** | 181k order items × 2,191 daily rolling 90d brand windows | **~209 slot-s (~31 slots)** | How does each brand's current 90d profit compare to its all-time peak and worst return-rate spikes? |
| **Part 1: Analytics & AI** | **`GIS`** | **Q6** | 16M+ spherical `ST_DISTANCE` checks across 1,200+ US micro-hubs | **~159 slot-s (~55 slots)** | Which US warehouses suffer from excessive long-haul shipping (> 1,500 km) vs. local micro-hubs? |
| **Part 1: Analytics & AI** | **`GIS`** | **Q7** | Spatial nearest-neighbor across US buyers × DCs × city hubs | **~598 slot-s (~109 slots)** | How many freight-kilometers could we save via nearest-warehouse vs. city micro-hub routing? |
| **Part 1: Analytics & AI** | **`GIS`** | **Q8** | 12,000+ daily `ST_CONVEXHULL` + `ST_AREA` + `ST_CENTROID` polygons | **~55 slot-s (~9 slots)** | What is the rolling 180d 300 km catchment revenue, convex-hull area, and demand centroid per DC? |
| **Part 1: Analytics & AI** | **`AI.*`** | **Q9** | `AI.FORECAST` (`TimesFM 2.5`, multi-series `id_cols`) | ~12 slot-s (~2 slots) | What is the 4-week revenue forecast and 90% confidence interval for Men's vs. Women's apparel? |
| **Part 1: Analytics & AI** | **`AI.*`** | **Q10** | `AI.DETECT_ANOMALIES` (`TimesFM 2.5`) | ~31 slot-s (~4 slots) | Which recent days experienced statistically anomalous order spikes vs. historical baseline? |
| **Part 1: Analytics & AI** | **`AI.*`** | **Q11** | Clickstream browse tiers + hubs → `AI.KEY_DRIVERS` | ~29 slot-s (~6 slots) | Which 6-D combinations of dept, category, hub, country, channel & browse tier drove YoY growth? |
| **Part 1: Analytics & AI** | **`AI.*`** | **Q12** | `AI.IF` + `AI.CLASSIFY` (zero-shot semantic filter & tagging) | ~38 slot-s (~7 slots) | Which top-selling outerwear SKUs are true winter/weather gear, and what campaign persona fits each? |
| **Part 1: Analytics & AI** | **`AI.*`** | **Q13** | Micro-hub `ST_DISTANCE` simulation + `AI.GENERATE` (`output_schema`) | **~120 slot-s (~30 slots)** | Synthesize SQL + GIS micro-hub KPIs per warehouse into typed executive diagnoses and action plans. |
| **Part 1: Analytics & AI** | **`Graph`** | **Q14** | Standalone ISO GQL 8-hop traversal (`GRAPH ... MATCH p = ... RETURN`) | ~5 slot-s (~2 slots) | Across 8 graph hops (`Warehouse → Product → OrderItem → Order → User ← Order ← OrderItem ← Product ← Warehouse`), which repeat-purchase category transitions drive downstream revenue & hub switches? |
| **Part 1: Analytics & AI** | **`All-in-One`** | **Q15** | **`GRAPH_TABLE` + Relational SQL + Spherical GIS + `AI.GENERATE`** | **~96 slot-s (~13 slots)** | Touching **all 7 dataset tables in one query**, diagnose long-haul corridors across Graph, SQL, and GIS, and synthesize typed Gemini executive plans. |
| **Part 2: Agent** | **`Chat`** | **4B** | **Conversational Analytics on `ecommerce_graph`** (`GRAPH_EXPAND` / `GQL` + `MEASURE`s) | Live Agent | **Still before revealing S3**: click **Chat** on `thelook_commerce.ecommerce_graph` in BigQuery Studio to ask multi-hop questions in plain English with zero fanout hallucinations. |
| **Part 3: The Twist** | **Audit** | **R1–R2** | `__TABLES__`, `PROPERTY_GRAPHS`, `lookupEntry` & `JOBS_BY_PROJECT` | < 1 slot-s | **"How much data did we copy into BigQuery?" → `0 bytes` — all 15 queries + Graph Chat ran live over Apache Iceberg on Amazon S3!** |
| **Part 4: Knowledge Catalog** | **Catalog** | **KC1** | `searchEntries`, `lookupEntry?view=ALL`, `:lookupContext` (`@biglake` + `@bigquery`) | REST API | Inspect automatic storage-agnostic cataloging, schemas, storage URIs, and LLM-ready YAML context across all 11 S3 Iceberg + Property Graph entries. |

---

## Part 1 — Analytics & AI

### `SQL` — Elastic Analytical GoogleSQL (`Q1`–`Q5`)

#### Query 1: Full-Funnel Brand Profitability Leaderboard (Views → Stock → Margin)
Joins `events`, `inventory_items`, `order_items`, and `products` with GoogleSQL `QUALIFY` window ranking to isolate the top 3 profit-generating brands per department.

```sql
-- Query 1: Full-Funnel Brand Profitability Leaderboard
WITH product_clicks AS (
  SELECT
    SAFE_CAST(REGEXP_EXTRACT(uri, r'/product/(\d+)') AS INT64) AS product_id,
    COUNT(*) AS product_page_views
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.events`
  WHERE event_type = 'product'
  GROUP BY product_id
),
product_stock AS (
  SELECT
    product_id,
    COUNTIF(sold_at IS NULL) AS unsold_units
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.inventory_items`
  GROUP BY product_id
),
brand_perf AS (
  SELECT
    p.department,
    p.brand,
    MAX(pc_brand.brand_views) AS clickstream_views,
    COUNT(oi.id) AS items_ordered,
    ROUND(SAFE_DIVIDE(COUNTIF(oi.status = 'Returned') * 100.0, COUNT(oi.id)), 2) AS return_rate_pct,
    ROUND(SUM(IF(oi.status NOT IN ('Cancelled', 'Returned'), oi.sale_price, 0)), 2) AS net_revenue,
    ROUND(SUM(IF(oi.status NOT IN ('Cancelled', 'Returned'), oi.sale_price - p.cost, 0)), 2) AS gross_profit
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  LEFT JOIN (
    SELECT p2.department, p2.brand, SUM(COALESCE(pc.product_page_views, 0)) AS brand_views
    FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p2
    LEFT JOIN product_clicks AS pc ON p2.id = pc.product_id
    LEFT JOIN product_stock AS ps ON p2.id = ps.product_id
    GROUP BY p2.department, p2.brand
  ) AS pc_brand
    ON p.department = pc_brand.department AND p.brand = pc_brand.brand
  GROUP BY p.department, p.brand
  HAVING items_ordered >= 100
)
SELECT
  department,
  RANK() OVER (PARTITION BY department ORDER BY gross_profit DESC) AS profit_rank,
  brand,
  clickstream_views,
  items_ordered,
  net_revenue,
  gross_profit,
  ROUND(SAFE_DIVIDE(gross_profit * 100.0, net_revenue), 1) AS gross_margin_pct,
  return_rate_pct
FROM brand_perf
QUALIFY profit_rank <= 3
ORDER BY department, profit_rank;
```

#### Query 2: 5-Year Daily Rolling 14-Day Clickstream Stage Funnel
Evaluates **1,826 daily rolling 14-day regional funnels** across `2.42M+` clickstream events (`~119 concurrent slots`) to measure view-to-cart and cart-to-purchase velocity by channel.

```sql
-- Query 2: 5-Year Daily Rolling 14-Day Clickstream Stage Funnel
WITH daily_windows AS (
  SELECT report_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2021-07-01', '2026-06-30')) AS report_date
),
daily_stage_funnel AS (
  SELECT
    w.report_date,
    e.traffic_source,
    e.state,
    COUNT(*) AS events_14d,
    COUNTIF(e.event_type = 'product') AS product_views_14d,
    COUNTIF(e.event_type = 'cart') AS cart_adds_14d,
    COUNTIF(e.event_type = 'purchase') AS purchases_14d
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.events` AS e
  INNER JOIN daily_windows AS w
    ON DATE(e.created_at) BETWEEN DATE_SUB(w.report_date, INTERVAL 13 DAY) AND w.report_date
  GROUP BY w.report_date, e.traffic_source, e.state
),
daily_channel_totals AS (
  SELECT
    report_date,
    traffic_source,
    SUM(events_14d) AS events_14d,
    SUM(product_views_14d) AS product_views_14d,
    SUM(cart_adds_14d) AS cart_adds_14d,
    SUM(purchases_14d) AS purchases_14d
  FROM daily_stage_funnel
  GROUP BY report_date, traffic_source
)
SELECT
  traffic_source,
  MAX(IF(report_date = DATE '2026-06-30', events_14d, 0)) AS latest_14d_events,
  MAX(IF(report_date = DATE '2026-06-30', purchases_14d, 0)) AS latest_14d_purchases,
  ROUND(AVG(SAFE_DIVIDE(cart_adds_14d * 100.0, NULLIF(product_views_14d, 0))), 2) AS view_to_cart_pct,
  ROUND(AVG(SAFE_DIVIDE(purchases_14d * 100.0, NULLIF(cart_adds_14d, 0))), 2) AS cart_to_purchase_pct,
  ROUND(AVG(SAFE_DIVIDE(purchases_14d * 100.0, NULLIF(product_views_14d, 0))), 2) AS product_to_purchase_pct
FROM daily_channel_totals
GROUP BY traffic_source
ORDER BY latest_14d_purchases DESC;
```

#### Query 3: 6-Year Daily Inventory Capital-at-Risk & Rolling Turnover Ledger
Expands `490k+` physical inventory item lifecycles (`created_at` → `sold_at`) across **2,373 daily calendar snapshots (`~600M active SKU-days`)** with 30-day rolling window functions.

```sql
-- Query 3: 6-Year Daily Inventory Capital-at-Risk & Rolling Turnover Ledger
WITH calendar_spine AS (
  SELECT snapshot_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2020-01-01', '2026-06-30')) AS snapshot_date
),
daily_category_ledger AS (
  SELECT
    c.snapshot_date,
    ii.product_department AS department,
    ii.product_category AS category,
    COUNT(ii.id) AS units_on_shelf,
    SUM(ii.cost) AS capital_tied_up_usd,
    SUM(ii.product_retail_price - ii.cost) AS unrealized_margin_usd,
    AVG(DATE_DIFF(c.snapshot_date, DATE(ii.created_at), DAY)) AS avg_days_on_shelf,
    COUNTIF(DATE(ii.sold_at) = c.snapshot_date) AS units_sold_that_day
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.inventory_items` AS ii
  INNER JOIN calendar_spine AS c
    ON c.snapshot_date BETWEEN DATE(ii.created_at) AND COALESCE(DATE(ii.sold_at), DATE '2026-06-30')
  GROUP BY c.snapshot_date, department, category
),
rolling_metrics AS (
  SELECT
    department,
    category,
    snapshot_date,
    units_on_shelf,
    unrealized_margin_usd,
    avg_days_on_shelf,
    AVG(capital_tied_up_usd) OVER (
      PARTITION BY department, category
      ORDER BY snapshot_date
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30d_capital_usd,
    SUM(units_sold_that_day) OVER (
      PARTITION BY department, category
      ORDER BY snapshot_date
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30d_units_sold
  FROM daily_category_ledger
)
SELECT
  department,
  category,
  units_on_shelf AS current_unsold_units,
  ROUND(rolling_30d_capital_usd, 2) AS avg_30d_capital_tied_usd,
  ROUND(unrealized_margin_usd, 2) AS unrealized_margin_pool_usd,
  ROUND(avg_days_on_shelf, 1) AS avg_age_days,
  ROUND(SAFE_DIVIDE(rolling_30d_units_sold * 100.0, units_on_shelf), 2) AS monthly_sell_through_pct
FROM rolling_metrics
WHERE snapshot_date = DATE '2026-06-30'
ORDER BY avg_30d_capital_tied_usd DESC
LIMIT 10;
```

#### Query 4: 5-Year Daily Rolling 30-Day Clickstream Abandonment & Velocity Cube
Evaluates **1,826 daily rolling 30-day windows** across `2.42M+` raw clickstream events (`~140+ concurrent BigQuery slots`) to measure cart abandonment and conversion volatility by channel and browser.

```sql
-- Query 4: 5-Year Daily Rolling 30-Day Clickstream Abandonment & Velocity Cube
WITH daily_windows AS (
  SELECT report_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2021-07-01', '2026-06-30')) AS report_date
),
daily_rolling_funnel AS (
  SELECT
    w.report_date,
    e.traffic_source,
    e.browser,
    COUNT(*) AS rolling_30d_events,
    COUNTIF(e.event_type = 'product') AS rolling_30d_product_views,
    COUNTIF(e.event_type = 'cart') AS rolling_30d_cart_events,
    COUNTIF(e.event_type = 'purchase') AS rolling_30d_purchases
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.events` AS e
  INNER JOIN daily_windows AS w
    ON DATE(e.created_at) BETWEEN DATE_SUB(w.report_date, INTERVAL 29 DAY) AND w.report_date
  GROUP BY w.report_date, e.traffic_source, e.browser
)
SELECT
  traffic_source,
  browser,
  ROUND(AVG(rolling_30d_events), 0) AS avg_30d_event_volume,
  MAX(IF(report_date = DATE '2026-06-30', rolling_30d_events, 0)) AS latest_30d_events,
  ROUND(AVG(SAFE_DIVIDE(rolling_30d_cart_events - rolling_30d_purchases, NULLIF(rolling_30d_cart_events, 0)) * 100.0), 2) AS avg_cart_abandonment_pct,
  ROUND(STDDEV(SAFE_DIVIDE(rolling_30d_purchases * 100.0, NULLIF(rolling_30d_product_views, 0))), 3) AS conversion_volatility_pts
FROM daily_rolling_funnel
GROUP BY traffic_source, browser
ORDER BY latest_30d_events DESC
LIMIT 10;
```

#### Query 5: 6-Year Daily Rolling 90-Day Brand Profit & Return-Spike Stress Cube
Evaluates **2,191 daily rolling 90-day windows** across `order_items` ⋈ `products` to benchmark each brand's current 90-day profit against its all-time peak and worst historical return-rate surges.

```sql
-- Query 5: 6-Year Daily Rolling 90-Day Brand Profit & Return-Spike Stress Cube
WITH daily_snapshots AS (
  SELECT report_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2020-07-01', '2026-06-30')) AS report_date
),
order_enriched AS (
  SELECT
    DATE(oi.created_at) AS order_date,
    oi.status,
    oi.sale_price,
    p.department,
    p.brand,
    p.cost
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
),
rolling_brand_health AS (
  SELECT
    s.report_date,
    oe.department,
    oe.brand,
    COUNT(*) AS rolling_90d_units,
    SUM(IF(oe.status NOT IN ('Cancelled', 'Returned'), oe.sale_price - oe.cost, 0)) AS rolling_90d_gross_profit,
    SAFE_DIVIDE(COUNTIF(oe.status = 'Returned') * 100.0, COUNT(*)) AS rolling_90d_return_pct
  FROM order_enriched AS oe
  INNER JOIN daily_snapshots AS s
    ON oe.order_date BETWEEN DATE_SUB(s.report_date, INTERVAL 89 DAY) AND s.report_date
  GROUP BY s.report_date, oe.department, oe.brand
  HAVING rolling_90d_units >= 20
)
SELECT
  department,
  brand,
  ROUND(MAX(IF(report_date = DATE '2026-06-30', rolling_90d_gross_profit, 0)), 2) AS current_90d_profit_usd,
  ROUND(MAX(rolling_90d_gross_profit), 2) AS all_time_peak_90d_profit_usd,
  ROUND(AVG(rolling_90d_return_pct), 2) AS historical_avg_return_pct,
  ROUND(MAX(rolling_90d_return_pct), 2) AS worst_90d_return_spike_pct
FROM rolling_brand_health
GROUP BY department, brand
HAVING MAX(rolling_90d_units) >= 60
ORDER BY current_90d_profit_usd DESC
LIMIT 10;
```

---

### `GIS` — Elastic Geospatial Analytics (`Q6`–`Q8`)

#### Query 6: Geodesic Last-Mile Shipping Distance vs. Local Micro-Hub Proximity
Evaluates **16M+ spherical `ST_DISTANCE` pairs** across **1,200+ US micro-hub demand centroids** to compare actual warehouse shipping distances against local fulfillment benchmarks.

```sql
-- Query 6: Geodesic Last-Mile Shipping Distance vs. Local Micro-Hub Proximity
WITH metro_demand_nodes AS (
  SELECT
    CONCAT(city, ', ', state) AS metro_node,
    ST_CENTROID_AGG(ST_GEOGFROMTEXT(user_geom)) AS metro_geom
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users`
  WHERE country = 'United States' AND city IS NOT NULL
  GROUP BY city, state
  HAVING COUNT(*) >= 5
),
shipment_distances AS (
  SELECT
    oi.id AS order_item_id,
    dc.name AS distribution_center,
    ST_DISTANCE(ST_GEOGFROMTEXT(dc.distribution_center_geom), ST_GEOGFROMTEXT(u.user_geom)) / 1000.0 AS actual_distance_km,
    DATETIME_DIFF(oi.delivered_at, oi.shipped_at, HOUR) / 24.0 AS transit_days,
    MIN(ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), m.metro_geom) / 1000.0) AS nearest_local_hub_km
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS dc
    ON p.distribution_center_id = dc.id
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
    ON oi.user_id = u.id
  CROSS JOIN metro_demand_nodes AS m
  WHERE u.country = 'United States'
    AND oi.delivered_at IS NOT NULL
    AND oi.shipped_at IS NOT NULL
  GROUP BY oi.id, dc.name, dc.distribution_center_geom, u.user_geom, oi.delivered_at, oi.shipped_at
)
SELECT
  distribution_center,
  COUNT(*) AS domestic_shipments,
  ROUND(AVG(actual_distance_km), 1) AS avg_distance_km,
  ROUND(APPROX_QUANTILES(actual_distance_km, 100)[OFFSET(90)], 1) AS p90_distance_km,
  ROUND(AVG(nearest_local_hub_km), 1) AS avg_local_hub_km,
  ROUND(AVG(transit_days), 2) AS avg_transit_days,
  ROUND(COUNTIF(actual_distance_km > 1500) * 100.0 / COUNT(*), 1) AS pct_long_haul_gt_1500km
FROM shipment_distances
GROUP BY distribution_center
ORDER BY avg_distance_km DESC;
```

#### Query 7: Optimal Nearest-Warehouse & Micro-Hub Re-Routing Simulation
Simultaneously evaluates every US customer against all 10 existing warehouses and high-density city micro-hubs (`~109 concurrent slots`) to quantify reducible freight-kilometers per category.

```sql
-- Query 7: Optimal Nearest-Warehouse & Micro-Hub Re-Routing Simulation
WITH city_micro_hubs AS (
  SELECT
    CONCAT(city, ', ', state) AS hub_label,
    ST_CENTROID_AGG(ST_GEOGFROMTEXT(user_geom)) AS hub_geom,
    COUNT(*) AS city_buyers
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users`
  WHERE country = 'United States' AND city IS NOT NULL
  GROUP BY city, state
  HAVING city_buyers >= 15
),
nearest_hub_per_user AS (
  SELECT
    u.id AS user_id,
    MIN(ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), ST_GEOGFROMTEXT(dc.distribution_center_geom)) / 1000.0) AS nearest_dc_km,
    MIN(ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), mh.hub_geom) / 1000.0) AS nearest_microhub_km
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
  CROSS JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS dc
  CROSS JOIN city_micro_hubs AS mh
  WHERE u.country = 'United States'
  GROUP BY u.id
)
SELECT
  p.category,
  COUNT(oi.id) AS us_shipments,
  ROUND(AVG(ST_DISTANCE(ST_GEOGFROMTEXT(actual_dc.distribution_center_geom), ST_GEOGFROMTEXT(u.user_geom)) / 1000.0), 1) AS avg_actual_km,
  ROUND(AVG(nh.nearest_dc_km), 1) AS avg_nearest_dc_km,
  ROUND(AVG(nh.nearest_microhub_km), 1) AS avg_microhub_km,
  ROUND(SUM(
    GREATEST(0, (ST_DISTANCE(ST_GEOGFROMTEXT(actual_dc.distribution_center_geom), ST_GEOGFROMTEXT(u.user_geom)) / 1000.0) - nh.nearest_dc_km)
  ), 0) AS reducible_freight_km
FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
  ON oi.product_id = p.id
INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS actual_dc
  ON p.distribution_center_id = actual_dc.id
INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
  ON oi.user_id = u.id
INNER JOIN nearest_hub_per_user AS nh
  ON u.id = nh.user_id
WHERE u.country = 'United States'
GROUP BY p.category
ORDER BY reducible_freight_km DESC
LIMIT 8;
```

#### Query 8: Multi-Year Rolling 300 km Catchment Polygon, Convex Hull & Centroid
Computes **12,000+ daily geodesic convex hulls (`ST_CONVEXHULL`), polygon areas (`ST_AREA`), and centroids (`ST_CENTROID`)** across 3.5 years of rolling 180-day 300 km catchments.

```sql
-- Query 8: Multi-Year Rolling 300 km Catchment Polygon, Convex Hull & Centroid
WITH dated_customer_orders AS (
  SELECT
    DATE(oi.created_at) AS order_date,
    u.id AS user_id,
    ST_GEOGFROMTEXT(u.user_geom) AS user_pt,
    IF(oi.status NOT IN ('Cancelled', 'Returned'), oi.sale_price, 0) AS net_sale
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
    ON u.id = oi.user_id
  WHERE u.country = 'United States'
),
daily_snapshots AS (
  SELECT report_date
  FROM UNNEST(GENERATE_DATE_ARRAY('2023-01-01', '2026-06-30')) AS report_date
),
daily_catchment_polygons AS (
  SELECT
    s.report_date,
    dc.name AS distribution_center,
    COUNT(DISTINCT dco.user_id) AS active_180d_buyers,
    SUM(dco.net_sale) AS rolling_180d_revenue,
    ST_AREA(ST_CONVEXHULL(ST_UNION_AGG(dco.user_pt))) / 1e6 AS hull_sq_km,
    ST_CENTROID(ST_UNION_AGG(dco.user_pt)) AS centroid_pt
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS dc
  INNER JOIN dated_customer_orders AS dco
    ON ST_DWITHIN(ST_GEOGFROMTEXT(dc.distribution_center_geom), dco.user_pt, 300000)
  INNER JOIN daily_snapshots AS s
    ON dco.order_date BETWEEN DATE_SUB(s.report_date, INTERVAL 179 DAY) AND s.report_date
  GROUP BY s.report_date, dc.name
)
SELECT
  distribution_center,
  MAX(IF(report_date = DATE '2026-06-30', active_180d_buyers, 0)) AS current_180d_buyers_300km,
  ROUND(MAX(IF(report_date = DATE '2026-06-30', rolling_180d_revenue, 0)), 2) AS current_180d_catchment_rev,
  ROUND(AVG(hull_sq_km), 0) AS avg_catchment_hull_sq_km,
  ANY_VALUE(IF(report_date = DATE '2026-06-30', ST_ASTEXT(centroid_pt), NULL)) AS current_demand_centroid_wkt
FROM daily_catchment_polygons
GROUP BY distribution_center
ORDER BY current_180d_catchment_rev DESC;
```

---

### `AI.*` — In-Warehouse Foundation Models & Gemini (`Q9`–`Q13`)

#### Query 9: Zero-Shot Multi-Series Weekly Revenue Forecast (`AI.FORECAST` + `TimesFM 2.5`)
Forecasts 4 weeks of weekly revenue simultaneously across `Men` and `Women` (`id_cols => ['department']`) with zero `CREATE MODEL` training step.

```sql
-- Query 9: Zero-Shot Multi-Series Weekly Revenue Forecast (AI.FORECAST + TimesFM 2.5)
WITH weekly_dept_sales AS (
  SELECT
    DATE_TRUNC(DATE(oi.created_at), WEEK(MONDAY)) AS sales_week,
    p.department,
    SUM(oi.sale_price) AS weekly_revenue
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  WHERE oi.status NOT IN ('Cancelled', 'Returned')
    AND DATE(oi.created_at) BETWEEN '2024-01-01' AND '2026-06-28'
  GROUP BY sales_week, p.department
)
SELECT
  department,
  DATE(forecast_timestamp) AS forecast_week,
  ROUND(forecast_value, 2) AS predicted_revenue,
  ROUND(prediction_interval_lower_bound, 2) AS lower_bound_90,
  ROUND(prediction_interval_upper_bound, 2) AS upper_bound_90
FROM AI.FORECAST(
  TABLE weekly_dept_sales,
  data_col => 'weekly_revenue',
  timestamp_col => 'sales_week',
  id_cols => ['department'],
  horizon => 4,
  confidence_level => 0.90,
  model => 'TimesFM 2.5'
)
ORDER BY department, forecast_week;
```

#### Query 10: Automated Daily Order Spike Detection (`AI.DETECT_ANOMALIES` + `TimesFM 2.5`)
Evaluates the latest 60 days of daily order volume per department against 16 months of prior history to surface statistically significant volume surges.

```sql
-- Query 10: Automated Daily Order Spike Detection (AI.DETECT_ANOMALIES + TimesFM 2.5)
WITH daily_dept_orders AS (
  SELECT
    DATE(oi.created_at) AS order_date,
    p.department,
    COUNT(oi.id) AS daily_items
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  WHERE oi.status != 'Cancelled'
    AND DATE(oi.created_at) BETWEEN '2025-01-01' AND '2026-06-30'
  GROUP BY order_date, p.department
)
SELECT
  department,
  DATE(time_series_timestamp) AS order_date,
  CAST(time_series_data AS INT64) AS actual_items,
  ROUND(lower_bound, 1) AS expected_min,
  ROUND(upper_bound, 1) AS expected_max,
  ROUND(anomaly_probability, 4) AS anomaly_prob,
  is_anomaly
FROM AI.DETECT_ANOMALIES(
  (SELECT * FROM daily_dept_orders WHERE order_date < '2026-05-01'),
  (SELECT * FROM daily_dept_orders WHERE order_date >= '2026-05-01'),
  data_col => 'daily_items',
  timestamp_col => 'order_date',
  id_cols => ['department'],
  model => 'TimesFM 2.5',
  anomaly_prob_threshold => 0.80
)
ORDER BY anomaly_probability DESC
LIMIT 10;
```

#### Query 11: 6-Dimensional YoY Revenue Growth Root-Cause Analysis (`AI.KEY_DRIVERS`)
Enriches `order_items` with clickstream engagement tiers (`Power_Browser_25+`, `Active_Browser_10_24`) and warehouse hubs so `AI.KEY_DRIVERS` discovers multi-dimensional YoY revenue expansion drivers across trailing 6-month windows.

```sql
-- Query 11: 6-Dimensional YoY Revenue Growth Root-Cause Analysis (AI.KEY_DRIVERS)
WITH user_engagement AS (
  SELECT
    user_id,
    CASE
      WHEN COUNT(*) >= 25 THEN 'Power_Browser_25+'
      WHEN COUNT(*) >= 10 THEN 'Active_Browser_10_24'
      ELSE 'Light_Browser_<10'
    END AS browse_tier
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.events`
  WHERE user_id IS NOT NULL
  GROUP BY user_id
),
yoy_sales AS (
  SELECT
    oi.sale_price,
    p.department,
    p.category,
    dc.name AS fulfillment_hub,
    u.country,
    u.traffic_source,
    COALESCE(ue.browse_tier, 'Guest_Checkout') AS browse_tier,
    (DATE(oi.created_at) BETWEEN '2026-01-02' AND '2026-06-30') AS is_current_6m
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS dc
    ON p.distribution_center_id = dc.id
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
    ON oi.user_id = u.id
  LEFT JOIN user_engagement AS ue
    ON u.id = ue.user_id
  WHERE oi.status NOT IN ('Cancelled', 'Returned')
    AND (
      DATE(oi.created_at) BETWEEN '2025-01-02' AND '2025-06-30'
      OR DATE(oi.created_at) BETWEEN '2026-01-02' AND '2026-06-30'
    )
)
SELECT
  ARRAY_TO_STRING(drivers, ' | ') AS segment_driver,
  ROUND(metric_reference, 2) AS prior_6m_revenue,
  ROUND(metric_interest, 2) AS current_6m_revenue,
  ROUND(difference, 2) AS yoy_delta,
  ROUND(relative_difference * 100.0, 1) AS yoy_growth_pct,
  ROUND(apriori_support * 100.0, 1) AS population_share_pct
FROM AI.KEY_DRIVERS(
  TABLE yoy_sales,
  metric_col => 'sale_price',
  dimension_cols => ['department', 'category', 'fulfillment_hub', 'country', 'traffic_source', 'browse_tier'],
  interest_label_col => 'is_current_6m',
  top_k => 8
)
ORDER BY yoy_delta DESC;
```

#### Query 12: Zero-Shot Semantic Filtering & Campaign Persona Tagging (`AI.IF` + `AI.CLASSIFY`)
Combines `AI.IF` in the `WHERE` clause (semantic boolean filter on unstructured product titles) with `AI.CLASSIFY` in `SELECT` to assign top-revenue outerwear SKUs to targeted marketing personas.

```sql
-- Query 12: Zero-Shot Semantic Filtering & Campaign Persona Tagging (AI.IF + AI.CLASSIFY)
WITH top_outerwear AS (
  SELECT
    p.id AS product_id,
    p.brand,
    p.category,
    p.name AS product_name,
    ROUND(AVG(p.retail_price), 2) AS retail_price,
    ROUND(SUM(oi.sale_price), 2) AS realized_revenue
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  WHERE oi.status NOT IN ('Cancelled', 'Returned')
    AND p.category IN ('Outerwear & Coats', 'Active')
  GROUP BY p.id, p.brand, p.category, p.name
  ORDER BY realized_revenue DESC
  LIMIT 15
)
SELECT
  product_id,
  brand,
  product_name,
  retail_price,
  realized_revenue,
  AI.CLASSIFY(
    product_name,
    categories => [
      'Alpine & Heavy Winter',
      'Urban Tailored Coat',
      'Rain & Wind Shell',
      'Fleece & Mid-Layer'
    ]
  ) AS campaign_segment
FROM top_outerwear
WHERE AI.IF((product_name, 'Is this garment intended for cold weather, winter warmth, or rain/wind protection?'))
ORDER BY realized_revenue DESC;
```

#### Query 13: Unified SQL + Micro-Hub GIS + Structured GenAI Supply-Chain Brief (`AI.GENERATE`)
Unifies geodesic regional micro-hub simulation, 4-table fulfillment joins, and structured Gemini generation (`AI.GENERATE` with `output_schema`) in a single SQL query.

```sql
-- Query 13: Unified SQL + Micro-Hub GIS + Structured GenAI Supply-Chain Brief (AI.GENERATE)
WITH metro_nodes AS (
  SELECT
    ST_CENTROID_AGG(ST_GEOGFROMTEXT(user_geom)) AS metro_geom
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users`
  WHERE country = 'United States' AND city IS NOT NULL
  GROUP BY city, state
  HAVING COUNT(*) >= 10
),
user_hub_gap AS (
  SELECT
    u.id AS user_id,
    u.user_geom,
    MIN(ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), m.metro_geom) / 1000.0) AS nearest_metro_km
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
  CROSS JOIN metro_nodes AS m
  WHERE u.country = 'United States'
  GROUP BY u.id, u.user_geom
),
dc_telemetry AS (
  SELECT
    dc.name AS distribution_center,
    ROUND(SUM(IF(oi.status NOT IN ('Cancelled', 'Returned'), oi.sale_price, 0)), 0) AS net_revenue_usd,
    ROUND(COUNTIF(oi.status = 'Returned') * 100.0 / COUNT(oi.id), 2) AS return_rate_pct,
    ROUND(AVG(ST_DISTANCE(ST_GEOGFROMTEXT(dc.distribution_center_geom), ST_GEOGFROMTEXT(ug.user_geom)) / 1000.0), 0) AS avg_ship_km,
    ROUND(AVG(ug.nearest_metro_km), 0) AS potential_microhub_km,
    ROUND(AVG(
      IF(oi.delivered_at IS NOT NULL AND oi.shipped_at IS NOT NULL,
         DATETIME_DIFF(oi.delivered_at, oi.shipped_at, HOUR) / 24.0,
         NULL)
    ), 2) AS avg_transit_days
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.order_items` AS oi
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.products` AS p
    ON oi.product_id = p.id
  INNER JOIN `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.distribution_centers` AS dc
    ON p.distribution_center_id = dc.id
  INNER JOIN user_hub_gap AS ug
    ON oi.user_id = ug.user_id
  GROUP BY dc.name
)
SELECT
  distribution_center,
  net_revenue_usd,
  avg_ship_km,
  potential_microhub_km,
  return_rate_pct,
  ai_plan.priority_tier,
  ai_plan.bottleneck_diagnosis,
  ai_plan.recommended_action
FROM (
  SELECT
    *,
    AI.GENERATE(
      CONCAT(
        'Analyze this US e-commerce warehouse KPI summary and recommend one concrete supply-chain action. ',
        'Warehouse: ', distribution_center,
        ', Net Revenue: $', CAST(net_revenue_usd AS STRING),
        ', Avg Shipping Distance: ', CAST(avg_ship_km AS STRING), ' km (vs ', CAST(potential_microhub_km AS STRING), ' km via regional micro-hubs)',
        ', Avg Transit Days: ', CAST(avg_transit_days AS STRING),
        ', Return Rate: ', CAST(return_rate_pct AS STRING), '%.'
      ),
      output_schema => 'priority_tier STRING, bottleneck_diagnosis STRING, recommended_action STRING'
    ) AS ai_plan
  FROM dc_telemetry
)
ORDER BY avg_ship_km DESC;
```

---

### `Graph` — Native Property Graph (`ISO GQL`, `Q14`)

#### Query 14: 8-Hop Repeat-Buyer Category & Warehouse Transition Graph
Uses standalone ISO GQL (`GRAPH` + `MATCH p = (...)` + `PATH_LENGTH(p)` + implicit `RETURN` grouping) over `<PROJECT_ID>.thelook_commerce.ecommerce_graph` to traverse **9 nodes and 8 directed edges** across sequential customer orders (`Warehouse → Product → OrderItem → Order → User ← Order ← OrderItem ← Product ← Warehouse`).

```sql
-- Query 14: 8-Hop Repeat-Buyer Category & Warehouse Transition Graph (Native ISO GQL)
GRAPH `<PROJECT_ID>.thelook_commerce.ecommerce_graph`
MATCH p = (dc1:DistributionCenter)<-[:product_stocked_at]-(p1:Product)<-[:includes_product]-(oi1:OrderItem)
          -[:belongs_to_order]->(o1:`Order`)-[:placed_order]->(u:User)<-[:placed_order]-(o2:`Order`)
          <-[:belongs_to_order]-(oi2:OrderItem)-[:includes_product]->(p2:Product)-[:product_stocked_at]->(dc2:DistributionCenter)
WHERE o1.created_at < o2.created_at
  AND p1.category != p2.category
  AND o1.status != 'Cancelled'
  AND o2.status != 'Cancelled'
RETURN
  p1.category AS first_order_category,
  p2.category AS repeat_order_category,
  MAX(PATH_LENGTH(p)) AS graph_hops,
  COUNT(DISTINCT u.id) AS repeat_customers,
  COUNT(*) AS cross_order_transitions,
  COUNTIF(dc1.id != dc2.id) AS cross_hub_switches,
  ROUND(AVG(DATETIME_DIFF(o2.created_at, o1.created_at, DAY)), 1) AS avg_days_to_next_order,
  ROUND(SUM(oi2.sale_price), 2) AS downstream_repeat_revenue
ORDER BY cross_order_transitions DESC, downstream_repeat_revenue DESC
LIMIT 12;
```

---

### `All-in-One` — 4-Engine Convergence (`SQL` + `Graph` + `GIS` + `AI.*` in One Query, `Q15`)

#### Query 15: Multi-Modal Supply-Chain & CX Convergence Across All 7 Tables
Unifies all four engines and all 7 physical tables in a single statement:
1. **`GRAPH` (`GRAPH_TABLE`)**: Traverses 4-hop fulfillment paths `(User)<-[:placed_order]-(Order)<-[:belongs_to_order]-(OrderItem)-[:includes_product]->(Product)-[:product_stocked_at]->(DistributionCenter)`.
2. **`SQL` (Relational Joins + Analytical Windowing)**: Joins clickstream `events` and physical `inventory_items` (both outside the graph) plus `RANK() OVER (...)`.
3. **`GIS` (`ST_DISTANCE`, `ST_CENTROID_AGG`, `ST_CONVEXHULL`, `ST_AREA`)**: Computes spherical long-haul shipping distances, regional US micro-hub proximity per buyer, and corridor convex-hull area (`sq km`).
4. **`AI.*` (`AI.GENERATE` with `output_schema`)**: Synthesizes Graph + SQL + GIS signals into typed executive actions inline.

```sql
-- Query 15: 4-Engine Convergence — Property Graph + Relational SQL + Spatial GIS + Gemini AI.GENERATE
WITH graph_fulfillment_paths AS (
  SELECT
    user_id, user_state, user_geom, order_id, item_status, sale_price, unit_cost, category, hub_id, hub_name, hub_geom
  FROM GRAPH_TABLE(
    `<PROJECT_ID>.thelook_commerce.ecommerce_graph`
    MATCH (u:User WHERE u.country = 'United States')<-[:placed_order]-(o:`Order` WHERE o.status != 'Cancelled')
          <-[:belongs_to_order]-(oi:OrderItem)-[:includes_product]->(p:Product)
          -[:product_stocked_at]->(dc:DistributionCenter)
    COLUMNS (
      u.id AS user_id,
      u.state AS user_state,
      u.user_geom AS user_geom,
      o.order_id AS order_id,
      oi.status AS item_status,
      oi.sale_price AS sale_price,
      p.cost AS unit_cost,
      p.category AS category,
      dc.id AS hub_id,
      dc.name AS hub_name,
      dc.distribution_center_geom AS hub_geom
    )
  )
),
user_clickstream AS (
  SELECT
    user_id,
    COUNT(*) AS web_events,
    COUNTIF(event_type = 'cart') AS cart_adds,
    COUNTIF(event_type = 'purchase') AS web_purchases
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.events`
  WHERE user_id IS NOT NULL
  GROUP BY user_id
),
hub_unsold_stock AS (
  SELECT
    product_distribution_center_id AS hub_id,
    product_category AS category,
    ROUND(SUM(cost), 2) AS unsold_stock_usd
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.inventory_items`
  WHERE sold_at IS NULL
  GROUP BY hub_id, category
),
us_metro_nodes AS (
  SELECT
    CONCAT(city, ', ', state) AS metro_hub,
    ST_CENTROID_AGG(ST_GEOGFROMTEXT(user_geom)) AS metro_pt
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users`
  WHERE country = 'United States' AND city IS NOT NULL AND user_geom IS NOT NULL
  GROUP BY city, state
  HAVING COUNT(*) >= 12
),
buyer_nearest_microhub AS (
  SELECT
    u.id AS user_id,
    ARRAY_AGG(
      STRUCT(
        m.metro_hub,
        ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), m.metro_pt) / 1000.0 AS microhub_km
      )
      ORDER BY ST_DISTANCE(ST_GEOGFROMTEXT(u.user_geom), m.metro_pt) ASC
      LIMIT 1
    )[OFFSET(0)] AS best_local
  FROM `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.users` AS u
  CROSS JOIN us_metro_nodes AS m
  WHERE u.country = 'United States' AND u.user_geom IS NOT NULL
  GROUP BY u.id
),
corridor_convergence AS (
  SELECT
    g.hub_name AS origin_hub,
    g.user_state AS dest_state,
    g.category,
    COUNT(*) AS graph_shipped_items,
    ROUND(SUM(g.sale_price - g.unit_cost), 2) AS gross_margin_usd,
    ROUND(100.0 * COUNTIF(g.item_status = 'Returned') / COUNT(*), 2) AS return_rate_pct,
    ROUND(AVG(cs.web_events), 1) AS avg_buyer_clicks,
    COALESCE(MAX(inv.unsold_stock_usd), 0.0) AS hub_unsold_capital_usd,
    ROUND(AVG(ST_DISTANCE(ST_GEOGFROMTEXT(g.user_geom), ST_GEOGFROMTEXT(g.hub_geom)) / 1000.0), 0) AS avg_haul_km,
    ROUND(AVG(bm.best_local.microhub_km), 0) AS avg_microhub_km,
    APPROX_TOP_COUNT(bm.best_local.metro_hub, 1)[OFFSET(0)].value AS top_forward_microhub,
    ROUND(ST_AREA(ST_CONVEXHULL(ST_UNION_AGG(ST_GEOGFROMTEXT(g.user_geom)))) / 1e6, 0) AS demand_hull_sq_km,
    RANK() OVER (
      ORDER BY SUM(g.sale_price - g.unit_cost) * (1.0 + COUNTIF(g.item_status = 'Returned') / COUNT(*)) DESC
    ) AS corridor_rank
  FROM graph_fulfillment_paths AS g
  LEFT JOIN user_clickstream AS cs
    ON g.user_id = cs.user_id
  LEFT JOIN hub_unsold_stock AS inv
    ON g.hub_id = inv.hub_id AND g.category = inv.category
  INNER JOIN buyer_nearest_microhub AS bm
    ON g.user_id = bm.user_id
  WHERE g.user_geom IS NOT NULL AND g.hub_geom IS NOT NULL
  GROUP BY g.hub_name, g.user_state, g.category
  HAVING graph_shipped_items >= 25 AND avg_haul_km >= 1800
  QUALIFY corridor_rank <= 6
)
SELECT
  origin_hub,
  dest_state,
  category,
  graph_shipped_items,
  gross_margin_usd,
  return_rate_pct,
  avg_buyer_clicks,
  hub_unsold_capital_usd,
  avg_haul_km,
  avg_microhub_km,
  top_forward_microhub,
  demand_hull_sq_km,
  ai_plan.priority_tier,
  ai_plan.corridor_diagnosis,
  ai_plan.forward_hub_plan,
  ai_plan.cx_retention_play
FROM (
  SELECT
    *,
    AI.GENERATE(
      CONCAT(
        'Synthesize a concise supply-chain & CX action plan (under 22 words per field; priority_tier must be P0, P1, or P2). ',
        'Graph Corridor: ', origin_hub, ' -> ', dest_state, ' (', category, ', ', CAST(graph_shipped_items AS STRING), ' items, $', CAST(gross_margin_usd AS STRING), ' margin, ', CAST(return_rate_pct AS STRING), '% returns). ',
        'SQL Signals: ', CAST(avg_buyer_clicks AS STRING), ' avg web clicks/buyer, $', CAST(hub_unsold_capital_usd AS STRING), ' unsold category stock at origin hub. ',
        'GIS Signals: ', CAST(avg_haul_km AS STRING), ' km actual haul vs ', CAST(avg_microhub_km AS STRING), ' km via forward hub ', top_forward_microhub, ' across ', CAST(demand_hull_sq_km AS STRING), ' sq km hull.'
      ),
      output_schema => 'priority_tier STRING, corridor_diagnosis STRING, forward_hub_plan STRING, cx_retention_play STRING'
    ) AS ai_plan
  FROM corridor_convergence
)
ORDER BY corridor_rank ASC;
```

---

## Part 2 — Agent: Native *Talk to Data / Talk to Graph* (`ecommerce_graph`)

> **Presenter Talk Track (Before Revealing Amazon S3)**:
> *"Writing SQL, GIS, `AI.*`, and 8-hop ISO GQL in a notebook is powerful for data teams — but what about a merchandising VP or supply-chain lead who just wants to ask multi-hop questions in plain English without worrying about 5-table join paths or fanout double-counting? Let's open `thelook_commerce.ecommerce_graph` right inside BigQuery Studio and click **Chat**."*

### How to Launch Live in BigQuery Studio
1. Click the **Open `ecommerce_graph` in BigQuery Studio → Click "Chat" → "Create Agent"** button in **Cell 5** of [`notebooks/thelook_analytics_ai_demo.ipynb`](../notebooks/thelook_analytics_ai_demo.ipynb) *(or in the BigQuery Studio Explorer pane, expand `<PROJECT_ID>` → `thelook_commerce` → `Property graphs` → `ecommerce_graph`)*.
2. Click **`Chat`** → **`Create Agent`** in the top Property Graph action bar to open **Conversational Analytics** scoped directly to `ecommerce_graph`.
3. Ask 1–2 of the natural-language questions below:
   - **Prompt 1 (Semantic Measures & Hub Rollup)**:
     ```text
     Which top 5 distribution centers generate the highest total revenue and order count across non-cancelled, non-returned items, and what are their top product categories?
     ```
   - **Prompt 2 (Multi-Hop Acquisition Channel Economics)**:
     ```text
     Compare total revenue, total cost, and user count by customer traffic_source across the Men and Women departments.
     ```
   - **Prompt 3 (Cross-Hub Regional Corridor Demand)**:
     ```text
     Which US customer states order the highest item_count of products stocked in the Chicago IL and Los Angeles CA distribution centers?
     ```
   - **Prompt 4 (5-Entity Relationship Exploration)**:
     ```text
     Trace how top-spending users in California connect through orders and order items to products and the distribution centers that stock them.
     ```

### Why This Works Out of the Box (Semantic `MEASURE`s + `GRAPH_EXPAND` / `GQL`)
- [`scripts/04_create_bq_graph.sh`](../scripts/04_create_bq_graph.sh) defines `thelook_commerce.ecommerce_graph` directly over `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.*` as a clean directed semantic tree rooted at `OrderItem` (`OrderItem → Order → User` and `OrderItem → Product → DistributionCenter`) with rich `OPTIONS(description=...)` on every property and **6 grain-locked `MEASURE(...)` declarations** (`total_revenue`, `item_count`, `order_count`, `user_count`, `total_cost`, `product_count`).
- On **standard On-Demand projects**, the Graph Chat agent automatically generates grain-safe `GRAPH_EXPAND` + `AGG(...)` queries so traversing `OrderItem → Order → User` or `OrderItem → Product` never inflates `order_count`, `user_count`, or `total_cost`. On **Enterprise reservations**, it can also emit native `GQL` path queries (`MATCH p = ... RETURN TO_JSON(p)`) with interactive node-link graph rendering.

---

## Part 3 — The Twist (`0 Bytes` in BigQuery + Cross-Cloud Waterfall)

> **Presenter Talk Track**:
> *"We just ran 15 parallel queries — 2.4M-row clickstream cubes, geodesic convex hulls, zero-shot `TimesFM 2.5` forecasting and anomaly detection, `AI.KEY_DRIVERS`, 8-hop ISO GQL Property Graph traversals, a single query combining SQL + Graph + GIS + Gemini `AI.GENERATE` across all 7 tables — AND we just chatted with our 5-entity commerce graph in plain English. Now let's check how much data is physically stored inside BigQuery, and where the tables in `thelook_catalog` actually live."*

### Reveal Query A: Zero-Copy Storage & Object Definitions (`0 Bytes` Stored in BigQuery)

Cell 6 of [`notebooks/thelook_analytics_ai_demo.ipynb`](../notebooks/thelook_analytics_ai_demo.ipynb) executes the SQL check below (`0` tables stored in BigQuery — only zero-copy `ecommerce_graph`) **and** queries Knowledge Catalog (`system=BIGLAKE` + `:lookupEntry?view=ALL`) to display the live `AWS_GLUE` + `ICEBERG` + `s3://<S3_BUCKET>/iceberg/<table>` origins of `<PROJECT_ID>.thelook_catalog.thelook_ecommerce.*`:

```sql
-- Reveal Query A: Zero-Copy Storage Check on thelook_commerce (0 Tables Stored in BigQuery, ecommerce_graph Only)
SELECT
  t.table_id AS object_name,
  CASE t.type WHEN 1 THEN 'BASE TABLE' ELSE 'OTHER' END AS object_type,
  t.size_bytes AS bytes_stored_in_bigquery,
  'BigQuery table' AS definition_summary
FROM `<PROJECT_ID>.thelook_commerce.__TABLES__` AS t
UNION ALL
SELECT
  g.property_graph_name AS object_name,
  'PROPERTY GRAPH' AS object_type,
  0 AS bytes_stored_in_bigquery,
  CONCAT(
    REGEXP_EXTRACT(g.ddl, r'(CREATE PROPERTY GRAPH [^\n]+)'),
    ' -> ',
    REGEXP_EXTRACT(g.ddl, r'NODE TABLES \(\n([^\n]+)')
  ) AS definition_summary
FROM `<PROJECT_ID>.thelook_commerce.INFORMATION_SCHEMA.PROPERTY_GRAPHS` AS g
ORDER BY object_type DESC, object_name;
```

### Reveal Query B: 4-Stage Cross-Cloud Byte-Reduction Waterfall (`JOBS_BY_PROJECT`)
Audits `INFORMATION_SCHEMA.JOBS_BY_PROJECT` and `UNNEST(object_storage_stats)` to break down the exact 4-stage data reduction pipeline across all 15 parallel queries:
1. **Logical Data Scanned (`logical_scan_mb`)** — Column-pruned uncompressed scan vs. full referenced table size
2. **Compressed Data Read (`compressed_mb` & `compression_ratio`)** — Columnar Snappy Parquet compression (`~3x` average, up to `~5x` on columnar event scans)
3. **Intelligent Cache Hit (`cache_hit_mb` & `cache_hit_pct`)** — Regional Lakehouse block cache (`0%` on cold run → `~100%` on warm run, shared across distinct SQL/GIS/AI/Graph queries reading overlapping Parquet column blocks)
4. **Sent Over the Wire (`sent_over_wire_mb` from `remote_cloud = 'AWS'`)** — Exact cross-cloud network transfer (`~117 MB` cold → **`0.00 MB` warm**)

```sql
-- Reveal Query B: Live BigQuery Engine Telemetry & 4-Stage Cross-Cloud Data Reduction Audit
WITH target_batch AS (
  SELECT (
    SELECT MAX((SELECT l.value FROM UNNEST(j2.labels) AS l WHERE l.key = 'demo_batch'))
    FROM `<PROJECT_ID>.region-us-east4.INFORMATION_SCHEMA.JOBS_BY_PROJECT` AS j2
    WHERE j2.creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)
  ) AS batch_id
),
table_logical_catalog AS (
  SELECT 'events' AS table_id, 384678804 AS full_logical_bytes UNION ALL
  SELECT 'inventory_items', 80897145 UNION ALL
  SELECT 'users', 19820850 UNION ALL
  SELECT 'order_items', 13569337 UNION ALL
  SELECT 'orders', 6728888 UNION ALL
  SELECT 'products', 4285975 UNION ALL
  SELECT 'distribution_centers', 809
),
job_metrics AS (
  SELECT
    UPPER(COALESCE((SELECT l.value FROM UNNEST(labels) AS l WHERE l.key = 'query_num'), 'query')) AS query_num,
    REGEXP_EXTRACT(query, r'-- Query \d+: ([^\n]+)') AS query_title,
    creation_time,
    ROUND(TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000.0, 2) AS elapsed_sec,
    ROUND(total_slot_ms / 1000.0, 1) AS slot_sec,
    ROUND(total_slot_ms / NULLIF(TIMESTAMP_DIFF(end_time, start_time, MILLISECOND), 0), 1) AS avg_slots,
    COALESCE((
      SELECT SUM(tlc.full_logical_bytes)
      FROM (SELECT DISTINCT rt.table_id FROM UNNEST(referenced_tables) AS rt) AS d
      LEFT JOIN table_logical_catalog AS tlc USING (table_id)
    ), 0) AS table_logical_bytes,
    COALESCE(total_bytes_processed, 0) AS raw_logical_scan_bytes,
    COALESCE((SELECT SUM(COALESCE(s.cache_bytes_read, 0)) FROM UNNEST(object_storage_stats) AS s), 0) AS cache_bytes,
    COALESCE((SELECT SUM(COALESCE(s.object_storage_bytes_read, 0)) FROM UNNEST(object_storage_stats) AS s), 0) AS wire_bytes,
    COALESCE((SELECT STRING_AGG(DISTINCT s.cloud_provider, ', ') FROM UNNEST(object_storage_stats) AS s), 'LOCAL') AS remote_cloud,
    ARRAY_TO_STRING(
      ARRAY(
        SELECT DISTINCT CONCAT(rt.dataset_id, '.', rt.table_id)
        FROM UNNEST(referenced_tables) AS rt
        ORDER BY 1
      ),
      ', '
    ) AS actual_physical_tables_read
  FROM `<PROJECT_ID>.region-us-east4.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
  CROSS JOIN target_batch AS tb
  WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)
    AND statement_type = 'SELECT'
    AND IF(
      tb.batch_id IS NOT NULL,
      EXISTS (SELECT 1 FROM UNNEST(labels) AS l WHERE l.key = 'demo_batch' AND l.value = tb.batch_id),
      (query LIKE '%<PROJECT_ID>.thelook_catalog.%' OR query LIKE '%<PROJECT_ID>.thelook_commerce.%')
        AND query NOT LIKE '%INFORMATION_SCHEMA%'
        AND query NOT LIKE '%__TABLES__%'
    )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY query_num, query_title ORDER BY creation_time DESC) = 1
),
enriched AS (
  SELECT
    *,
    (cache_bytes + wire_bytes) AS compressed_bytes,
    COALESCE(
      NULLIF(raw_logical_scan_bytes, 0),
      CAST(
        ROUND(
          (cache_bytes + wire_bytes) * COALESCE(
            SAFE_DIVIDE(
              SUM(IF(raw_logical_scan_bytes > 0, raw_logical_scan_bytes, 0)) OVER (),
              NULLIF(SUM(IF(raw_logical_scan_bytes > 0, cache_bytes + wire_bytes, 0)) OVER (), 0)
            ),
            1.0
          )
        ) AS INT64
      )
    ) AS logical_scan_bytes
  FROM job_metrics
)
SELECT
  query_num,
  query_title,
  elapsed_sec,
  slot_sec,
  avg_slots,
  ROUND(table_logical_bytes / 1048576.0, 2) AS table_logical_mb,
  ROUND(logical_scan_bytes / 1048576.0, 2) AS logical_scan_mb,
  ROUND(compressed_bytes / 1048576.0, 2) AS compressed_mb,
  FORMAT('%.2fx', COALESCE(SAFE_DIVIDE(logical_scan_bytes, NULLIF(compressed_bytes, 0)), 1.0)) AS compression_ratio,
  ROUND(cache_bytes / 1048576.0, 2) AS cache_hit_mb,
  ROUND(100.0 * SAFE_DIVIDE(cache_bytes, NULLIF(compressed_bytes, 0)), 1) AS cache_hit_pct,
  ROUND(wire_bytes / 1048576.0, 2) AS sent_over_wire_mb,
  remote_cloud,
  actual_physical_tables_read
FROM enriched
ORDER BY CAST(REGEXP_EXTRACT(query_num, r'\d+') AS INT64), creation_time DESC
LIMIT 20;
```

---

## Part 4 — Knowledge Catalog: Zero-Touch Storage-Agnostic Discovery & Agentic Context

> **Presenter Talk Track (After the Amazon S3 Twist)**:
> *"Once customers see that BigQuery and our Graph Agent ran directly over Apache Iceberg on Amazon S3 with zero copies, the very next architectural question is: **'How do we discover schemas and feed trusted context to AI agents when our physical tables live in S3 + AWS Glue while semantic Property Graphs live in BigQuery?'** That is where **Knowledge Catalog** closes the loop automatically."*

### What Knowledge Catalog Indexes Out of the Box
1. **Storage-Agnostic Auto-Discovery (`@biglake` + `@bigquery`)**:
   - Without moving data or running custom catalog scripts, Knowledge Catalog automatically indexes the federated **AWS Glue + Amazon S3 Apache Iceberg** catalog (`thelook_catalog`), namespace (`thelook_ecommerce`), and all 7 Iceberg tables under `@biglake` (capturing `s3://.../iceberg/<table>` URIs, `ICEBERG` format, `AWS_GLUE` catalog origin, and Iceberg schemas) alongside the `thelook_commerce` dataset and `ecommerce_graph` Property Graph under `@bigquery` (including graph node/edge topology, property `OPTIONS(description=...)`, and `MEASURE` metadata).
2. **Live Agentic Context Synthesis (`:lookupContext`)**:
   - Step 7 of [`notebooks/thelook_analytics_ai_demo.ipynb`](../notebooks/thelook_analytics_ai_demo.ipynb) calls Knowledge Catalog's `:lookupContext` endpoint across both a federated `@biglake` S3 Iceberg table and `@bigquery` `ecommerce_graph`, rendering the exact pre-formatted **YAML context payload** consumed by LLM agents and MCP tools.

### Console Walkthrough & Useful Search Filters
Open [**Knowledge Catalog Search**](https://console.cloud.google.com/dataplex/search) in the Google Cloud Console (or click the buttons rendered in **Step 7** of the notebook) and demonstrate these storage-agnostic searches:

- **Federated Amazon S3 + AWS Glue Apache Iceberg Tables Only**:
  ```text
  system=BIGLAKE
  ```
- **Native ISO GQL Property Graph Entry (Inspect Nodes, Edges & Measures)**:
  ```text
  type=bigquery-graph ecommerce_graph
  ```
