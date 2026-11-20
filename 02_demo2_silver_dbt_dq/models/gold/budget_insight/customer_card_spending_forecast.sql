{{ config(
    materialized='table',
    cluster_by=['customer_id', 'forecast_method'],
) }}

{% set timesfm_shards = 16 %}

-- dp_budget_insight · customer_card_spending_forecast :
-- Prévision zéro-shot des dépenses carte mensuelles pour le mois en cours par client (80 000 lignes)
-- via BigQuery AI.FORECAST (TimesFM 2.5, horizon = 1 mois, intervalle de confiance 80 %).
--   * Parallélisation en {{ timesfm_shards }} shards de hachage (FARM_FINGERPRINT) pour distribuer l'inférence
--     TimesFM sur {{ timesfm_shards }} workers BigQuery en parallèle (< 1 min au lieu de > 15 min sur 1 worker).
--   * Séries mensuelles denses (0 EUR sur les mois sans dépense carte entre le 1er mois actif et M-1).
--   * Clients avec >= min_timesfm_history_months (3) mois complets -> TimesFM 2.5 (borne inférieure >= 0).
--   * Clients récents (1-2 mois complets) -> moyenne mensuelle historique (HISTORICAL_AVG).
--   * Clients tout nouveaux ou sans historique complet (0 mois) -> 0 EUR (NEW_OR_INACTIVE).
WITH rules AS (
    SELECT min_timesfm_history_months
    FROM {{ ref('budget_insight_rules') }}
    LIMIT 1
),
batch_cutoff AS (
    SELECT
        MAX(period_month)                               AS current_month,
        DATE_SUB(MAX(period_month), INTERVAL 1 MONTH)   AS prev_complete_month,
        DATE_SUB(MAX(period_month), INTERVAL 3 MONTH)   AS lookback_3m_start
    FROM {{ ref('account_monthly_balances') }}
    WHERE is_partial_month
),
hist_tx AS (
    SELECT
        t.customer_id,
        t.booking_month                                 AS period_month,
        ROUND(SUM(IF(t.is_variable_card, t.amount_eur, CAST(0 AS NUMERIC))), 2) AS card_spending_eur
    FROM {{ ref('customer_transactions_enriched') }} AS t
    CROSS JOIN batch_cutoff AS bc
    WHERE t.booking_month < bc.current_month
    GROUP BY t.customer_id, t.booking_month
),
cust_span AS (
    SELECT
        h.customer_id,
        MOD(ABS(FARM_FINGERPRINT(h.customer_id)), {{ timesfm_shards }})         AS shard_id,
        MIN(h.period_month)                                                     AS first_active_month,
        DATE_DIFF(bc.prev_complete_month, MIN(h.period_month), MONTH) + 1       AS history_months_count,
        ROUND(
            AVG(IF(h.period_month BETWEEN bc.lookback_3m_start AND bc.prev_complete_month, h.card_spending_eur, NULL)),
            2
        )                                                                       AS avg_3m_card_spending_eur,
        ROUND(AVG(h.card_spending_eur), 2)                                      AS avg_all_card_spending_eur
    FROM hist_tx AS h
    CROSS JOIN batch_cutoff AS bc
    GROUP BY h.customer_id, bc.prev_complete_month, bc.lookback_3m_start
),
dense_series AS (
    SELECT
        s.customer_id,
        s.shard_id,
        TIMESTAMP(m)                                                            AS ts,
        CAST(COALESCE(h.card_spending_eur, CAST(0 AS NUMERIC)) AS FLOAT64)      AS card_spending_eur
    FROM cust_span AS s
    CROSS JOIN batch_cutoff AS bc
    CROSS JOIN rules AS r
    CROSS JOIN UNNEST(GENERATE_DATE_ARRAY(s.first_active_month, bc.prev_complete_month, INTERVAL 1 MONTH)) AS m
    LEFT JOIN hist_tx AS h
        ON h.customer_id = s.customer_id
       AND h.period_month = m
    WHERE s.history_months_count >= r.min_timesfm_history_months
),
timesfm_raw AS (
    {% for shard in range(timesfm_shards) %}
    SELECT
        customer_id,
        DATE(forecast_timestamp)                        AS forecast_month,
        forecast_value,
        prediction_interval_lower_bound,
        prediction_interval_upper_bound,
        ai_forecast_status
    FROM AI.FORECAST(
        (SELECT customer_id, ts, card_spending_eur FROM dense_series WHERE shard_id = {{ shard }}),
        data_col => 'card_spending_eur',
        timestamp_col => 'ts',
        id_cols => ['customer_id'],
        horizon => 1,
        model => 'TimesFM 2.5',
        confidence_level => 0.8
    )
    {% if not loop.last %}UNION ALL{% endif %}
    {% endfor %}
)
SELECT
    c.customer_id,
    bc.current_month                                                            AS forecast_month,
    COALESCE(s.history_months_count, 0)                                         AS history_months_count,
    COALESCE(s.avg_3m_card_spending_eur, CAST(0 AS NUMERIC))                    AS avg_3m_card_spending_eur,
    CASE
        WHEN tf.forecast_value IS NOT NULL THEN
            CAST(ROUND(GREATEST(0.0, tf.forecast_value), 2) AS NUMERIC)
        WHEN COALESCE(s.history_months_count, 0) > 0 THEN
            COALESCE(s.avg_3m_card_spending_eur, s.avg_all_card_spending_eur, CAST(0 AS NUMERIC))
        ELSE
            CAST(0 AS NUMERIC)
    END                                                                         AS forecast_card_spending_eur,
    CASE
        WHEN tf.prediction_interval_lower_bound IS NOT NULL THEN
            CAST(ROUND(GREATEST(0.0, tf.prediction_interval_lower_bound), 2) AS NUMERIC)
        ELSE CAST(NULL AS NUMERIC)
    END                                                                         AS forecast_ci_low_eur,
    CASE
        WHEN tf.prediction_interval_upper_bound IS NOT NULL THEN
            CAST(ROUND(GREATEST(0.0, tf.prediction_interval_upper_bound), 2) AS NUMERIC)
        ELSE CAST(NULL AS NUMERIC)
    END                                                                         AS forecast_ci_high_eur,
    CASE
        WHEN tf.forecast_value IS NOT NULL THEN 'TIMESFM_2_5'
        WHEN COALESCE(s.history_months_count, 0) > 0 THEN 'HISTORICAL_AVG'
        ELSE 'NEW_OR_INACTIVE'
    END                                                                         AS forecast_method,
    NULLIF(TRIM(COALESCE(tf.ai_forecast_status, '')), '')                       AS ai_forecast_status
FROM {{ ref('customers') }} AS c
CROSS JOIN batch_cutoff AS bc
LEFT JOIN cust_span AS s
    ON s.customer_id = c.customer_id
LEFT JOIN timesfm_raw AS tf
    ON tf.customer_id = c.customer_id
