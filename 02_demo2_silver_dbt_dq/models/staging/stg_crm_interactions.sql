{{ config(materialized='view') }}

-- Interactions CRM AWS (RDV agence, call center, messagerie app).
-- Profiling : identifiants uniques, 0 client orphelin, code guichet = '0' + code agence sur 100 % des lignes.
SELECT
    interaction_id,
    customer_id,
    RIGHT(TRIM(guichet_code_5), 4)          AS agency_code,
    interaction_ts,
    DATE(interaction_ts)                    AS interaction_date,
    channel,
    topic_code,
    advisor_sentiment_tag,
    verbatim_note
FROM {{ source('raw_bank', 'aws_crm_interactions') }}
