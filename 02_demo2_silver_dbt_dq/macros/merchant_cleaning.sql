{#
  Extrait un nom de marchand / contrepartie lisible pour l'application mobile
  et l'agent conversationnel d'analyse des transactions :
    1. Si virement néobanque/courtier : nom commercial depuis competitor_institutions (ex. Revolut)
    2. Sinon si nom de contrepartie renseigné : nom de contrepartie nettoyé
    3. Sinon : libellé bancaire débarrassé du préfixe technique de canal (CB, PRLV SEPA, VIR...)
    4. Repli ultime : libellé français de la catégorie.
#}
{% macro resolve_merchant_name(neobank_name_col, counterparty_name_col, label_col, is_internal_col, category_label_col) -%}
    COALESCE(
        NULLIF(TRIM({{ neobank_name_col }}), ''),
        IF({{ is_internal_col }}, {{ category_label_col }}, NULL),
        NULLIF(TRIM({{ counterparty_name_col }}), ''),
        NULLIF(
            TRIM(
                REGEXP_REPLACE(
                    TRIM({{ label_col }}),
                    r'^(CB|PRLV SEPA|PRLV|VIR SEPA INST|VIR SEPA|VIR INTERNE 58|VIR)\s+',
                    ''
                )
            ),
            ''
        ),
        {{ category_label_col }}
    )
{%- endmacro %}
