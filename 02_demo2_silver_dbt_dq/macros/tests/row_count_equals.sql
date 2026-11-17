{#
  Test générique : la table contient exactement `expected` lignes
  (invariants chiffrés d'AGENTS.md, seed=2026).
#}
{% test row_count_equals(model, expected) %}
SELECT row_count
FROM (SELECT COUNT(*) AS row_count FROM {{ model }})
WHERE row_count != {{ expected }}
{% endtest %}
