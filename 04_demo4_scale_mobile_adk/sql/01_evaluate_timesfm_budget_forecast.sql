-- ==============================================================================
-- Démo #4 — Backtesting chronologique TimesFM 2.5 (AI.EVALUATE) sur holdout M-1
-- Conforme aux bonnes pratiques bigquery-ai-ml :
--   * Découpage chronologique strict : historique [2025-06 .. 2026-09] vs réel [2026-10]
--   * Évaluation native via AI.EVALUATE (MAE, RMSE, sMAPE) sur un échantillon stratifié (5 %)
--     + focus dédié sur le client témoin CUST00002026 (Lucas Martin).
-- ==============================================================================
WITH hist_tx AS (
  SELECT
    customer_id,
    booking_month AS period_month,
    ROUND(SUM(IF(is_variable_card, amount_eur, CAST(0 AS NUMERIC))), 2) AS card_spending_eur
  FROM `data-days-demo.gold_bank.customer_transactions_enriched`
  WHERE booking_month <= DATE '2026-10-01'
  GROUP BY 1, 2
),
eligible_sample AS (
  SELECT
    customer_id,
    MIN(period_month) AS first_month
  FROM hist_tx
  WHERE period_month < DATE '2026-10-01'
  GROUP BY 1
  HAVING DATE_DIFF(DATE '2026-09-01', MIN(period_month), MONTH) + 1 >= 3
     AND (customer_id = 'CUST00002026' OR MOD(ABS(FARM_FINGERPRINT(customer_id)), 20) = 0)
),
dense_all AS (
  SELECT
    e.customer_id,
    m AS period_month,
    TIMESTAMP(m) AS ts,
    CAST(COALESCE(h.card_spending_eur, CAST(0 AS NUMERIC)) AS FLOAT64) AS card_spending_eur
  FROM eligible_sample AS e
  CROSS JOIN UNNEST(GENERATE_DATE_ARRAY(e.first_month, DATE '2026-10-01', INTERVAL 1 MONTH)) AS m
  LEFT JOIN hist_tx AS h
    ON h.customer_id = e.customer_id
   AND h.period_month = m
),
eval_metrics AS (
  SELECT *
  FROM AI.EVALUATE(
    (SELECT customer_id, ts, card_spending_eur FROM dense_all WHERE period_month < DATE '2026-10-01'),
    (SELECT customer_id, ts, card_spending_eur FROM dense_all WHERE period_month = DATE '2026-10-01'),
    data_col => 'card_spending_eur',
    timestamp_col => 'ts',
    id_cols => ['customer_id'],
    horizon => 1,
    model => 'TimesFM 2.5'
  )
)
SELECT
  IF(customer_id = 'CUST00002026', 'WITNESS_LUCAS_MARTIN', 'PORTFOLIO_5PCT_SAMPLE') AS cohort,
  COUNT(*) AS evaluated_customers,
  ROUND(AVG(mean_absolute_error), 2) AS avg_mae_eur,
  ROUND(APPROX_QUANTILES(mean_absolute_error, 4)[OFFSET(2)], 2) AS median_mae_eur,
  ROUND(AVG(root_mean_squared_error), 2) AS avg_rmse_eur,
  ROUND(AVG(symmetric_mean_absolute_percentage_error), 2) AS avg_smape_pct
FROM eval_metrics
GROUP BY 1
ORDER BY 1;
