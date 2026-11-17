{{ config(
    materialized='table',
    cluster_by=['customer_id'],
) }}

-- dp_customer_360 · accounts : 1 ligne par compte (95 000).
-- Le CRM AWS est la base (il contient aussi les 650 comptes ouverts après le batch Mainframe J-1) ;
-- le Mainframe apporte le solde de la veille et la date du dernier mouvement.
WITH crm AS (
    SELECT * FROM {{ ref('stg_crm_accounts') }}
),
mainframe AS (
    SELECT * FROM {{ ref('stg_cbk_accounts') }}
)
SELECT
    COALESCE(crm.account_id, mf.account_id)                  AS account_id,
    COALESCE(crm.customer_id, mf.customer_id)                AS customer_id,
    COALESCE(crm.account_number_11, mf.account_number_11)    AS account_number_11,
    COALESCE(crm.iban, mf.iban)                              AS iban,
    COALESCE(crm.account_type, mf.account_type)              AS account_type,
    COALESCE(crm.account_type, mf.account_type) = 'CC_CHQ'   AS is_current_account,
    COALESCE(crm.product_label, mf.product_label)            AS product_label,
    COALESCE(crm.rate_bps, mf.rate_bps)                      AS rate_bps,
    COALESCE(crm.agency_code, mf.agency_code)                AS agency_code,
    COALESCE(crm.account_status, mf.account_status)          AS account_status,
    COALESCE(crm.opened_date, mf.opening_date)               AS opened_date,
    COALESCE(crm.closed_date, mf.closure_date)               AS closed_date,
    COALESCE(crm.opened_in_current_quarter, FALSE)           AS opened_in_current_quarter,
    crm.promo_contract_id,
    mf.balance_d1_eur,
    mf.last_movement_date,
    mf.account_id IS NOT NULL                                AS is_in_mainframe,
    mf.account_id IS NULL                                    AS is_mainframe_orphan
FROM crm
FULL OUTER JOIN mainframe AS mf
    ON mf.account_id = crm.account_id
