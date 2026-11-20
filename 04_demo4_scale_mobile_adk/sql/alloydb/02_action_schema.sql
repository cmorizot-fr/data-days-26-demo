-- =============================================================================
-- Démo #4 · AlloyDB `hexagone` · Schéma opérationnel Agent Action (virement 1-clic)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.savings_transfers (
  transfer_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key    TEXT UNIQUE,
  customer_id        TEXT NOT NULL,
  source_account_id  TEXT NOT NULL,
  target_offer_code  TEXT NOT NULL,
  target_offer_label TEXT NOT NULL,
  amount_eur         NUMERIC(14, 2) NOT NULL CHECK (amount_eur > 0),
  rate_bps           INTEGER,
  acpr_cushion_ok    BOOLEAN NOT NULL DEFAULT true,
  status             TEXT NOT NULL DEFAULT 'EXECUTED' CHECK (status IN ('EXECUTED', 'REVERSED')),
  initiated_by       TEXT NOT NULL DEFAULT 'adk_action_agent',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS savings_transfers_customer_idx
  ON public.savings_transfers (customer_id, created_at DESC);

-- Vue temps réel lue par l'application mobile et les 3 agents ADK (< 15 ms sur Read Pool)
CREATE OR REPLACE VIEW public.v_customer_live_summary AS
WITH live_delta AS (
  SELECT customer_id,
         COALESCE(SUM(signed_amount_eur), 0)::numeric(14,2) AS live_movements_delta_eur,
         COUNT(*) AS live_movements_count
  FROM public.v_live_movements_settled
  GROUP BY customer_id
),
transfer_delta AS (
  SELECT customer_id,
         COALESCE(SUM(amount_eur), 0)::numeric(14,2) AS savings_transferred_eur,
         COUNT(*) AS savings_transfers_count
  FROM public.savings_transfers
  WHERE status = 'EXECUTED'
  GROUP BY customer_id
)
SELECT
  i.*,
  COALESCE(l.live_movements_delta_eur, 0)::numeric(14,2) AS live_movements_delta_eur,
  COALESCE(l.live_movements_count, 0) AS live_movements_count,
  COALESCE(t.savings_transferred_eur, 0)::numeric(14,2) AS savings_transferred_eur,
  COALESCE(t.savings_transfers_count, 0) AS savings_transfers_count,
  (i.current_account_balance_d1_eur
    + COALESCE(l.live_movements_delta_eur, 0)
    - COALESCE(t.savings_transferred_eur, 0))::numeric(14,2) AS live_current_balance_eur,
  (i.predicted_end_of_month_surplus_eur
    + COALESCE(l.live_movements_delta_eur, 0)
    - COALESCE(t.savings_transferred_eur, 0))::numeric(14,2) AS live_eom_surplus_eur
FROM public.customer_mobile_insights i
LEFT JOIN live_delta l ON l.customer_id = i.customer_id
LEFT JOIN transfer_delta t ON t.customer_id = i.customer_id;
