{{ config(
    materialized='table',
    cluster_by=['customer_id'],
) }}

-- dp_customer_timeline · beneficiaries : bénéficiaires IBAN externes ajoutés par les clients,
-- 1 ligne par (compte, IBAN bénéficiaire) — retries techniques de l'API mobile retirés.
WITH src AS (
    SELECT
        account_holder.customer_id      AS customer_id,
        account_holder.account_id       AS account_id,
        beneficiary.iban                AS beneficiary_iban,
        beneficiary.agent_bic           AS beneficiary_bic,
        beneficiary.custom_label        AS custom_label,
        security_context.channel        AS channel,
        header.event_ts                 AS enrolled_at,
        ingestion_source
    FROM {{ source('raw_bank', 'raw_iban_events_unified') }}
)
SELECT
    customer_id,
    account_id,
    beneficiary_iban,
    beneficiary_bic,
    beneficiary_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX') AS is_neobank_or_broker,
    custom_label,
    channel,
    enrolled_at                                                      AS first_enrolled_at,
    ingestion_source
FROM src
QUALIFY ROW_NUMBER() OVER (PARTITION BY account_id, beneficiary_iban ORDER BY enrolled_at) = 1
