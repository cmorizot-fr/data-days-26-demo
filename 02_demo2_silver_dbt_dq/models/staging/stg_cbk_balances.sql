{{ config(materialized='view') }}

-- Soldes CFONB 120 : ligne '01' = solde d'ouverture du mois, ligne '07' = solde de clôture.
-- Profiling : 0 date invalide, 0 code guichet mal cadré, 1 seul fichier par mois (le RUN01 en ABEND est déjà écarté par Spark).
SELECT
    period_ym,
    PARSE_DATE('%Y%m', period_ym)                                AS period_month,
    record_type,
    TRIM(num_compte_11)                                          AS account_number_11,
    {{ parse_mainframe_date('balance_date_raw') }}               AS balance_date,
    signed_balance_eur,
    {{ normalize_agency_code("''", 'code_guichet_raw') }}        AS agency_code,
    _source_file                                                 AS source_file
FROM {{ source('raw_bank', 'cbk_cfonb_balances') }}
