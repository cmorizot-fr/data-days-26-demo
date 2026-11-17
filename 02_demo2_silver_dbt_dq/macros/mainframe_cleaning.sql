{#
  Normalise un code agence Mainframe sur 4 caractères.
  Cas RAW observés : '0042' (correct), '42  ' (cadré à gauche), '    ' (vide).
  Repli sur les 4 derniers chiffres du code guichet (5 caractères) si le code agence est vide.
#}
{% macro normalize_agency_code(agency_raw, guichet_raw) -%}
    COALESCE(
        IF(TRIM({{ agency_raw }}) = '', NULL, LPAD(TRIM({{ agency_raw }}), 4, '0')),
        IF(TRIM({{ guichet_raw }}) = '', NULL, RIGHT(LPAD(TRIM({{ guichet_raw }}), 5, '0'), 4))
    )
{%- endmacro %}

{# Date Mainframe 'YYYYMMDD' ; '00000000' / '99999999' / vide -> NULL #}
{% macro parse_mainframe_date(raw_col) -%}
    IF({{ raw_col }} IN ('00000000', '99999999'), NULL, SAFE.PARSE_DATE('%Y%m%d', TRIM({{ raw_col }})))
{%- endmacro %}
