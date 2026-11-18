-- Continuité des soldes : l'ouverture d'un mois doit égaler la clôture du mois précédent, pour chaque compte.
-- Renvoie les ruptures (0 attendue).
SELECT account_id, period_month, opening_balance_eur, previous_closing_eur
FROM (
    SELECT
        account_id,
        period_month,
        opening_balance_eur,
        LAG(closing_balance_eur) OVER (PARTITION BY account_id ORDER BY period_month) AS previous_closing_eur
    FROM {{ ref('account_monthly_balances') }}
)
WHERE previous_closing_eur IS NOT NULL
  AND previous_closing_eur != opening_balance_eur
