{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='promo_contract_id',
    on_schema_change='append_new_columns',
) }}

-- dp_commercial_commitments · promo_contracts : 1 ligne par avenant promotionnel d'agence (250 PDF).
-- Approche hybride :
--   * les champs certifiés (montant engagé, compte PCEC, dates) sont extraits UNE fois par AI.GENERATE
--     directement sur l'Object Table (aucune copie des PDF), puis testés par dbt (total = 14 300 000,00 EUR) ;
--   * chaque ligne garde son ObjectRef (source_pdf) : un agent peut rouvrir le PDF à la demande pour citer une clause.
-- Fiabilité : température 0, reprise immédiate des PDF en échec dans la même requête, puis à chaque run
-- seuls les PDF incomplets ou modifiés (md5) sont relus. Le suivi PDF par PDF est dans promo_contracts_pdf_tracking.
-- Le type de promotion n'est pas demandé au modèle : il est déduit du compte PCEC via le référentiel promo_types.

{% set existing_cols = [] %}
{% if is_incremental() %}
    {% set existing_cols = adapter.get_columns_in_relation(this) | map(attribute='name') | list %}
{% endif %}
{% set has_tracking = 'is_extraction_complete' in existing_cols %}

WITH pdf AS (
    SELECT p.promo_contract_id, p.region_code_hint, p.uri, p.md5_hash, p.updated_ts, p.ref
    FROM {{ source('raw_bank', 'raw_promo_contracts_pdf') }} AS p
    {% if has_tracking %}
    -- PDF déjà extrait complètement dans sa version courante : on ne le relit pas,
    -- sauf relance ciblée : dbt run -s promo_contracts --vars '{reextract_ids: [PROMO-2026-186]}'
    WHERE NOT EXISTS (
        SELECT 1 FROM {{ this }} AS t
        WHERE t.promo_contract_id = p.promo_contract_id
          AND t.source_md5_hash = p.md5_hash
          AND t.is_extraction_complete
    )
    {% if var('reextract_ids', []) | length > 0 %}
       OR p.promo_contract_id IN ('{{ var("reextract_ids") | join("', '") }}')
    {% endif %}
    {% endif %}
    -- Sans colonnes de suivi (1er run ou table antérieure), les 250 PDF sont relus avec le prompt courant.
),
first_pass AS (
    SELECT pdf.*, {{ ai_extract_promo_contract('pdf.uri') }} AS ai
    FROM pdf
),
checked AS (
    SELECT *, {{ promo_extraction_is_complete('ai', 'promo_contract_id') }} AS first_pass_ok
    FROM first_pass
),
extracted AS (
    -- Reprise immédiate des réponses vides ou non conformes (quota, réponse illisible, champ manquant) :
    -- la branche ELSE du IF n'est évaluée que pour les PDF en échec au premier passage.
    SELECT
        k.* EXCEPT (ai, first_pass_ok),
        IF(k.first_pass_ok, k.ai, {{ ai_extract_promo_contract('k.uri') }}) AS ai,
        IF(k.first_pass_ok, 1, 2)                                           AS run_attempts
    FROM checked AS k
),
{% if has_tracking %}
previous AS (
    SELECT promo_contract_id, source_md5_hash, extraction_attempts
    FROM {{ this }}
),
{% endif %}
digital_cap AS (
    -- Plafond ACPR 2024-R-01 du canal mobile, porté par l'offre Livret Boost Maison
    SELECT boosted_rate_bps - base_rate_bps AS max_boost_bps, boost_duration_months AS max_boost_months
    FROM {{ ref('savings_offer_catalog') }}
    WHERE offer_code = 'LIV_BOOST_MAISON'
)
SELECT
    e.promo_contract_id,
    e.region_code_hint                                               AS region_code,
    e.ai.primary_branch_code                                         AS agency_code,
    pt.promo_type                                                    AS promo_type,
    pt.promo_type_label                                              AS promo_type_label,
    SAFE.PARSE_DATE('%Y-%m-%d', e.ai.effective_date)                 AS effective_date,
    SAFE.PARSE_DATE('%Y-%m-%d', e.ai.end_date)                       AS end_date,
    e.ai.duration_months                                             AS duration_months,
    e.ai.boost_rate_bps                                              AS boost_rate_bps,
    CAST(ROUND(e.ai.welcome_bonus_eur, 2) AS NUMERIC)                AS welcome_bonus_eur,
    CAST(ROUND(e.ai.committed_promo_cost_eur, 2) AS NUMERIC)         AS committed_promo_cost_eur,
    e.ai.pcec_account                                                AS pcec_account,
    e.ai.boost_rate_bps > 0
        AND (e.ai.boost_rate_bps > c.max_boost_bps
             OR e.ai.duration_months > c.max_boost_months)           AS exceeds_acpr_digital_cap,
    -- Suivi de l'extraction
    {{ promo_extraction_is_complete('e.ai', 'e.promo_contract_id') }} AS is_extraction_complete,
    e.ai.status                                                      AS extraction_status,
    IF({{ promo_extraction_is_complete('e.ai', 'e.promo_contract_id') }}, NULL,
       SUBSTR(TO_JSON_STRING(e.ai.full_response), 1, 1000))         AS extraction_error_detail,
    e.ai.contract_reference                                          AS extracted_contract_reference,
    {% if has_tracking %}
    -- Tentatives cumulées sur la version courante du PDF (remise à zéro si le PDF change)
    e.run_attempts + IF(pv.source_md5_hash = e.md5_hash, COALESCE(pv.extraction_attempts, 0), 0)
    {% else %}
    e.run_attempts
    {% endif %}                                                      AS extraction_attempts,
    '{{ var("ai_endpoint").split("/")[-1] }}'                        AS extraction_model,
    CURRENT_TIMESTAMP()                                              AS extracted_at,
    -- Lien vers le PDF source. Lecture à la demande : AI.GENERATE((question, OBJ.MAKE_REF(source_uri)), ...) sur une seule ligne
    -- (accès direct : les URL signées de source_pdf ne traversent pas le périmètre VPC Service Controls)
    e.ref                                                            AS source_pdf,
    e.uri                                                            AS source_uri,
    e.md5_hash                                                       AS source_md5_hash,
    e.updated_ts                                                     AS source_updated_at
FROM extracted AS e
CROSS JOIN digital_cap AS c
LEFT JOIN {{ ref('promo_types') }} AS pt ON pt.pcec_account = e.ai.pcec_account
{% if has_tracking %}
LEFT JOIN previous AS pv USING (promo_contract_id)
{% endif %}
