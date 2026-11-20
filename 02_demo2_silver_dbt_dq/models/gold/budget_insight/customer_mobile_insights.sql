{{ config(
    materialized='table',
    cluster_by=['customer_id', 'region_code'],
) }}

-- dp_budget_insight · customer_mobile_insights :
-- Table maîtresse GOLD synchronisée vers AlloyDB (< 15 ms) pour les 3 agents mobiles ADK
-- (Budget Insight, Conseil Offres, Action) — exactement 1 ligne par client (80 000).
--   * Prévision du reste à vivre fin de mois = revenus projetés - charges fixes projetées
--     - GREATEST(dépenses carte réalisées MTD, prévision TimesFM 2.5).
--   * Signaux "Depuis votre dernière connexion" : hausse d'abonnement récurrent, remboursement santé,
--     fuites néobanques M-2 / M-1 et dépenses temps réel post-batch.
--   * Recommandation d'épargne 100 % gouvernée par silver_bank.savings_offers & budget_insight_rules
--     (ACPR 2024-R-01 : coussin >= 100 EUR, max 70 % du surplus, priorité Livret A / LDDS puis Livret Boost Maison 3,50 %).
WITH rules AS (
    SELECT *
    FROM {{ ref('budget_insight_rules') }}
    LIMIT 1
),
batch_cutoff AS (
    SELECT
        MAX(period_month)                                                       AS current_month,
        MAX(closing_balance_date)                                               AS batch_cutoff_date,
        DATE_SUB(MAX(period_month), INTERVAL 1 MONTH)                           AS prev_complete_month
    FROM {{ ref('account_monthly_balances') }}
    WHERE is_partial_month
),
acpr_policy AS (
    SELECT
        MAX(acpr_max_surplus_share_pct)                                         AS acpr_max_surplus_share_pct
    FROM {{ ref('savings_offers') }}
    WHERE is_acpr_compliant
),
boosted_offer AS (
    SELECT
        o.offer_code,
        o.product_label,
        o.headline_rate_bps,
        o.base_rate_bps,
        o.boost_duration_months
    FROM {{ ref('savings_offers') }} AS o
    JOIN rules AS r
        ON o.offer_code = r.boosted_offer_code
    WHERE o.is_acpr_compliant
    LIMIT 1
),
customer_accounts AS (
    SELECT
        customer_id,
        MAX(IF(is_current_account, account_id, NULL))                           AS current_account_id,
        MAX(IF(is_current_account, balance_d1_eur, NULL))                       AS current_account_balance_d1_eur,
        ROUND(SUM(IF(NOT is_current_account, COALESCE(balance_d1_eur, CAST(0 AS NUMERIC)), CAST(0 AS NUMERIC))), 2) AS total_savings_balance_d1_eur,
        COUNTIF(NOT is_current_account)                                         AS savings_accounts_count
    FROM {{ ref('accounts') }}
    GROUP BY customer_id
),
customer_offer_headroom AS (
    -- Évalue pour chaque client la marge disponible sur chaque offre réglementée (priority_rank = 1)
    SELECT
        c.customer_id,
        o.offer_code,
        o.product_label,
        o.headline_rate_bps,
        o.priority_rank,
        o.deposit_cap_eur,
        a.account_id IS NOT NULL                                                AS already_holds_account,
        COALESCE(a.balance_d1_eur, CAST(0 AS NUMERIC))                          AS current_offer_balance_eur,
        CASE
            WHEN o.deposit_cap_eur IS NULL THEN CAST(999999999 AS NUMERIC)
            ELSE GREATEST(CAST(0 AS NUMERIC), o.deposit_cap_eur - COALESCE(a.balance_d1_eur, CAST(0 AS NUMERIC)))
        END                                                                     AS remaining_headroom_eur
    FROM {{ ref('customers') }} AS c
    CROSS JOIN {{ ref('savings_offers') }} AS o
    CROSS JOIN rules AS r
    LEFT JOIN {{ ref('accounts') }} AS a
        ON a.customer_id = c.customer_id
       AND a.account_type = o.account_type
    WHERE o.is_acpr_compliant
      AND o.is_regulated
      AND o.priority_rank = r.regulated_priority_rank
),
best_regulated_offer AS (
    SELECT
        customer_id,
        offer_code                                                              AS best_regulated_offer_code,
        product_label                                                           AS best_regulated_offer_label,
        headline_rate_bps                                                       AS best_regulated_rate_bps,
        remaining_headroom_eur                                                  AS best_regulated_headroom_eur
    FROM customer_offer_headroom
    WHERE remaining_headroom_eur > 0
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY deposit_cap_eur DESC, offer_code ASC
    ) = 1
),
mtd_flows AS (
    SELECT
        t.customer_id,
        ROUND(SUM(IF(t.is_income, t.amount_eur, CAST(0 AS NUMERIC))), 2)        AS mtd_income_eur,
        ROUND(SUM(IF(t.is_fixed_charge, t.amount_eur, CAST(0 AS NUMERIC))), 2)  AS mtd_fixed_charges_eur,
        ROUND(SUM(IF(t.is_variable_card, t.amount_eur, CAST(0 AS NUMERIC))), 2) AS mtd_card_spending_eur,
        ROUND(SUM(IF(t.is_health_refund, t.amount_eur, CAST(0 AS NUMERIC))), 2) AS recent_health_refund_eur,
        ROUND(SUM(IF(t.is_post_batch_realtime AND t.direction = 'DEBIT', t.amount_eur, CAST(0 AS NUMERIC))), 2) AS realtime_post_batch_spend_eur,
        COUNTIF(t.is_post_batch_realtime)                                       AS realtime_post_batch_tx_count
    FROM {{ ref('customer_transactions_enriched') }} AS t
    WHERE t.is_current_month
    GROUP BY t.customer_id
),
neobank_m2_m1 AS (
    SELECT
        t.customer_id,
        ROUND(SUM(t.signed_amount_eur), 2)                                      AS neobank_outflow_m2_m1_eur,
        COUNT(*)                                                                AS neobank_transfers_m2_m1_count,
        ARRAY_AGG(t.neobank_institution_name IGNORE NULLS ORDER BY t.amount_eur DESC, t.booking_date DESC LIMIT 1)[SAFE_OFFSET(0)]
            AS primary_neobank_name
    FROM {{ ref('customer_transactions_enriched') }} AS t
    CROSS JOIN batch_cutoff AS bc
    CROSS JOIN rules AS r
    WHERE t.is_neobank_outflow
      AND t.booking_month BETWEEN DATE_SUB(bc.current_month, INTERVAL r.neobank_lookback_months MONTH)
                              AND bc.prev_complete_month
    GROUP BY t.customer_id
),
recurring_summary AS (
    SELECT
        customer_id,
        ROUND(SUM(IF(is_income, expected_amount_this_month_eur, CAST(0 AS NUMERIC))), 2)        AS recurring_monthly_income_eur,
        ROUND(SUM(IF(is_income, expected_remaining_eur, CAST(0 AS NUMERIC))), 2)                AS expected_remaining_income_eur,
        ROUND(SUM(IF(is_fixed_charge, expected_remaining_eur, CAST(0 AS NUMERIC))), 2)          AS expected_remaining_fixed_charges_eur,
        COUNTIF(is_fixed_charge AND commitment_status = 'EXPECTED_BEFORE_EOM')                  AS remaining_fixed_charges_count,
        COUNTIF(is_price_hike)                                                                  AS subscription_hikes_count
    FROM {{ ref('customer_recurring_commitments') }}
    GROUP BY customer_id
),
top_subscription_hike AS (
    SELECT
        customer_id,
        merchant_name                                                           AS detected_subscription_hike_merchant,
        prev_month_amount_eur                                                   AS subscription_prev_amount_eur,
        current_month_amount_eur                                                AS subscription_new_amount_eur,
        amount_delta_vs_prev_month_eur                                          AS subscription_hike_delta_eur
    FROM {{ ref('customer_recurring_commitments') }}
    WHERE is_price_hike
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY amount_delta_vs_prev_month_eur DESC, category ASC
    ) = 1
),
assembled AS (
    SELECT
        c.customer_id,
        c.first_name,
        c.last_name,
        c.age,
        c.age_segment,
        c.segment,
        c.city,
        c.region_code,
        c.region_name,
        c.agency_code,
        c.digital_opt_in,
        bc.current_month                                                        AS reference_month,
        bc.batch_cutoff_date,
        ca.current_account_id,
        ca.current_account_balance_d1_eur,
        COALESCE(ca.total_savings_balance_d1_eur, CAST(0 AS NUMERIC))           AS total_savings_balance_d1_eur,
        COALESCE(ca.savings_accounts_count, 0)                                  AS savings_accounts_count,
        COALESCE(rs.recurring_monthly_income_eur, mf.mtd_income_eur, CAST(0 AS NUMERIC)) AS monthly_salary_eur,
        COALESCE(mf.mtd_income_eur, CAST(0 AS NUMERIC))                         AS mtd_income_eur,
        COALESCE(rs.expected_remaining_income_eur, CAST(0 AS NUMERIC))          AS expected_remaining_income_eur,
        COALESCE(mf.mtd_fixed_charges_eur, CAST(0 AS NUMERIC))                  AS mtd_fixed_charges_eur,
        COALESCE(rs.expected_remaining_fixed_charges_eur, CAST(0 AS NUMERIC))   AS expected_remaining_fixed_charges_eur,
        COALESCE(rs.remaining_fixed_charges_count, 0)                           AS remaining_fixed_charges_count,
        COALESCE(mf.mtd_card_spending_eur, CAST(0 AS NUMERIC))                  AS mtd_card_spending_eur,
        COALESCE(mf.realtime_post_batch_spend_eur, CAST(0 AS NUMERIC))          AS realtime_post_batch_spend_eur,
        COALESCE(mf.realtime_post_batch_tx_count, 0)                            AS realtime_post_batch_tx_count,
        fc.forecast_card_spending_eur,
        fc.forecast_ci_low_eur                                                  AS forecast_card_ci_low_eur,
        fc.forecast_ci_high_eur                                                 AS forecast_card_ci_high_eur,
        fc.forecast_method,
        GREATEST(
            CAST(0 AS NUMERIC),
            fc.forecast_card_spending_eur - COALESCE(mf.mtd_card_spending_eur, CAST(0 AS NUMERIC))
        )                                                                       AS expected_remaining_card_spending_eur,
        ROUND(
            (COALESCE(mf.mtd_income_eur, CAST(0 AS NUMERIC)) + COALESCE(rs.expected_remaining_income_eur, CAST(0 AS NUMERIC)))
            - (COALESCE(mf.mtd_fixed_charges_eur, CAST(0 AS NUMERIC)) + COALESCE(rs.expected_remaining_fixed_charges_eur, CAST(0 AS NUMERIC)))
            - GREATEST(COALESCE(mf.mtd_card_spending_eur, CAST(0 AS NUMERIC)), fc.forecast_card_spending_eur),
            2
        )                                                                       AS predicted_end_of_month_surplus_eur,
        COALESCE(nb.neobank_outflow_m2_m1_eur, CAST(0 AS NUMERIC))              AS neobank_outflow_m2_m1_eur,
        COALESCE(nb.neobank_transfers_m2_m1_count, 0)                           AS neobank_transfers_m2_m1_count,
        nb.primary_neobank_name,
        sh.detected_subscription_hike_merchant,
        sh.subscription_prev_amount_eur,
        sh.subscription_new_amount_eur,
        COALESCE(sh.subscription_hike_delta_eur, CAST(0 AS NUMERIC))            AS subscription_hike_delta_eur,
        COALESCE(mf.recent_health_refund_eur, CAST(0 AS NUMERIC))               AS recent_health_refund_eur,
        r.min_safety_cushion_eur                                                AS minimum_safety_cushion_eur,
        r.savings_rounding_step_eur,
        ap.acpr_max_surplus_share_pct,
        bro.best_regulated_offer_code,
        bro.best_regulated_offer_label,
        bro.best_regulated_rate_bps,
        bo.offer_code                                                           AS boosted_offer_code,
        bo.product_label                                                        AS boosted_offer_label,
        bo.headline_rate_bps                                                    AS boosted_offer_rate_bps,
        bo.boost_duration_months                                                AS boosted_offer_duration_months
    FROM {{ ref('customers') }} AS c
    CROSS JOIN batch_cutoff AS bc
    CROSS JOIN rules AS r
    CROSS JOIN acpr_policy AS ap
    CROSS JOIN boosted_offer AS bo
    LEFT JOIN customer_accounts AS ca
        ON ca.customer_id = c.customer_id
    LEFT JOIN best_regulated_offer AS bro
        ON bro.customer_id = c.customer_id
    LEFT JOIN mtd_flows AS mf
        ON mf.customer_id = c.customer_id
    LEFT JOIN neobank_m2_m1 AS nb
        ON nb.customer_id = c.customer_id
    LEFT JOIN recurring_summary AS rs
        ON rs.customer_id = c.customer_id
    LEFT JOIN top_subscription_hike AS sh
        ON sh.customer_id = c.customer_id
    JOIN {{ ref('customer_card_spending_forecast') }} AS fc
        ON fc.customer_id = c.customer_id
),
scored AS (
    SELECT
        a.*,
        CASE
            WHEN a.predicted_end_of_month_surplus_eur >= a.minimum_safety_cushion_eur THEN
                CAST(
                    GREATEST(
                        0.0,
                        LEAST(
                            FLOOR(
                                (CAST(a.predicted_end_of_month_surplus_eur AS FLOAT64) * (CAST(a.acpr_max_surplus_share_pct AS FLOAT64) / 100.0))
                                / CAST(a.savings_rounding_step_eur AS FLOAT64)
                            ) * CAST(a.savings_rounding_step_eur AS FLOAT64),
                            FLOOR(
                                CAST(a.predicted_end_of_month_surplus_eur - a.minimum_safety_cushion_eur AS FLOAT64)
                                / CAST(a.savings_rounding_step_eur AS FLOAT64)
                            ) * CAST(a.savings_rounding_step_eur AS FLOAT64)
                        )
                    ) AS NUMERIC
                )
            ELSE CAST(0 AS NUMERIC)
        END                                                                     AS recommended_savings_amount_eur
    FROM assembled AS a
)
SELECT
    customer_id,
    first_name,
    last_name,
    age,
    age_segment,
    segment,
    city,
    region_code,
    region_name,
    agency_code,
    digital_opt_in,
    reference_month,
    batch_cutoff_date,
    current_account_id,
    current_account_balance_d1_eur,
    total_savings_balance_d1_eur,
    savings_accounts_count,
    monthly_salary_eur,
    mtd_income_eur,
    expected_remaining_income_eur,
    mtd_fixed_charges_eur,
    expected_remaining_fixed_charges_eur,
    remaining_fixed_charges_count,
    mtd_card_spending_eur,
    realtime_post_batch_spend_eur,
    realtime_post_batch_tx_count,
    forecast_card_spending_eur,
    forecast_card_ci_low_eur,
    forecast_card_ci_high_eur,
    forecast_method,
    expected_remaining_card_spending_eur,
    predicted_end_of_month_surplus_eur,
    neobank_outflow_m2_m1_eur,
    neobank_transfers_m2_m1_count,
    primary_neobank_name,
    detected_subscription_hike_merchant,
    subscription_prev_amount_eur,
    subscription_new_amount_eur,
    subscription_hike_delta_eur,
    recent_health_refund_eur,
    minimum_safety_cushion_eur,
    acpr_max_surplus_share_pct,
    (
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur
        AND recommended_savings_amount_eur > 0
    )                                                                           AS is_eligible_for_proactive_savings,
    recommended_savings_amount_eur,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        COALESCE(best_regulated_offer_code, boosted_offer_code),
        CAST(NULL AS STRING)
    )                                                                           AS primary_recommended_offer_code,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        COALESCE(best_regulated_offer_label, boosted_offer_label),
        CAST(NULL AS STRING)
    )                                                                           AS primary_recommended_offer_label,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        COALESCE(best_regulated_rate_bps, boosted_offer_rate_bps),
        CAST(NULL AS INT64)
    )                                                                           AS primary_recommended_rate_bps,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        boosted_offer_code,
        CAST(NULL AS STRING)
    )                                                                           AS boosted_alternative_offer_code,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        boosted_offer_label,
        CAST(NULL AS STRING)
    )                                                                           AS boosted_alternative_offer_label,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        boosted_offer_rate_bps,
        CAST(NULL AS INT64)
    )                                                                           AS boosted_alternative_rate_bps,
    IF(
        predicted_end_of_month_surplus_eur >= minimum_safety_cushion_eur AND recommended_savings_amount_eur > 0,
        FORMAT(
            'Épargne conseillée : %.0f EUR (coussin %.0f EUR préservé) · Priorité réglementée : %s (%.2f %%) · Alternative mobile : %s (%.2f %% sur %d mois)',
            CAST(recommended_savings_amount_eur AS FLOAT64),
            CAST(minimum_safety_cushion_eur AS FLOAT64),
            COALESCE(best_regulated_offer_label, boosted_offer_label),
            CAST(COALESCE(best_regulated_rate_bps, boosted_offer_rate_bps) AS FLOAT64) / 100.0,
            boosted_offer_label,
            CAST(boosted_offer_rate_bps AS FLOAT64) / 100.0,
            boosted_offer_duration_months
        ),
        CAST(NULL AS STRING)
    )                                                                           AS recommended_mobile_action
FROM scored
