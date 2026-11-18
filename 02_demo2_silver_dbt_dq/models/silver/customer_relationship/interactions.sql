{{ config(
    materialized='table',
    partition_by={'field': 'interaction_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['customer_id', 'topic_code'],
) }}

-- dp_customer_relationship · interactions : 1 ligne par contact client (RDV agence, call center, messagerie app).
--  * verbatim_note est conservé mais masqué par CLS (policy tag PII_SENSITIVE_FREETEXT_REDACT, ALWAYS_NULL) :
--    12,8 % des verbatims évoquent la santé (RGPD Art. 9).
--  * Indicateurs non sensibles portés par des référentiels (aucune règle en dur) :
--      - seed crm_topics : risque de fuite, offre promo et sentiment attendu par sujet ;
--      - seed competitor_institutions : motifs de mention des néobanques et courtiers.
--    Aucun indicateur santé n'est créé : ce serait lui-même une donnée sensible.
--  * Le tag de sentiment du conseiller est saisi à la main : il est conservé, et l'écart avec le sujet est signalé.
WITH src AS (
    SELECT * FROM {{ ref('stg_crm_interactions') }}
),
mention_regex AS (
    SELECT STRING_AGG(mention_pattern, '|') AS pattern
    FROM {{ ref('competitor_institutions') }}
)
SELECT
    s.interaction_id,
    s.customer_id,
    s.agency_code,
    s.interaction_ts,
    s.interaction_date,
    s.channel,
    s.topic_code,
    s.advisor_sentiment_tag,
    t.is_liquidity_outflow_risk,
    t.is_promo_related,
    REGEXP_CONTAINS(LOWER(s.verbatim_note), m.pattern)          AS mentions_neobank,
    s.advisor_sentiment_tag != t.expected_sentiment_tag         AS is_sentiment_tag_inconsistent,
    s.verbatim_note
FROM src AS s
LEFT JOIN {{ ref('crm_topics') }} AS t USING (topic_code)
CROSS JOIN mention_regex AS m
