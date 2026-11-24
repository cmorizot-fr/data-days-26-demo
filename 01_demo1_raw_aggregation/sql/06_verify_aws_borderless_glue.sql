-- ==============================================================================
-- Démo #1 · Étape 3 — Audit SQL inter-clouds Borderless Lakehouse
-- BigQuery (europe-west1) <-> AWS Glue / S3 Iceberg (eu-west-1 · crm_callcenter_db)
-- ==============================================================================

SELECT
  (SELECT COUNT(*) FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_branches_ref`)      AS aws_branches_450,
  (SELECT COUNT(*) FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_customers`)         AS aws_customers_80k,
  (SELECT COUNT(*) FROM `data-days-demo.raw_bank.cbk_customers_ref`)                              AS mf_customers_79350,
  (SELECT COUNT(*)
   FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_customers` AS c
   LEFT JOIN `data-days-demo.raw_bank.cbk_customers_ref` AS m USING (customer_id)
   WHERE m.customer_id IS NULL)                                                                   AS j0_orphan_customers_650,
  (SELECT COUNT(*) FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_account_portfolio`) AS aws_accounts_95k,
  (SELECT COUNT(*)
   FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_account_portfolio` AS a
   LEFT JOIN `data-days-demo.raw_bank.cbk_accounts_master` AS m USING (account_id)
   WHERE m.account_id IS NULL)                                                                   AS j0_orphan_accounts_650,
  (SELECT COUNTIF(opened_in_current_quarter)
   FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_account_portfolio`)                 AS qtr_openings_15k,
  (SELECT COUNTIF(closed_date IS NOT NULL)
   FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_account_portfolio`)                 AS closures_0,
  (SELECT COUNT(*) FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_interactions`)      AS aws_interactions_320k;
