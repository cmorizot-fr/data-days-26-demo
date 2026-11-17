{#
  Utilise le dataset déclaré (+schema) tel quel, sans le préfixer par le dataset
  par défaut du profil : staging -> raw_bank, silver -> silver_bank.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
