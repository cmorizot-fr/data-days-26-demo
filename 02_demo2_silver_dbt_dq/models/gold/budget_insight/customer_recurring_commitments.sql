{{ config(
    materialized='table',
    cluster_by=['customer_id', 'commitment_status'],
) }}

-- dp_budget_insight · customer_recurring_commitments :
-- Engagements et revenus récurrents détectés par client (1 ligne par client x catégorie récurrente).
-- Alimente :
--   1. L'agent conversationnel ("Quels sont mes abonnements ?", "Qu'est-ce qui a augmenté ?",
--      "Quels prélèvements restent à passer avant la fin du mois ?").
--   2. La composante déterministe (revenus + charges fixes à venir) du reste à vivre fin de mois.
WITH rules AS (
    SELECT
        subscription_hike_min_delta_eur,
        min_recurring_months
    FROM {{ ref('budget_insight_rules') }}
    LIMIT 1
),
batch_cutoff AS (
    SELECT
        MAX(period_month)                                                       AS current_month,
        EXTRACT(MONTH FROM MAX(period_month))                                   AS current_month_num,
        DATE_SUB(MAX(period_month), INTERVAL 1 MONTH)                           AS prev_complete_month,
        DATE_SUB(MAX(period_month), INTERVAL 3 MONTH)                           AS lookback_3m_start,
        DATE_SUB(MAX(period_month), INTERVAL 12 MONTH)                          AS same_month_last_year
    FROM {{ ref('account_monthly_balances') }}
    WHERE is_partial_month
),
recurring_tx AS (
    SELECT
        t.customer_id,
        t.category,
        t.category_label_fr,
        t.category_group,
        t.category_group_label_fr,
        t.direction,
        t.is_income,
        t.is_fixed_charge,
        t.is_subscription,
        mc.active_months_max,
        t.merchant_name,
        t.booking_month,
        t.booking_date,
        t.day_of_month,
        t.amount_eur
    FROM {{ ref('customer_transactions_enriched') }} AS t
    JOIN {{ ref('movement_categories') }} AS mc
        ON mc.category = t.category
    WHERE t.is_recurring_candidate
),
monthly_by_cat AS (
    SELECT
        customer_id,
        category,
        ANY_VALUE(category_label_fr)                                            AS category_label_fr,
        ANY_VALUE(category_group)                                               AS category_group,
        ANY_VALUE(category_group_label_fr)                                      AS category_group_label_fr,
        ANY_VALUE(direction)                                                    AS direction,
        ANY_VALUE(is_income)                                                    AS is_income,
        ANY_VALUE(is_fixed_charge)                                              AS is_fixed_charge,
        ANY_VALUE(is_subscription)                                              AS is_subscription,
        ANY_VALUE(active_months_max)                                            AS active_months_max,
        ARRAY_AGG(merchant_name ORDER BY booking_date DESC LIMIT 1)[OFFSET(0)]  AS merchant_name,
        booking_month,
        MIN(booking_date)                                                       AS booking_date,
        CAST(ROUND(AVG(day_of_month)) AS INT64)                                 AS day_of_month,
        ROUND(SUM(amount_eur), 2)                                               AS month_amount_eur
    FROM recurring_tx
    GROUP BY customer_id, category, booking_month
),
per_stream AS (
    SELECT
        m.customer_id,
        m.category,
        ANY_VALUE(m.category_label_fr)                                          AS category_label_fr,
        ANY_VALUE(m.category_group)                                             AS category_group,
        ANY_VALUE(m.category_group_label_fr)                                    AS category_group_label_fr,
        ANY_VALUE(m.direction)                                                  AS direction,
        ANY_VALUE(m.is_income)                                                  AS is_income,
        ANY_VALUE(m.is_fixed_charge)                                            AS is_fixed_charge,
        ANY_VALUE(m.is_subscription)                                            AS is_subscription,
        ANY_VALUE(m.active_months_max)                                          AS active_months_max,
        ARRAY_AGG(m.merchant_name ORDER BY m.booking_month DESC LIMIT 1)[OFFSET(0)] AS merchant_name,
        COUNTIF(m.booking_month < bc.current_month)                             AS total_hist_months,
        COUNTIF(m.booking_month BETWEEN bc.lookback_3m_start AND bc.prev_complete_month) AS recent_3m_months,
        CAST(ROUND(AVG(IF(m.booking_month < bc.current_month, m.day_of_month, NULL))) AS INT64) AS usual_day_of_month,
        MAX(IF(m.booking_month = bc.prev_complete_month, m.month_amount_eur, NULL)) AS prev_month_amount_eur,
        ROUND(
            AVG(IF(m.booking_month BETWEEN bc.lookback_3m_start AND bc.prev_complete_month, m.month_amount_eur, NULL)),
            2
        )                                                                       AS avg_3m_amount_eur,
        MAX(IF(m.booking_month = bc.same_month_last_year, m.month_amount_eur, NULL)) AS same_month_last_year_amount_eur,
        MAX(IF(m.booking_month = bc.current_month, m.month_amount_eur, NULL))   AS current_month_amount_eur,
        MAX(IF(m.booking_month = bc.current_month, m.booking_date, NULL))       AS current_month_booking_date
    FROM monthly_by_cat AS m
    CROSS JOIN batch_cutoff AS bc
    GROUP BY m.customer_id, m.category
),
qualified AS (
    SELECT
        s.*,
        bc.current_month,
        bc.current_month_num,
        r.subscription_hike_min_delta_eur,
        COALESCE(
            s.current_month_amount_eur,
            s.same_month_last_year_amount_eur,
            s.prev_month_amount_eur,
            s.avg_3m_amount_eur
        )                                                                       AS expected_amount_this_month_eur
    FROM per_stream AS s
    CROSS JOIN batch_cutoff AS bc
    CROSS JOIN rules AS r
    WHERE s.recent_3m_months >= r.min_recurring_months
       OR (s.current_month_amount_eur IS NOT NULL AND s.recent_3m_months >= 1)
)
SELECT
    customer_id,
    category,
    category_label_fr,
    category_group,
    category_group_label_fr,
    direction,
    is_income,
    is_fixed_charge,
    is_subscription,
    merchant_name,
    current_month                                                               AS reference_month,
    total_hist_months,
    recent_3m_months,
    COALESCE(usual_day_of_month, EXTRACT(DAY FROM current_month_booking_date))  AS usual_day_of_month,
    prev_month_amount_eur,
    avg_3m_amount_eur,
    current_month_amount_eur,
    current_month_booking_date,
    ROUND(current_month_amount_eur - prev_month_amount_eur, 2)                  AS amount_delta_vs_prev_month_eur,
    (
        is_subscription
        AND current_month_amount_eur IS NOT NULL
        AND prev_month_amount_eur IS NOT NULL
        AND (current_month_amount_eur - prev_month_amount_eur) >= subscription_hike_min_delta_eur
    )                                                                           AS is_price_hike,
    IF(
        current_month_num <= active_months_max,
        ROUND(expected_amount_this_month_eur, 2),
        CAST(0 AS NUMERIC)
    )                                                                           AS expected_amount_this_month_eur,
    CASE
        WHEN current_month_amount_eur IS NOT NULL AND is_income THEN 'RECEIVED_THIS_MONTH'
        WHEN current_month_amount_eur IS NOT NULL THEN 'PAID_THIS_MONTH'
        WHEN current_month_num > active_months_max THEN 'NOT_EXPECTED_THIS_MONTH'
        ELSE 'EXPECTED_BEFORE_EOM'
    END                                                                         AS commitment_status,
    CASE
        WHEN current_month_amount_eur IS NOT NULL THEN CAST(0 AS NUMERIC)
        WHEN current_month_num > active_months_max THEN CAST(0 AS NUMERIC)
        ELSE ROUND(expected_amount_this_month_eur, 2)
    END                                                                         AS expected_remaining_eur
FROM qualified
