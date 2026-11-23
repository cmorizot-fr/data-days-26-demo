-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 · Étape 4 (Sous-étape 5)
-- Requête SQL de vérification du masquage dynamique Column-Level Security (CLS)
-- sur les sous-champs `STRUCT` de `raw_bank.raw_sepa_payments_pubsub_stream`.
--
-- Exécution côté Data Analyst (`roles/bigquerydatapolicy.maskedReader`) :
--   CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT="hexagone-data-analyst@data-days-demo.iam.gserviceaccount.com" \
--     bq --location=europe-west1 query --project_id=data-days-demo --use_legacy_sql=false \
--     --label datacloud:antigravity < 01_demo1_raw_aggregation/sql/07_verify_cls_masking.sql
--
-- Note IAM importante : un compte `roles/owner` possède `datacatalog.categories.fineGrainedGet`
-- et voit les données en clair ; l'impersonation du compte `hexagone-data-analyst`
-- permet de tester le rendu exact vu par les équipes Data / dbt.
-- ==============================================================================

SELECT
  -- 1. Sous-champs analytiques des STRUCT -> EN CLAIR (exploitables par dbt)
  header.end_to_end_id,
  settlement.payment_scheme,
  settlement.tx_status,
  instructed_amount.amount_eur,
  debtor.customer_id,
  creditor.agent_bic,

  -- 2. Sous-champs IBAN -> LAST_FOUR_CHARACTERS (ex: XXXXX2623)
  debtor.iban AS debtor_iban_masked,
  creditor.iban AS creditor_iban_masked,

  -- 3. Identité civile -> SHA256 déterministe (jointures préservées sans révéler le nom)
  SUBSTR(debtor.full_name, 1, 16) || '...' AS debtor_name_sha256,

  -- 4. Texte libre (santé RGPD Art. 9 : pharmacie / CPAM) -> ALWAYS_NULL
  remittance.unstructured_info AS remittance_art9_redacted
FROM `data-days-demo.raw_bank.raw_sepa_payments_pubsub_stream`
WHERE header.end_to_end_id IS NOT NULL
  AND (
    debtor.customer_id = 'CUST00002026'      -- Témoin Lucas Martin (inclut achat Pharmacie)
    OR creditor.agent_bic = 'REVOLT21XXX'    -- Virements instantanés vers néobanque
  )
ORDER BY
  debtor.customer_id = 'CUST00002026' DESC,
  header.end_to_end_id
LIMIT 5;
