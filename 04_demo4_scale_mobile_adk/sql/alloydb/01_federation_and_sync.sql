-- =============================================================================
-- Démo #4 · AlloyDB `hexagone` · Fédération BigQuery (`bigquery_fdw`) & Sync (`alloydb_sync`)
-- Nécessite PostgreSQL 18 + flags bigquery_fdw.enabled=on, alloydb_sync.enabled=on
-- et rôles BigQuery (dataViewer, jobUser, readSessionUser) sur le SA du cluster AlloyDB.
-- Exécuter sur le primaire (`hexagone-d4-primary`) dans une session read-write.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS bigquery_fdw;
CREATE EXTENSION IF NOT EXISTS alloydb_sync;

CREATE SCHEMA IF NOT EXISTS bq_fed;
CREATE SERVER IF NOT EXISTS bigquery_server FOREIGN DATA WRAPPER bigquery_fdw;
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER bigquery_server;
CREATE USER MAPPING IF NOT EXISTS FOR postgres SERVER bigquery_server;
CREATE USER MAPPING IF NOT EXISTS FOR PUBLIC SERVER bigquery_server;

-- -----------------------------------------------------------------------------
-- 1. Fédération zéro-copie (`bigquery_fdw`) : requêtes à la demande vers BigQuery
--    - bq_fed.customer_mobile_insights : utilisé sur scène pour comparer latence FDW vs Sync
--    - bq_fed.customer_monthly_spending (5,0 M) & customer_transactions_enriched (5,5 M) :
--      historique détaillé interrogé à la demande sans dupliquer 2,5 Go dans AlloyDB.
-- -----------------------------------------------------------------------------
CREATE FOREIGN TABLE IF NOT EXISTS bq_fed.customer_mobile_insights (
  customer_id text,
  current_account_id text,
  current_account_balance_d1_eur numeric,
  predicted_end_of_month_surplus_eur numeric,
  detected_subscription_hike_merchant text,
  subscription_hike_delta_eur numeric,
  recent_health_refund_eur numeric,
  recommended_savings_amount_eur numeric,
  primary_recommended_offer_code text,
  boosted_alternative_offer_code text,
  recommended_mobile_action text
) SERVER bigquery_server OPTIONS (project 'data-days-demo', dataset 'gold_bank', table 'customer_mobile_insights');

CREATE FOREIGN TABLE IF NOT EXISTS bq_fed.customer_monthly_spending (
  customer_id text,
  period_month date,
  category_group text,
  category_group_label_fr text,
  category text,
  category_label_fr text,
  cashflow_role text,
  direction text,
  transaction_count bigint,
  total_amount_eur numeric,
  signed_total_eur numeric,
  prev_month_amount_eur numeric,
  mom_delta_eur numeric,
  mom_delta_pct double precision,
  avg_3m_amount_eur numeric,
  share_of_month_outflows_pct double precision,
  neobank_transaction_count bigint,
  neobank_outflow_eur numeric,
  is_partial_month boolean
) SERVER bigquery_server OPTIONS (project 'data-days-demo', dataset 'gold_bank', table 'customer_monthly_spending');

CREATE FOREIGN TABLE IF NOT EXISTS bq_fed.customer_transactions_enriched (
  movement_id text,
  customer_id text,
  account_id text,
  account_type text,
  source_system text,
  booking_date date,
  booking_month date,
  day_of_month bigint,
  is_current_month boolean,
  is_post_batch_realtime boolean,
  direction text,
  amount_eur numeric,
  signed_amount_eur numeric,
  category_group text,
  category_group_label_fr text,
  category text,
  category_label_fr text,
  cashflow_role text,
  is_income boolean,
  is_fixed_charge boolean,
  is_variable_card boolean,
  is_recurring_candidate boolean,
  is_subscription boolean,
  is_health_refund boolean,
  is_organic_budget_flow boolean,
  merchant_name text,
  raw_label text,
  payment_scheme text,
  is_neobank_outflow boolean,
  neobank_institution_name text,
  neobank_institution_type text,
  is_internal_transfer boolean
) SERVER bigquery_server OPTIONS (project 'data-days-demo', dataset 'gold_bank', table 'customer_transactions_enriched');

-- -----------------------------------------------------------------------------
-- 2. Synchronisation locale périodique (`alloydb_sync`, < 1 ms sur Read Pool)
-- -----------------------------------------------------------------------------
SELECT
  alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.customer_mobile_insights', 'public.customer_mobile_insights', INTERVAL '1 hour', 'replace', ARRAY['customer_id']) AS insights_job,
  alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.customer_card_spending_forecast', 'public.customer_card_spending_forecast', INTERVAL '1 hour', 'replace', ARRAY['customer_id']) AS forecast_job,
  alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.customer_recurring_commitments', 'public.customer_recurring_commitments', INTERVAL '1 hour', 'replace', NULL) AS commitments_job,
  alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.movement_categories', 'public.movement_categories', INTERVAL '1 hour', 'replace', NULL) AS categories_job,
  alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.budget_insight_rules', 'public.budget_insight_rules', INTERVAL '1 hour', 'replace', NULL) AS rules_job,
  alloydb_sync.create_bq_sync_table('data-days-demo.silver_bank.savings_offers', 'public.savings_offers', INTERVAL '1 hour', 'replace', ARRAY['offer_code']) AS offers_job;
