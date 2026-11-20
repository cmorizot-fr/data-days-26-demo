-- =============================================================================
-- Démo #4 · Reset opérationnel AlloyDB (rejouable avant chaque répétition / keynote)
-- =============================================================================

TRUNCATE TABLE public.savings_transfers;
DELETE FROM public.live_movements WHERE customer_id = 'CUST00002026';

-- Contrôle baseline attendu pour Lucas Martin (CUST00002026) :
--   live_current_balance_eur = 6892.00 | live_eom_surplus_eur = 300.00 | recommended_savings_amount_eur = 200
SELECT customer_id,
       current_account_id,
       live_current_balance_eur,
       live_eom_surplus_eur,
       recommended_savings_amount_eur,
       primary_recommended_offer_code,
       boosted_alternative_offer_code
FROM public.v_customer_live_summary
WHERE customer_id = 'CUST00002026';
