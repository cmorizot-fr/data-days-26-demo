{#
  Test générique : une expression agrégée sur toute la table vaut exactement `expected`
  (invariants métier d'AGENTS.md, seed=2026).
#}
{% test expression_equals(model, expression, expected) %}
SELECT observed
FROM (SELECT {{ expression }} AS observed FROM {{ model }})
WHERE observed IS NULL OR observed != {{ expected }}
{% endtest %}
