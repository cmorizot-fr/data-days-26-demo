{#
  Extraction IA d'un avenant promotionnel PDF lu directement dans GCS (ObjectRef, aucune copie).
  Utilisée deux fois par promo_contracts : premier passage, puis reprise immédiate des PDF en échec dans la même requête.
  Température 0 : même PDF -> même réponse (extraction reproductible et testable au centime).
  Accès direct (OBJ.MAKE_REF(uri) sans connexion) : les URL signées de l'Object Table (OBJ.GET_ACCESS_URL)
  ne traversent pas le périmètre VPC Service Controls du projet et faisaient échouer une partie des PDF.
#}
{% macro ai_extract_promo_contract(object_uri) %}
AI.GENERATE(
    ('''Tu es contrôleur de gestion. Lis cet avenant promotionnel d'agence bancaire (PDF d'une page) et renvoie uniquement les champs demandés.
- contract_reference : la référence de l'avenant, au format PROMO-AAAA-NNN ;
- primary_branch_code : le code de l'agence principale signataire, 4 chiffres (le premier code agence cité) ;
- effective_date : la date d'effet, de signature ou d'arrêté de l'avenant, au format AAAA-MM-JJ ;
- end_date : la date d'échéance ou de fin, au format AAAA-MM-JJ (vide si absente) ;
- duration_months : la durée en mois (0 si absente) ;
- boost_rate_bps : la bonification de taux en points de base, par exemple 150 pour +150 bps (0 si aucune) ;
- welcome_bonus_eur : la prime unitaire d'ouverture de compte par client en euros (0 si aucune) ;
- committed_promo_cost_eur : le montant TOTAL engagé par l'avenant (coût commercial net, engagement PNB ou impact PNB), en euros, nombre positif avec 2 décimales ;
- pcec_account : le compte PCEC d'imputation, 6 chiffres.
Les montants français utilisent l'espace ou le point comme séparateur de milliers et la virgule comme séparateur décimal.
Les dates françaises sont au format JJ/MM/AAAA (jour d'abord) : 05/09/2026 est le 5 septembre 2026.''',
     OBJ.MAKE_REF({{ object_uri }})),
    connection_id => '{{ var("ai_connection") }}',
    endpoint => '{{ var("ai_endpoint") }}',
    model_params => JSON '{"generation_config": {"temperature": 0}}',
    output_schema => '''contract_reference STRING, primary_branch_code STRING, effective_date STRING, end_date STRING,
        duration_months INT64, boost_rate_bps INT64, welcome_bonus_eur FLOAT64,
        committed_promo_cost_eur FLOAT64, pcec_account STRING'''
)
{% endmacro %}


{# Une extraction n'est complète que si l'appel a réussi ET que les champs certifiés sont présents et cohérents. #}
{% macro promo_extraction_is_complete(ai, contract_id) %}
COALESCE(
    {{ ai }}.status = ''
    AND {{ ai }}.committed_promo_cost_eur > 0
    AND REGEXP_CONTAINS({{ ai }}.pcec_account, r'^[0-9]{6}$')
    AND {{ ai }}.contract_reference = {{ contract_id }},
    FALSE
)
{% endmacro %}
