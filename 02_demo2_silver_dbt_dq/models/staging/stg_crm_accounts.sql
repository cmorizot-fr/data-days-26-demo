{{ config(materialized='view') }}

-- Portefeuille de comptes du CRM AWS (Iceberg Glue / S3).
SELECT
    TRIM(account_id)               AS account_id,
    TRIM(num_compte_11)            AS account_number_11,
    TRIM(iban)                     AS iban,
    TRIM(customer_id)              AS customer_id,
    TRIM(agency_code_4)            AS agency_code,
    TRIM(account_type)             AS account_type,
    TRIM(product_label)            AS product_label,
    rate_bps,
    TRIM(account_status)           AS account_status,
    opened_date,
    closed_date,
    opened_in_current_quarter,
    NULLIF(TRIM(promo_contract_id), '') AS promo_contract_id
FROM {{ source('raw_bank', 'aws_crm_account_portfolio') }}
