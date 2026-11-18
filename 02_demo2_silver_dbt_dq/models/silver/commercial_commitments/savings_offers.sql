{{ config(materialized='table') }}

-- dp_commercial_commitments · savings_offers : catalogue des offres d'épargne proposables, 1 ligne par offre.
-- Le catalogue est versionné dans le seed savings_offer_catalog, puis contrôlé contre les règles que l'IA
-- extrait du PDF réglementaire REG_06 (Recommandation ACPR 2024-R-01, commercialisation digitale d'épargne).
WITH acpr AS (
    SELECT
        uri AS rule_source_uri,
        AI.GENERATE(
            ('''Ce document est une recommandation de conformité sur la commercialisation d'épargne sur mobile. Extrais :
- regulated_rate_bps : le taux du Livret A / LDDS en points de base ;
- base_rate_bps : le taux de base du Livret Maison en points de base ;
- boosted_rate_cap_bps : le taux boosté maximal du Livret Maison en points de base ;
- max_boost_bps : la bonification maximale autorisée en points de base ;
- max_boost_duration_months : la durée maximale de la bonification en mois ;
- max_surplus_share_pct : la part maximale du surplus de fin de mois qu'on peut recommander d'épargner, en pourcentage.''',
             OBJ.GET_ACCESS_URL(ref, 'r')),
            connection_id => '{{ var("ai_connection") }}',
            endpoint => '{{ var("ai_endpoint") }}',
            output_schema => '''regulated_rate_bps INT64, base_rate_bps INT64, boosted_rate_cap_bps INT64,
                max_boost_bps INT64, max_boost_duration_months INT64, max_surplus_share_pct INT64'''
        ) AS ai
    FROM {{ source('raw_bank', 'raw_cfo_regulatory_pdf') }}
    WHERE uri LIKE '%/REG_06_ACPR_2024_R01_%'
)
SELECT
    o.offer_code,
    o.product_label,
    o.account_type,
    o.channel,
    o.base_rate_bps,
    o.boosted_rate_bps,
    o.boost_duration_months,
    COALESCE(o.boosted_rate_bps, o.base_rate_bps)                    AS headline_rate_bps,
    o.deposit_cap_eur,
    o.is_regulated,
    o.tax_status,
    o.priority_rank,
    a.ai.max_surplus_share_pct                                       AS acpr_max_surplus_share_pct,
    a.ai.boosted_rate_cap_bps                                        AS acpr_boosted_rate_cap_bps,
    a.ai.max_boost_bps                                               AS acpr_max_boost_bps,
    a.ai.max_boost_duration_months                                   AS acpr_max_boost_duration_months,
    CASE
        WHEN o.is_regulated THEN o.base_rate_bps = a.ai.regulated_rate_bps
        WHEN o.boosted_rate_bps IS NULL THEN o.base_rate_bps = a.ai.base_rate_bps
        ELSE o.base_rate_bps = a.ai.base_rate_bps
             AND o.boosted_rate_bps <= a.ai.boosted_rate_cap_bps
             AND o.boosted_rate_bps - o.base_rate_bps <= a.ai.max_boost_bps
             AND o.boost_duration_months <= a.ai.max_boost_duration_months
    END                                                              AS is_acpr_compliant,
    a.rule_source_uri
FROM {{ ref('savings_offer_catalog') }} AS o
CROSS JOIN acpr AS a
