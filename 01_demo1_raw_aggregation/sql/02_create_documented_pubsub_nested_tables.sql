-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
-- Création & Documentation complète des 2 tables d'historisation temps réel
-- Cloud Pub/Sub -> BigQuery Subscription (`--use-table-schema` + `--write-metadata`)
-- en schéma 100 % Nested (`STRUCT` ISO 20022 `pacs.008` & Ajouts IBAN).
--
-- Variables substituées par `scripts/setup_pubsub_queues.sh` :
--   __PROJECT_ID__      (ex: data-days-demo)
--   __DATASET_RAW__     (ex: raw_bank)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Table Streaming ISO 20022 pacs.008 : raw_sepa_payments_pubsub_stream
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_pubsub_stream`;
CREATE TABLE `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_pubsub_stream` (
  -- Métadonnées techniques d'enveloppe Pub/Sub (--write-metadata)
  subscription_name STRING OPTIONS (
    description = "Nom complet de la BigQuery Subscription Pub/Sub ayant écrit le message (projects/.../subscriptions/sepa-payments-bq-historization-sub)."
  ),
  message_id STRING OPTIONS (
    description = "Identifiant unique attribué par le broker Cloud Pub/Sub lors de la publication."
  ),
  publish_time TIMESTAMP OPTIONS (
    description = "Horodatage UTC de réception par Cloud Pub/Sub (clé de partitionnement journalier)."
  ),
  attributes JSON OPTIONS (
    description = "Attributs de routage Pub/Sub attachés à l'enveloppe (tx_status, payment_scheme, creditor_bic, is_retry)."
  ),

  -- Bloc 1 : En-tête de message ISO 20022 (GrpHdr / PmtId)
  header STRUCT<
    schema_version STRING OPTIONS (
      description = "Version du schéma événementiel ISO 20022 (ex: iso20022.pacs.008.001.08)."
    ),
    event_id STRING OPTIONS (
      description = "Identifiant technique unitaire de l'événement émis par le moteur de paiement."
    ),
    end_to_end_id STRING OPTIONS (
      description = "Identifiant bout-en-bout SEPA (PmtId.EndToEndId). Contient ~3,4 % de doublons techniques en RAW lors des retries réseau."
    ),
    execution_ts TIMESTAMP OPTIONS (
      description = "Horodatage métier d'exécution de l'opération dans le moteur de paiement."
    )
  > OPTIONS (
    description = "En-tête d'identification et de traçabilité ISO 20022 du message de paiement."
  ),

  -- Bloc 2 : Statut de règlement interbancaire (TxInfAndSts)
  settlement STRUCT<
    settlement_method STRING OPTIONS (
      description = "Méthode de compensation interbancaire (CLRG_RT1_INST pour SEPA Instant <10s, CLRG_STEP2 pour standard)."
    ),
    payment_scheme STRING OPTIONS (
      description = "Schéma de paiement (SCT_INST, SCT_INST_INBOUND, CARD_CONTACTLESS, CARD_ECOMMERCE, SEPA_SDD)."
    ),
    tx_status STRING OPTIONS (
      description = "Statut ISO 20022 : ACSC (compensé ~91,9 %), RJCT (rejeté) ou PDNG (en attente) — ~8,1 % non réglés conservés en RAW."
    ),
    status_reason_code STRING OPTIONS (
      description = "Code motif ISO 20022 en cas de rejet ou d'attente (AM04 fonds insuffisants, AC04 compte clos, AB05 timeout, NULL si ACSC)."
    ),
    retry_attempt INT64 OPTIONS (
      description = "Compteur de réémission technique du broker (0 = émission initiale, >=1 = doublon de retry réseau)."
    )
  > OPTIONS (
    description = "Informations de compensation, schéma de paiement et statut technique de règlement ISO 20022."
  ),

  -- Bloc 3 : Montant instruit (IntrBkSttlmAmt)
  instructed_amount STRUCT<
    amount_cents INT64 OPTIONS (
      description = "Montant exact de l'opération exprimé en centimes d'euro (entier signé sans perte de précision)."
    ),
    amount_eur NUMERIC OPTIONS (
      description = "Montant exact de l'opération exprimé en euros (NUMERIC 2 décimales)."
    ),
    currency STRING OPTIONS (
      description = "Code devise ISO 4217 (EUR)."
    )
  > OPTIONS (
    description = "Montant monétaire instruit et devise du transfert."
  ),

  -- Bloc 4 : Donneur d'ordre / Débiteur Banque Hexagone (Dbtr / DbtrAcct / DbtrAgt) — CONTIENT PII
  debtor STRUCT<
    customer_id STRING OPTIONS (
      description = "Identifiant client Banque Hexagone (ex: CUST00002026, inclut les 650 clients récents créés sur AWS S3)."
    ),
    account_id STRING OPTIONS (
      description = "Identifiant interne du compte débité (ex: ACC00002026)."
    ),
    full_name STRING OPTIONS (
      description = "Nom complet patronymique du titulaire débiteur (Dbtr.Nm) — Donnée personnelle PII à protéger via CLS."
    ),
    iban STRING OPTIONS (
      description = "IBAN complet sur 27 caractères du compte débité (DbtrAcct.Id.IBAN) — Donnée bancaire sensible soumise à masquage partiel CLS."
    ),
    agent_bic STRING OPTIONS (
      description = "Code BIC de l'établissement teneur de compte débiteur (HEXAFRLPXXX)."
    ),
    branch_guichet STRING OPTIONS (
      description = "Code guichet interbancaire sur 5 chiffres de l'agence de rattachement (ex: 00042)."
    )
  > OPTIONS (
    description = "Informations d'identité et de compte du client donneur d'ordre (Dbtr)."
  ),

  -- Bloc 5 : Bénéficiaire / Créditeur (Cdtr / CdtrAcct / CdtrAgt) — CONTIENT PII
  creditor STRUCT<
    name STRING OPTIONS (
      description = "Nom du bénéficiaire ou de l'enseigne (Cdtr.Nm, contient le nom civil lors d'un virement vers néobanque) — Donnée PII."
    ),
    iban STRING OPTIONS (
      description = "IBAN du compte bénéficiaire externe (CdtrAcct.Id.IBAN : LT60..., DE89..., FR76...) — Donnée sensible soumise à masquage partiel CLS."
    ),
    agent_bic STRING OPTIONS (
      description = "Code BIC de l'établissement destinataire (ex: REVOLT21XXX, TRBKDEBBXXX, NTSBDEB1XXX, BOURFRPPXXX, DEGIRO2AXXX)."
    )
  > OPTIONS (
    description = "Informations d'identité, d'IBAN et d'établissement BIC du bénéficiaire externe (Cdtr)."
  ),

  -- Bloc 6 : Motif de paiement libre (RmtInf) — CONTIENT TEXTE LIBRE POTENTIELLEMENT SENSIBLE
  remittance STRUCT<
    unstructured_info STRING OPTIONS (
      description = "Libellé libre non structuré du paiement (RmtInf.Ustrd, ex: motif santé, loyer ou transfert épargne) — Champ sensible contextuel."
    )
  > OPTIONS (
    description = "Informations de remise et motif libre accompagnant l'instruction de paiement."
  )
)
PARTITION BY DATE(publish_time)
CLUSTER BY subscription_name
OPTIONS (
  description = "Historisation temps réel sans serveur (BigQuery Subscription --use-table-schema) du topic sepa-payments-pacs008-topic en structure 100 % Nested (STRUCT ISO 20022 pacs.008). Conserve les doublons de retry (~3,4 %) et les statuts RJCT/PDNG (~8,1 %) en zone RAW."
);

-- ------------------------------------------------------------------------------
-- 2. Table Streaming Enrôlement IBAN : raw_iban_events_pubsub_stream
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_pubsub_stream`;
CREATE TABLE `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_pubsub_stream` (
  -- Métadonnées techniques d'enveloppe Pub/Sub (--write-metadata)
  subscription_name STRING OPTIONS (
    description = "Nom complet de la BigQuery Subscription Pub/Sub (projects/.../subscriptions/iban-beneficiary-bq-historization-sub)."
  ),
  message_id STRING OPTIONS (
    description = "Identifiant unique du message attribué par Cloud Pub/Sub."
  ),
  publish_time TIMESTAMP OPTIONS (
    description = "Horodatage UTC de publication dans Cloud Pub/Sub (clé de partitionnement journalier)."
  ),
  attributes JSON OPTIONS (
    description = "Attributs de routage Pub/Sub (beneficiary_bic, channel)."
  ),

  -- Bloc 1 : En-tête technique de l'événement d'enrôlement
  header STRUCT<
    schema_version STRING OPTIONS (
      description = "Version du contrat d'événement mobile/web d'ajout de bénéficiaire (iban.enrollment.v2)."
    ),
    event_id STRING OPTIONS (
      description = "Identifiant unique de l'événement d'ajout de bénéficiaire IBAN."
    ),
    event_ts TIMESTAMP OPTIONS (
      description = "Horodatage UTC de validation de l'ajout du bénéficiaire dans le canal digital."
    ),
    retry_attempt INT64 OPTIONS (
      description = "Compteur de réémission technique API mobile (0 = nominal, >=1 = doublon technique)."
    )
  > OPTIONS (
    description = "En-tête technique et horodatage de l'événement d'enrôlement IBAN."
  ),

  -- Bloc 2 : Titulaire du compte Banque Hexagone — CONTIENT PII
  account_holder STRUCT<
    customer_id STRING OPTIONS (
      description = "Identifiant client Banque Hexagone ayant ajouté le bénéficiaire."
    ),
    account_id STRING OPTIONS (
      description = "Identifiant du compte courant rattaché."
    ),
    full_name STRING OPTIONS (
      description = "Nom complet du client titulaire — Donnée personnelle PII à protéger via CLS."
    ),
    debtor_iban STRING OPTIONS (
      description = "IBAN du compte courant source Banque Hexagone — Donnée sensible soumise à masquage partiel CLS."
    ),
    branch_guichet STRING OPTIONS (
      description = "Code guichet sur 5 chiffres de l'agence du client."
    )
  > OPTIONS (
    description = "Identité et coordonnées bancaires internes du client initiateur."
  ),

  -- Bloc 3 : Coordonnées du bénéficiaire externe ajouté — CONTIENT PII
  beneficiary STRUCT<
    iban STRING OPTIONS (
      description = "IBAN externe nouvellement enregistré par le client — Donnée sensible soumise à masquage partiel CLS."
    ),
    agent_bic STRING OPTIONS (
      description = "Code BIC de la banque ou néobanque du bénéficiaire (ex: REVOLT21XXX, TRBKDEBBXXX)."
    ),
    custom_label STRING OPTIONS (
      description = "Libellé personnel saisi par le client dans l'application mobile (ex: 'Lucas Martin Revolut') — Donnée PII libre."
    )
  > OPTIONS (
    description = "Coordonnées bancaires et libellé personnalisé du bénéficiaire externe enregistré."
  ),

  -- Bloc 4 : Contexte de sécurité & authentification forte DSP2 — CONTIENT PII TECHNIQUE
  security_context STRUCT<
    channel STRING OPTIONS (
      description = "Canal digital d'origine (MOBILE_APP_ANDROID, MOBILE_APP_IOS, WEB_HOMEBANKING)."
    ),
    sca_strong_auth_status STRING OPTIONS (
      description = "Statut d'authentification forte DSP2 (VERIFIED_BIOMETRIC, VERIFIED_PASSKEY)."
    ),
    device_ip STRING OPTIONS (
      description = "Adresse IPv4 du terminal ayant validé l'enrôlement DSP2 — Identifiant technique personnel RGPD."
    )
  > OPTIONS (
    description = "Traces de sécurité DSP2 et empreinte réseau du terminal client."
  )
)
PARTITION BY DATE(publish_time)
CLUSTER BY subscription_name
OPTIONS (
  description = "Historisation temps réel sans serveur (BigQuery Subscription --use-table-schema) du topic iban-beneficiary-events-topic en structure 100 % Nested (STRUCT)."
);
