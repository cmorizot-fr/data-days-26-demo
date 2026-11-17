{{ config(
    materialized='table',
    cluster_by=['region_code', 'agency_code'],
) }}

-- dp_customer_360 · customers : 1 ligne par client (80 000).
-- Le CRM AWS est la base (il contient aussi les 650 clients créés après le batch Mainframe J-1) ;
-- le Mainframe apporte le statut de dossier et la date du batch.
WITH crm AS (
    SELECT * FROM {{ ref('stg_crm_customers') }}
),
mainframe AS (
    SELECT * FROM {{ ref('stg_cbk_customers') }}
)
SELECT
    COALESCE(crm.customer_id, mf.customer_id)                AS customer_id,
    COALESCE(crm.first_name, mf.first_name)                  AS first_name,
    COALESCE(crm.last_name, mf.last_name)                    AS last_name,
    COALESCE(crm.birth_date, mf.birth_date)                  AS birth_date,
    COALESCE(crm.age, mf.age_years)                          AS age,
    COALESCE(crm.age, mf.age_years) BETWEEN 18 AND 32        AS is_young_18_32,
    crm.age_segment,
    COALESCE(crm.segment, mf.segment)                        AS segment,
    COALESCE(crm.csp, mf.csp)                                AS csp,
    crm.declared_monthly_income_eur,
    COALESCE(crm.region_code, mf.region_code)                AS region_code,
    crm.region_name,
    COALESCE(crm.agency_code, mf.agency_code)                AS agency_code,
    crm.city,
    COALESCE(crm.onboarding_date, mf.onboarding_date)        AS onboarding_date,
    COALESCE(crm.closed_date, mf.closure_date)               AS closed_date,
    crm.commercial_status,
    mf.dossier_status                                        AS mainframe_dossier_status,
    COALESCE(crm.digital_opt_in, FALSE)                      AS digital_opt_in,
    mf.customer_id IS NOT NULL                               AS is_in_mainframe,
    mf.customer_id IS NULL                                   AS is_mainframe_orphan,
    mf.batch_date                                            AS mainframe_batch_date,
    crm.crm_updated_at
FROM crm
FULL OUTER JOIN mainframe AS mf
    ON mf.customer_id = crm.customer_id
