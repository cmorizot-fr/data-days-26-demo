-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 · Étape 4 (Chip 3)
-- Audit Hybride de Données Sensibles (Détecteurs déterministes DLP-like +
-- Profilage sémantique des champs libres) sur les 2 tables 100 % Nested STRUCT :
--   1. `raw_bank.raw_sepa_payments_pubsub_stream`
--   2. `raw_bank.raw_iban_events_pubsub_stream`
--
-- Principe RGPD / ACPR : Aucune valeur brute PII ne quitte BigQuery ; la requête
-- ne retourne à l'agent que les métadonnées agrégées par chemin `STRUCT` feuille.
-- ==============================================================================

WITH payments_profile AS (
  SELECT
    COUNT(*) AS n_rows,
    COUNTIF(REGEXP_CONTAINS(debtor.iban, r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$')) AS debtor_iban_hits,
    COUNTIF(REGEXP_CONTAINS(creditor.iban, r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$')) AS creditor_iban_hits,
    COUNTIF(debtor.full_name IS NOT NULL AND ARRAY_LENGTH(SPLIT(TRIM(debtor.full_name), ' ')) >= 2) AS debtor_name_hits,
    -- Personne physique côté créditeur : virement vers son propre compte néobanque (nom = titulaire)
    COUNTIF(creditor.name IS NOT NULL AND creditor.name = debtor.full_name) AS creditor_person_hits,
    COUNTIF(REGEXP_CONTAINS(UPPER(remittance.unstructured_info), r'(SANTE|CPAM|MUTUELLE|MEDICAL|ORDONNANCE|PHARMACIE|LOYER)')) AS remittance_sensitive_hits
  FROM `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_pubsub_stream`
),
iban_profile AS (
  SELECT
    COUNT(*) AS n_rows,
    COUNTIF(REGEXP_CONTAINS(account_holder.debtor_iban, r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$')) AS holder_iban_hits,
    COUNTIF(REGEXP_CONTAINS(beneficiary.iban, r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$')) AS benef_iban_hits,
    COUNTIF(account_holder.full_name IS NOT NULL AND LENGTH(TRIM(account_holder.full_name)) > 3) AS holder_name_hits,
    COUNTIF(beneficiary.custom_label IS NOT NULL AND LENGTH(TRIM(beneficiary.custom_label)) > 3) AS benef_label_hits,
    COUNTIF(REGEXP_CONTAINS(security_context.device_ip, r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')) AS device_ip_hits
  FROM `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_pubsub_stream`
)
SELECT * FROM (
  SELECT
    'raw_sepa_payments_pubsub_stream' AS table_name,
    'debtor.iban' AS nested_field_path,
    'IBAN_CODE (DLP Deterministic)' AS detected_info_type,
    ROUND(100.0 * debtor_iban_hits / NULLIF(n_rows, 0), 1) AS match_rate_pct,
    'HIGH_FINANCIAL_PII' AS sensitivity_level,
    'PII_IBAN_PARTIAL_MASK (LAST_FOUR_CHARACTERS)' AS recommended_cls_policy
  FROM payments_profile
  UNION ALL
  SELECT
    'raw_sepa_payments_pubsub_stream',
    'creditor.iban',
    'IBAN_CODE (DLP Deterministic)',
    ROUND(100.0 * creditor_iban_hits / NULLIF(n_rows, 0), 1),
    'HIGH_FINANCIAL_PII',
    'PII_IBAN_PARTIAL_MASK (LAST_FOUR_CHARACTERS)'
  FROM payments_profile
  UNION ALL
  SELECT
    'raw_sepa_payments_pubsub_stream',
    'debtor.full_name',
    'PERSON_NAME (Direct Identifier)',
    ROUND(100.0 * debtor_name_hits / NULLIF(n_rows, 0), 1),
    'HIGH_DIRECT_PII',
    'PII_IDENTITY_IP_HASH (SHA256)'
  FROM payments_profile
  UNION ALL
  SELECT
    'raw_sepa_payments_pubsub_stream',
    'creditor.name',
    'PERSON_OR_MERCHANT_NAME (Contextual)',
    ROUND(100.0 * creditor_person_hits / NULLIF(n_rows, 0), 1),
    'HIGH_DIRECT_PII',
    'PII_IDENTITY_IP_HASH (SHA256)'
  FROM payments_profile
  UNION ALL
  SELECT
    'raw_sepa_payments_pubsub_stream',
    'remittance.unstructured_info',
    'MEDICAL_AND_HOUSING_FREETEXT (Semantic)',
    ROUND(100.0 * remittance_sensitive_hits / NULLIF(n_rows, 0), 1),
    'CRITICAL_ART9_GDPR',
    'PII_SENSITIVE_FREETEXT_REDACT (ALWAYS_NULL)'
  FROM payments_profile
  UNION ALL
  SELECT
    'raw_iban_events_pubsub_stream',
    'account_holder.debtor_iban',
    'IBAN_CODE (DLP Deterministic)',
    ROUND(100.0 * holder_iban_hits / NULLIF(n_rows, 0), 1),
    'HIGH_FINANCIAL_PII',
    'PII_IBAN_PARTIAL_MASK (LAST_FOUR_CHARACTERS)'
  FROM iban_profile
  UNION ALL
  SELECT
    'raw_iban_events_pubsub_stream',
    'beneficiary.iban',
    'IBAN_CODE (DLP Deterministic)',
    ROUND(100.0 * benef_iban_hits / NULLIF(n_rows, 0), 1),
    'HIGH_FINANCIAL_PII',
    'PII_IBAN_PARTIAL_MASK (LAST_FOUR_CHARACTERS)'
  FROM iban_profile
  UNION ALL
  SELECT
    'raw_iban_events_pubsub_stream',
    'account_holder.full_name',
    'PERSON_NAME (Direct Identifier)',
    ROUND(100.0 * holder_name_hits / NULLIF(n_rows, 0), 1),
    'HIGH_DIRECT_PII',
    'PII_IDENTITY_IP_HASH (SHA256)'
  FROM iban_profile
  UNION ALL
  SELECT
    'raw_iban_events_pubsub_stream',
    'security_context.device_ip',
    'IP_ADDRESS (GDPR Online Identifier)',
    ROUND(100.0 * device_ip_hits / NULLIF(n_rows, 0), 1),
    'MEDIUM_TECHNICAL_PII',
    'PII_IDENTITY_IP_HASH (SHA256)'
  FROM iban_profile
  UNION ALL
  SELECT
    'raw_iban_events_pubsub_stream',
    'beneficiary.custom_label',
    'PERSONAL_FREETEXT_LABEL (Semantic)',
    ROUND(100.0 * benef_label_hits / NULLIF(n_rows, 0), 1),
    'CRITICAL_FREETEXT_PII',
    'PII_SENSITIVE_FREETEXT_REDACT (ALWAYS_NULL)'
  FROM iban_profile
)
ORDER BY table_name DESC, nested_field_path;
