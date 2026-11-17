-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 : Certification du silo SaaS CRM (Iceberg sur GCS)
-- et de son alignement avec le Mainframe (cbk_*) et le SI Paiements.
--
-- Variables : __PROJECT_ID__, __DATASET_RAW__
-- ==============================================================================

WITH
cust AS (SELECT * FROM `__PROJECT_ID__.__DATASET_RAW__.aws_crm_customers`),
acc AS (SELECT * FROM `__PROJECT_ID__.__DATASET_RAW__.aws_crm_account_portfolio`),
itx AS (SELECT * FROM `__PROJECT_ID__.__DATASET_RAW__.aws_crm_interactions`),
br AS (SELECT * FROM `__PROJECT_ID__.__DATASET_RAW__.aws_crm_branches_ref`),
mf_acc AS (SELECT account_id, iban FROM `__PROJECT_ID__.__DATASET_RAW__.cbk_accounts_master`),
mf_cust AS (SELECT customer_id, TRIM(first_name) AS first_name, TRIM(last_name) AS last_name
            FROM `__PROJECT_ID__.__DATASET_RAW__.cbk_customers_ref`),
kpi AS (
  SELECT
    (SELECT COUNT(*) FROM cust) AS n_customers,
    (SELECT COUNT(DISTINCT region_code) FROM cust) AS n_regions,
    (SELECT COUNT(*) FROM br) AS n_branches,
    (SELECT COUNTIF(closed_date IS NOT NULL) FROM cust) AS n_customer_closures,
    (SELECT COUNT(*) FROM acc) AS n_accounts,
    (SELECT COUNTIF(opened_in_current_quarter) FROM acc) AS n_openings_quarter,
    (SELECT COUNTIF(closed_date IS NOT NULL) FROM acc) AS n_account_closures,
    (SELECT COUNT(*) FROM acc LEFT JOIN mf_acc USING (account_id) WHERE mf_acc.account_id IS NULL) AS n_orphans_vs_mainframe,
    (SELECT COUNT(*) FROM acc JOIN mf_acc USING (account_id) WHERE acc.iban != mf_acc.iban) AS n_iban_mismatch,
    (SELECT COUNT(*) FROM cust JOIN mf_cust USING (customer_id)
       WHERE cust.first_name != mf_cust.first_name OR cust.last_name != mf_cust.last_name) AS n_name_mismatch,
    (SELECT COUNT(*) FROM itx) AS n_interactions,
    (SELECT COUNTIF(customer_id = 'CUST00002026') FROM itx) AS n_witness_interactions,
    (SELECT COUNT(*) FROM itx LEFT JOIN cust USING (customer_id) WHERE cust.customer_id IS NULL) AS n_interactions_unknown_customer,
    (SELECT COUNT(DISTINCT promo_contract_id) FROM acc WHERE promo_contract_id IS NOT NULL) AS n_promo_contracts
)
SELECT check_name, observed, expected, IF(observed = expected, 'PASS', 'FAIL') AS status
FROM kpi,
UNNEST([
  STRUCT(1 AS ord, 'Clients CRM' AS check_name, n_customers AS observed, 80000 AS expected),
  STRUCT(2, 'Régions commerciales', n_regions, 8),
  STRUCT(3, 'Agences', n_branches, 450),
  STRUCT(4, 'Clôtures clients sur le trimestre', n_customer_closures, 0),
  STRUCT(5, 'Comptes CRM', n_accounts, 95000),
  STRUCT(6, 'Ouvertures sur le trimestre', n_openings_quarter, 15000),
  STRUCT(7, 'Clôtures de comptes sur le trimestre', n_account_closures, 0),
  STRUCT(8, 'Comptes CRM absents du Mainframe J-1 (orphelins)', n_orphans_vs_mainframe, 650),
  STRUCT(9, 'IBAN divergents CRM vs Mainframe', n_iban_mismatch, 0),
  STRUCT(10, 'Noms divergents CRM vs Mainframe', n_name_mismatch, 0),
  STRUCT(11, 'Interactions RDV / Call Center', n_interactions, 320000),
  STRUCT(12, 'Interactions rattachées à un client inconnu', n_interactions_unknown_customer, 0),
  STRUCT(13, 'Contrats promo PDF référencés', n_promo_contracts, 250),
  STRUCT(14, 'Interactions du témoin CUST00002026 (>= 2)', LEAST(n_witness_interactions, 2), 2)
])
ORDER BY ord;
