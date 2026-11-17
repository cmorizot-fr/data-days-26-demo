{{ config(materialized='view') }}

-- Maître des comptes Mainframe : typage des dates, normalisation des codes agence, solde J-1.
SELECT
    TRIM(account_id)                                                    AS account_id,
    TRIM(num_compte_11)                                                 AS account_number_11,
    TRIM(customer_id)                                                   AS customer_id,
    {{ normalize_agency_code('code_agence_raw', 'code_guichet_raw') }}  AS agency_code,
    TRIM(iban)                                                          AS iban,
    TRIM(account_type)                                                  AS account_type,
    TRIM(currency_iso)                                                  AS currency,
    {{ parse_mainframe_date('opening_date_raw') }}                      AS opening_date,
    {{ parse_mainframe_date('closure_date_raw') }}                      AS closure_date,
    TRIM(account_status)                                                AS account_status,
    rate_bps,
    solde_veille_eur                                                    AS balance_d1_eur,
    {{ parse_mainframe_date('last_movement_date_raw') }}                AS last_movement_date,
    TRIM(product_label)                                                 AS product_label
FROM {{ source('raw_bank', 'cbk_accounts_master') }}
