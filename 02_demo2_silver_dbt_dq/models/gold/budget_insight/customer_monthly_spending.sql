{{ config(
    materialized='table',
    partition_by={'field': 'period_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['customer_id', 'category_group'],
) }}

-- dp_budget_insight · customer_monthly_spending :
-- Agrégat mensuel client x mois x catégorie x sens pour les réponses conversationnelles < 15 ms
-- ("Combien j'ai dépensé en courses ce mois-ci vs le mois dernier ?", "Quelle est ma plus grosse catégorie ?").
WITH batch_cutoff AS (
    SELECT MAX(period_month) AS current_month
    FROM {{ ref('account_monthly_balances') }}
    WHERE is_partial_month
),
monthly_agg AS (
    SELECT
        customer_id,
        booking_month                                   AS period_month,
        category_group,
        ANY_VALUE(category_group_label_fr)              AS category_group_label_fr,
        category,
        ANY_VALUE(category_label_fr)                    AS category_label_fr,
        ANY_VALUE(cashflow_role)                        AS cashflow_role,
        ANY_VALUE(is_organic_budget_flow)               AS is_organic_budget_flow,
        direction,
        COUNT(*)                                        AS transaction_count,
        ROUND(SUM(amount_eur), 2)                       AS total_amount_eur,
        ROUND(SUM(signed_amount_eur), 2)                AS signed_total_eur,
        COUNTIF(is_neobank_outflow)                     AS neobank_transaction_count,
        ROUND(SUM(IF(is_neobank_outflow, amount_eur, 0)), 2) AS neobank_outflow_eur
    FROM {{ ref('customer_transactions_enriched') }}
    GROUP BY customer_id, booking_month, category_group, category, direction
),
customer_first_month AS (
    SELECT
        customer_id,
        MIN(period_month) AS first_active_month
    FROM monthly_agg
    GROUP BY customer_id
),
with_prev_and_windows AS (
    SELECT
        cur.customer_id,
        cur.period_month,
        cur.category_group,
        cur.category_group_label_fr,
        cur.category,
        cur.category_label_fr,
        cur.cashflow_role,
        cur.is_organic_budget_flow,
        cur.direction,
        cur.transaction_count,
        cur.total_amount_eur,
        cur.signed_total_eur,
        cur.neobank_transaction_count,
        cur.neobank_outflow_eur,
        IF(
            cur.period_month > fm.first_active_month,
            COALESCE(prev.total_amount_eur, CAST(0 AS NUMERIC)),
            CAST(NULL AS NUMERIC)
        )                                                                       AS prev_month_amount_eur,
        ROUND(
            AVG(cur.total_amount_eur) OVER (
                PARTITION BY cur.customer_id, cur.category, cur.direction
                ORDER BY (EXTRACT(YEAR FROM cur.period_month) * 12 + EXTRACT(MONTH FROM cur.period_month))
                RANGE BETWEEN 3 PRECEDING AND 1 PRECEDING
            ),
            2
        )                                                                       AS avg_3m_amount_eur,
        SUM(IF(cur.direction = 'DEBIT' AND cur.is_organic_budget_flow, cur.total_amount_eur, CAST(0 AS NUMERIC))) OVER (
            PARTITION BY cur.customer_id, cur.period_month
        )                                                                       AS month_total_organic_outflows_eur
    FROM monthly_agg AS cur
    JOIN customer_first_month AS fm
        ON fm.customer_id = cur.customer_id
    LEFT JOIN monthly_agg AS prev
        ON prev.customer_id = cur.customer_id
       AND prev.category = cur.category
       AND prev.direction = cur.direction
       AND prev.period_month = DATE_SUB(cur.period_month, INTERVAL 1 MONTH)
)
SELECT
    w.customer_id,
    w.period_month,
    w.category_group,
    w.category_group_label_fr,
    w.category,
    w.category_label_fr,
    w.cashflow_role,
    w.direction,
    w.transaction_count,
    w.total_amount_eur,
    w.signed_total_eur,
    w.prev_month_amount_eur,
    ROUND(w.total_amount_eur - w.prev_month_amount_eur, 2)                      AS mom_delta_eur,
    ROUND(
        SAFE_DIVIDE(
            CAST(w.total_amount_eur - w.prev_month_amount_eur AS FLOAT64),
            CAST(NULLIF(w.prev_month_amount_eur, 0) AS FLOAT64)
        ) * 100.0,
        1
    )                                                                           AS mom_delta_pct,
    w.avg_3m_amount_eur,
    IF(
        w.direction = 'DEBIT' AND w.is_organic_budget_flow,
        ROUND(
            SAFE_DIVIDE(
                CAST(w.total_amount_eur AS FLOAT64),
                CAST(NULLIF(w.month_total_organic_outflows_eur, 0) AS FLOAT64)
            ) * 100.0,
            1
        ),
        CAST(NULL AS FLOAT64)
    )                                                                           AS share_of_month_outflows_pct,
    w.neobank_transaction_count,
    w.neobank_outflow_eur,
    w.period_month = bc.current_month                                           AS is_partial_month
FROM with_prev_and_windows AS w
CROSS JOIN batch_cutoff AS bc
