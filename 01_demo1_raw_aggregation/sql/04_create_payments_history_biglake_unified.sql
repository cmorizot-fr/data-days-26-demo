-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
-- Historique 18 mois du SI Paiements exposé SANS COPIE (BigLake sur Parquet GCS)
-- + vues unifiées Historique ↔ Temps réel Pub/Sub (même schéma 100 % Nested STRUCT).
--
-- Variables substituées par `scripts/run_demo1_payments_history_unified.sh` :
--   __PROJECT_ID__      (ex: data-days-demo)
--   __DATASET_RAW__     (ex: raw_bank)
--   __CONNECTION_ID__   (ex: data-days-demo.europe-west1.biglake-gcs-conn)
--   __BUCKET_LANDING__  (ex: data-days-demo-landing)
--
-- Convention de sens (identique historique & temps réel) : `debtor` = compte Banque Hexagone
-- concerné, `creditor` = contrepartie externe ; `settlement.payment_scheme = *_INBOUND` = crédit reçu.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Table BigLake (zéro copie) : raw_sepa_payments_history (6 200 000 événements, 2025-06-01 → 2026-11-12)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE EXTERNAL TABLE `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_history` (
  header STRUCT<
    schema_version STRING OPTIONS (description = "Version du schéma événementiel ISO 20022 (iso20022.pacs.008.001.08)."),
    event_id STRING OPTIONS (description = "Identifiant technique unitaire de l'événement archivé (PEVT...)."),
    end_to_end_id STRING OPTIONS (description = "Identifiant bout-en-bout SEPA (PmtId.EndToEndId). ~3,4 % de doublons de retry conservés en RAW ; jointure avec les lignes CFONB 05 du Mainframe."),
    execution_ts TIMESTAMP OPTIONS (description = "Horodatage UTC d'exécution de l'opération (2025-06-01 → 2026-11-12, snapshot inclus).")
  > OPTIONS (description = "En-tête d'identification et de traçabilité ISO 20022."),
  settlement STRUCT<
    settlement_method STRING OPTIONS (description = "Méthode de compensation (CLRG_RT1_INST pour SEPA Instant, CLRG_STEP2 sinon)."),
    payment_scheme STRING OPTIONS (description = "Schéma de paiement (SCT_INST, SCT_INBOUND, SEPA_SDD, CARD_CONTACTLESS, CARD_ECOMMERCE). *_INBOUND = crédit reçu par le client."),
    tx_status STRING OPTIONS (description = "Statut ISO 20022 : ACSC, RJCT ou PDNG (~8,1 % non réglés conservés en RAW)."),
    status_reason_code STRING OPTIONS (description = "Code motif ISO 20022 (AM04, AM02, AC04, AB05) ; NULL si ACSC."),
    retry_attempt INT64 OPTIONS (description = "0 = émission initiale, 1 = doublon technique de retry réseau.")
  > OPTIONS (description = "Compensation, schéma et statut de règlement ISO 20022."),
  instructed_amount STRUCT<
    amount_cents INT64 OPTIONS (description = "Montant exact en centimes d'euro."),
    amount_eur NUMERIC OPTIONS (description = "Montant exact en euros (2 décimales)."),
    currency STRING OPTIONS (description = "Devise ISO 4217 (EUR).")
  > OPTIONS (description = "Montant instruit et devise."),
  debtor STRUCT<
    customer_id STRING OPTIONS (description = "Identifiant client Banque Hexagone (référentiel partagé, incl. 650 comptes récents AWS)."),
    account_id STRING OPTIONS (description = "Compte Banque Hexagone concerné par l'opération."),
    full_name STRING OPTIONS (description = "Nom complet du titulaire — Donnée personnelle PII protégée par CLS."),
    iban STRING OPTIONS (description = "IBAN FR du compte Banque Hexagone — Donnée bancaire sensible (masquage partiel CLS)."),
    agent_bic STRING OPTIONS (description = "BIC teneur de compte (HEXAFRLPXXX)."),
    branch_guichet STRING OPTIONS (description = "Code guichet sur 5 chiffres de l'agence de rattachement.")
  > OPTIONS (description = "Compte Banque Hexagone concerné (débité, ou crédité si *_INBOUND)."),
  creditor STRUCT<
    name STRING OPTIONS (description = "Nom de la contrepartie (enseigne, organisme, ou nom civil du titulaire pour un virement vers son compte néobanque) — PII."),
    iban STRING OPTIONS (description = "IBAN de la contrepartie externe (néobanques : IBAN déterministe par client, identique au temps réel) — masquage partiel CLS."),
    agent_bic STRING OPTIONS (description = "BIC de la contrepartie (REVOLT21XXX, TRBKDEBBXXX, NTSBDEB1XXX, BOURFRPPXXX, DEGIRO2AXXX, ...).")
  > OPTIONS (description = "Contrepartie externe de l'opération."),
  remittance STRUCT<
    unstructured_info STRING OPTIONS (description = "Libellé libre aligné sur le Mainframe CFONB (contient des motifs santé / loyer) — champ sensible RGPD Art. 9.")
  > OPTIONS (description = "Motif libre de l'opération.")
)
WITH CONNECTION `__CONNECTION_ID__`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://__BUCKET_LANDING__/RAW/PAYMENTS/sepa_payment_events/*.parquet'],
  description = "Archive historique 18 mois du SI Paiements ISO 20022 (6 200 000 événements, 2025-06-01 → 2026-11-12) exposée sans copie via BigLake sur Parquet GCS. Schéma 100 % Nested STRUCT identique au flux temps réel raw_sepa_payments_pubsub_stream. Conserve 3,4 % de doublons et 8,1 % de RJCT/PDNG."
);

-- ------------------------------------------------------------------------------
-- 2. Table BigLake (zéro copie) : raw_iban_events_history (enrôlements IBAN bénéficiaires)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE EXTERNAL TABLE `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_history` (
  header STRUCT<
    schema_version STRING OPTIONS (description = "Version du contrat d'enrôlement (iban.enrollment.v2)."),
    event_id STRING OPTIONS (description = "Identifiant de l'événement d'enrôlement (suffixe _RETRY = doublon API)."),
    event_ts TIMESTAMP OPTIONS (description = "Horodatage UTC de l'enrôlement (veille du premier virement vers la néobanque)."),
    retry_attempt INT64 OPTIONS (description = "0 = nominal, 1 = doublon technique API mobile.")
  > OPTIONS (description = "En-tête technique de l'enrôlement."),
  account_holder STRUCT<
    customer_id STRING OPTIONS (description = "Identifiant client Banque Hexagone."),
    account_id STRING OPTIONS (description = "Compte courant source."),
    full_name STRING OPTIONS (description = "Nom complet du titulaire — PII protégée par CLS."),
    debtor_iban STRING OPTIONS (description = "IBAN FR du compte source — masquage partiel CLS."),
    branch_guichet STRING OPTIONS (description = "Code guichet de l'agence.")
  > OPTIONS (description = "Titulaire Banque Hexagone ayant ajouté le bénéficiaire."),
  beneficiary STRUCT<
    iban STRING OPTIONS (description = "IBAN externe enregistré (identique aux virements historiques et temps réel) — masquage partiel CLS."),
    agent_bic STRING OPTIONS (description = "BIC de la néobanque bénéficiaire."),
    custom_label STRING OPTIONS (description = "Libellé personnel saisi par le client — PII libre.")
  > OPTIONS (description = "Bénéficiaire externe enregistré."),
  security_context STRUCT<
    channel STRING OPTIONS (description = "Canal digital (déterministe par client)."),
    sca_strong_auth_status STRING OPTIONS (description = "Statut d'authentification forte DSP2."),
    device_ip STRING OPTIONS (description = "Adresse IPv4 du terminal — identifiant en ligne RGPD.")
  > OPTIONS (description = "Contexte de sécurité DSP2.")
)
WITH CONNECTION `__CONNECTION_ID__`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://__BUCKET_LANDING__/RAW/PAYMENTS/iban_beneficiary_events/*.parquet'],
  description = "Historique des enrôlements IBAN bénéficiaires (néobanques) exposé sans copie via BigLake sur Parquet GCS. Schéma identique à raw_iban_events_pubsub_stream."
);

-- ------------------------------------------------------------------------------
-- 3. Vue unifiée Paiements : Historique (BigLake) ∪ Temps réel (Pub/Sub BigQuery Subscription)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_unified`
OPTIONS (
  description = "Flux Paiements ISO 20022 continu : archive 18 mois (≤ 2026-11-12, BigLake) puis temps réel Pub/Sub (> 2026-11-12). Même schéma STRUCT, mêmes contreparties et IBAN ; ingestion_source distingue les deux couches. Le CLS des tables sources s'applique à travers la vue."
) AS
SELECT
  'HISTORY_ARCHIVE' AS ingestion_source,
  CAST(NULL AS STRING) AS subscription_name,
  CAST(NULL AS STRING) AS message_id,
  CAST(NULL AS TIMESTAMP) AS publish_time,
  header, settlement, instructed_amount, debtor, creditor, remittance
FROM `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_history`
UNION ALL
SELECT
  'PUBSUB_LIVE' AS ingestion_source,
  subscription_name,
  message_id,
  publish_time,
  header, settlement, instructed_amount, debtor, creditor, remittance
FROM `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_pubsub_stream`;

-- ------------------------------------------------------------------------------
-- 4. Vue unifiée Enrôlements IBAN : Historique ∪ Temps réel
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_unified`
OPTIONS (
  description = "Enrôlements IBAN bénéficiaires continus : historique (BigLake) puis temps réel Pub/Sub. Un bénéficiaire déjà enrôlé dans l'historique n'est jamais ré-enrôlé en temps réel."
) AS
SELECT
  'HISTORY_ARCHIVE' AS ingestion_source,
  CAST(NULL AS STRING) AS subscription_name,
  CAST(NULL AS STRING) AS message_id,
  CAST(NULL AS TIMESTAMP) AS publish_time,
  header, account_holder, beneficiary, security_context
FROM `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_history`
UNION ALL
SELECT
  'PUBSUB_LIVE' AS ingestion_source,
  subscription_name,
  message_id,
  publish_time,
  header, account_holder, beneficiary, security_context
FROM `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_pubsub_stream`;
