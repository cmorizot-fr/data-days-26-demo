{{ config(materialized='view') }}

-- Clients du CRM AWS (Iceberg Glue / S3) : déjà typés, simple nettoyage des espaces.
SELECT
    TRIM(customer_id)              AS customer_id,
    TRIM(first_name)               AS first_name,
    TRIM(last_name)                AS last_name,
    birth_date,
    age,
    TRIM(age_segment)              AS age_segment,
    TRIM(segment)                  AS segment,
    TRIM(csp)                      AS csp,
    declared_monthly_income_eur,
    TRIM(region_code)              AS region_code,
    TRIM(region_name)              AS region_name,
    TRIM(agency_code_4)            AS agency_code,
    TRIM(city)                     AS city,
    onboarding_date,
    TRIM(commercial_status)        AS commercial_status,
    closed_date,
    digital_opt_in,
    crm_updated_at
FROM {{ source('raw_bank', 'aws_crm_customers') }}
