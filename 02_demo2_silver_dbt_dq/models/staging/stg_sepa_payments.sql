{{ config(materialized='view') }}

-- Paiements SEPA (historique + temps réel) aplatis depuis les STRUCT ISO 20022.
-- Dédoublonnage des retries techniques (~3,4 %) : 1 ligne par end_to_end_id (première exécution).
WITH src AS (
    SELECT
        header.end_to_end_id                         AS end_to_end_id,
        header.execution_ts                          AS execution_ts,
        settlement.payment_scheme                    AS payment_scheme,
        settlement.tx_status                         AS tx_status,
        settlement.status_reason_code                AS status_reason_code,
        instructed_amount.amount_eur                 AS amount_eur,
        debtor.customer_id                           AS customer_id,
        debtor.account_id                            AS account_id,
        creditor.name                                AS counterparty_name,
        creditor.iban                                AS counterparty_iban,
        creditor.agent_bic                           AS counterparty_bic,
        remittance.unstructured_info                 AS remittance_info,
        ingestion_source
    FROM {{ source('raw_bank', 'raw_sepa_payments_unified') }}
)
SELECT
    end_to_end_id,
    execution_ts,
    DATE(execution_ts)                                                    AS booking_date,  -- même date que le CFONB
    payment_scheme,
    tx_status,
    tx_status = 'ACSC'                                                    AS is_settled,
    status_reason_code,
    IF(ENDS_WITH(payment_scheme, 'INBOUND'), amount_eur, -amount_eur)     AS signed_amount_eur,
    customer_id,
    account_id,
    counterparty_name,
    counterparty_iban,
    counterparty_bic,
    TRIM(remittance_info)                                                 AS label,
    ingestion_source
FROM src
QUALIFY ROW_NUMBER() OVER (PARTITION BY end_to_end_id ORDER BY execution_ts) = 1
