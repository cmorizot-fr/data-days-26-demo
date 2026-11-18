{{ config(
    materialized='table',
    partition_by={'field': 'period_month', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['customer_id', 'account_id'],
) }}

-- dp_customer_360 · account_monthly_balances : 1 ligne par compte et par mois (18 mois CFONB).
-- Ouverture (ligne 01) et clôture (ligne 07) côte à côte, rapprochées des mouvements Mainframe du mois.
-- Profiling : 0 rupture entre la clôture d'un mois et l'ouverture du suivant ; ouverture + mouvements = clôture sur 100 % des lignes.
WITH balances AS (
    SELECT
        account_number_11,
        period_month,
        MAX(IF(record_type = '01', signed_balance_eur, NULL))   AS opening_balance_eur,
        MAX(IF(record_type = '07', signed_balance_eur, NULL))   AS closing_balance_eur,
        MAX(IF(record_type = '07', balance_date, NULL))         AS closing_balance_date,
        ANY_VALUE(agency_code)                                  AS agency_code,
        ANY_VALUE(source_file)                                  AS source_file
    FROM {{ ref('stg_cbk_balances') }}
    GROUP BY account_number_11, period_month
),
movements AS (
    SELECT
        account_id,
        DATE_TRUNC(booking_date, MONTH)  AS period_month,
        SUM(signed_amount_eur)           AS movements_net_eur,
        COUNT(*)                         AS movement_count
    FROM {{ ref('customer_movements') }}
    WHERE source_system = 'MAINFRAME_CFONB'
    GROUP BY 1, 2
)
SELECT
    a.account_id,
    a.customer_id,
    b.account_number_11,
    a.account_type,
    b.agency_code,
    b.period_month,
    b.opening_balance_eur,
    b.closing_balance_eur,
    b.closing_balance_eur - b.opening_balance_eur                               AS net_change_eur,
    COALESCE(m.movement_count, 0)                                               AS movement_count,
    b.opening_balance_eur + COALESCE(m.movements_net_eur, 0)
        = b.closing_balance_eur                                                 AS is_reconciled,
    b.closing_balance_date,
    b.closing_balance_date < LAST_DAY(b.period_month)                           AS is_partial_month,
    b.closing_balance_eur < 0                                                   AS is_overdrawn,
    b.source_file
FROM balances AS b
JOIN {{ ref('accounts') }} AS a USING (account_number_11)
LEFT JOIN movements AS m
    ON m.account_id = a.account_id AND m.period_month = b.period_month
