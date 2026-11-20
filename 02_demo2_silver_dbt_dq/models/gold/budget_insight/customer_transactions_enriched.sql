{{ config(
    materialized='table',
    partition_by={'field': 'booking_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['customer_id', 'category_group'],
) }}

-- dp_budget_insight · customer_transactions_enriched :
-- Grand livre de transactions prêt pour l'agent conversationnel mobile et AlloyDB (< 15 ms).
-- Corrections & enrichissements par rapport à silver_bank.customer_movements :
--   1. Résolution d'un merchant_name toujours renseigné (0 NULL, y compris sur les 1,95 M d'opérations carte
--      et les virements néobanques résolus via competitor_institutions).
--   2. Libellés métier français et rôles budgétaires issus du référentiel versionné movement_categories.
--   3. Normalisation booléenne stricte de is_neobank_outflow (COALESCE FALSE sur les lignes carte Mainframe).
--   4. Exclusion des données sensibles IBAN (counterparty_iban omis de la couche analytique mobile).
WITH batch_cutoff AS (
    SELECT
        MAX(period_month)           AS current_month,
        MAX(closing_balance_date)   AS batch_cutoff_date
    FROM {{ ref('account_monthly_balances') }}
    WHERE is_partial_month
),
competitors AS (
    SELECT
        bic,
        institution_name,
        institution_type
    FROM {{ ref('competitor_institutions') }}
    WHERE bic IS NOT NULL
),
categories AS (
    SELECT
        category,
        category_label_fr,
        category_group_label_fr,
        cashflow_role,
        is_income,
        is_fixed_charge,
        is_variable_card,
        is_recurring_candidate,
        is_subscription,
        is_health_refund,
        is_organic_budget_flow,
        active_months_max
    FROM {{ ref('movement_categories') }}
)
SELECT
    m.movement_id,
    m.customer_id,
    m.account_id,
    m.account_type,
    m.source_system,
    m.booking_date,
    DATE_TRUNC(m.booking_date, MONTH)                                           AS booking_month,
    EXTRACT(DAY FROM m.booking_date)                                            AS day_of_month,
    DATE_TRUNC(m.booking_date, MONTH) = bc.current_month                        AS is_current_month,
    m.booking_date > bc.batch_cutoff_date                                       AS is_post_batch_realtime,
    m.direction,
    m.amount_eur,
    m.signed_amount_eur,
    m.category_group,
    mc.category_group_label_fr,
    m.category,
    mc.category_label_fr,
    mc.cashflow_role,
    mc.is_income,
    mc.is_fixed_charge,
    mc.is_variable_card,
    mc.is_recurring_candidate,
    mc.is_subscription,
    mc.is_health_refund,
    mc.is_organic_budget_flow,
    {{ resolve_merchant_name(
        'IF(COALESCE(m.is_neobank_outflow, FALSE), comp.institution_name, NULL)',
        'm.counterparty_name',
        'm.label',
        'm.is_internal_transfer',
        'mc.category_label_fr'
    ) }}                                                                        AS merchant_name,
    m.label                                                                     AS raw_label,
    m.payment_scheme,
    COALESCE(m.is_neobank_outflow, FALSE)                                       AS is_neobank_outflow,
    IF(COALESCE(m.is_neobank_outflow, FALSE), comp.institution_name, NULL)      AS neobank_institution_name,
    IF(COALESCE(m.is_neobank_outflow, FALSE), comp.institution_type, NULL)      AS neobank_institution_type,
    m.is_internal_transfer
FROM {{ ref('customer_movements') }} AS m
JOIN categories AS mc
    ON mc.category = m.category
LEFT JOIN competitors AS comp
    ON comp.bic = m.counterparty_bic
CROSS JOIN batch_cutoff AS bc
