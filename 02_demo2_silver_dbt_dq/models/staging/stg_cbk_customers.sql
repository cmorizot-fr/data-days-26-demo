{{ config(materialized='view') }}

-- Référentiel clients Mainframe : typage des dates YYYYMMDD et normalisation des codes agence.
SELECT
    TRIM(customer_id)                                                   AS customer_id,
    {{ normalize_agency_code('code_agence_raw', 'code_guichet_raw') }}  AS agency_code,
    code_agence_raw                                                     AS agency_code_raw,
    {{ normalize_agency_code('code_agence_raw', 'code_guichet_raw') }} IS DISTINCT FROM code_agence_raw
                                                                        AS agency_code_was_normalized,
    TRIM(region_code)                                                   AS region_code,
    {{ parse_mainframe_date('birth_date_raw') }}                        AS birth_date,
    age_years,
    TRIM(segment_clientele)                                             AS segment,
    TRIM(csp_code)                                                      AS csp,
    {{ parse_mainframe_date('onboarding_date_raw') }}                   AS onboarding_date,
    {{ parse_mainframe_date('closure_date_raw') }}                      AS closure_date,
    TRIM(dossier_status)                                                AS dossier_status,
    TRIM(last_name)                                                     AS last_name,
    TRIM(first_name)                                                    AS first_name,
    {{ parse_mainframe_date('batch_date_raw') }}                        AS batch_date
FROM {{ source('raw_bank', 'cbk_customers_ref') }}
