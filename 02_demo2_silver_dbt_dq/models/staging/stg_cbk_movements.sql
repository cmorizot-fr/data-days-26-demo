{{ config(materialized='view') }}

-- Mouvements CFONB 120 (lignes '04' + complément SEPA '05' rattaché par Spark).
-- Dates typées ; date de valeur '00000000' / '99999999' remplacée par la date comptable et signalée.
WITH src AS (
    SELECT * FROM {{ source('raw_bank', 'cbk_cfonb_movements') }}
)
SELECT
    CONCAT('CFONB-', _source_file, '-', CAST(_line_offset AS STRING))      AS movement_id,
    TRIM(num_compte_11)                                                    AS account_number_11,
    {{ parse_mainframe_date('date_compta_raw') }}                          AS booking_date,
    COALESCE({{ parse_mainframe_date('date_valeur_raw') }},
             {{ parse_mainframe_date('date_compta_raw') }})                AS value_date,
    {{ parse_mainframe_date('date_valeur_raw') }} IS NULL                  AS value_date_was_invalid,
    signed_amount_eur,
    TRIM(code_afb)                                                         AS code_afb,
    TRIM(code_op_interne)                                                  AS code_op_interne,
    TRIM(libelle_court)                                                    AS label,
    NULLIF(TRIM(counterparty_bic), '')                                     AS counterparty_bic,
    NULLIF(TRIM(sepa_end_to_end_id), '')                                   AS end_to_end_id,
    _source_file                                                           AS source_file
FROM src
