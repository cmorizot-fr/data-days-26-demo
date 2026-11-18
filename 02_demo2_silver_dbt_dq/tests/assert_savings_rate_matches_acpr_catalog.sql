-- Conformité : le taux servi par le Mainframe doit être égal au taux de base du catalogue d'offres
-- aligné sur l'ACPR 2024-R-01 (PDF REG_06). Le Livret Maison est servi à 1,50 %, comme dans REG_06
-- et dans les avenants agence. Test bloquant : toute ligne renvoyée est un écart de taux.
SELECT a.account_id, a.account_type, a.rate_bps AS served_rate_bps, o.base_rate_bps AS catalog_base_rate_bps
FROM {{ ref('accounts') }} AS a
JOIN {{ ref('savings_offers') }} AS o
    ON o.account_type = a.account_type
   AND o.boosted_rate_bps IS NULL
WHERE a.rate_bps != o.base_rate_bps
