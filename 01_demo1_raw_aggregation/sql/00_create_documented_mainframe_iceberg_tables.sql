-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
-- Création & Documentation complète (Dataset, Tables BigLake Iceberg & Colonnes)
-- des 4 tables Mainframe Core Banking dans BigQuery (`raw_bank`).
--
-- Variables substituées par `scripts/run_demo1_mainframe_spark_iceberg.sh` :
--   __PROJECT_ID__      (ex: data-days-demo)
--   __LOCATION__        (ex: europe-west1)
--   __DATASET_RAW__     (ex: raw_bank)
--   __CONNECTION_ID__   (ex: biglake-gcs-conn)
--   __BUCKET_LANDING__  (ex: data-days-demo-landing)
-- ==============================================================================

ALTER SCHEMA `__PROJECT_ID__.__DATASET_RAW__`
SET OPTIONS (
  description = "Couche RAW multi-silos de Banque Hexagone : tables BigLake Managed Iceberg Mainframe z/OS décodées par Dataproc Serverless Spark (EBCDIC CP500 + COMP-3 & CFONB 120 multi-lignes), fédération zéro-copie AWS S3 (BigQuery Omni), flux temps réel Pub/Sub ISO 20022 (pacs.008) et Object Tables PDF. Conserve volontairement les anomalies de contenu métier brutes pour l'audit Auto Data Quality et la couche dbt SILVER."
);

-- ------------------------------------------------------------------------------
-- 1. Table BigLake Managed Iceberg : cbk_customers_ref (79 350 clients Mainframe)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET_RAW__.cbk_customers_ref` (
  customer_id STRING OPTIONS (
    description = "Identifiant unique client Mainframe z/OS (CBK-CUST-ID, octets 001-012, ex: CUST00002026). Décodé depuis EBCDIC CP500."
  ),
  code_agence_raw STRING OPTIONS (
    description = "Code agence de rattachement sur 4 caractères (CBK-CODE-AGENCE, octets 013-016) conservé brut sans normalisation ('0042' mais aussi '42  ' ou '    ')."
  ),
  code_guichet_raw STRING OPTIONS (
    description = "Code guichet interbancaire sur 5 caractères (CBK-CODE-GUICHET, octets 017-021) conservé brut sans normalisation ('00042' vs '42   ' ou '     ')."
  ),
  region_code STRING OPTIONS (
    description = "Code direction régionale Banque Hexagone (CBK-CODE-REGION, octets 022-025 : REG1 à REG8)."
  ),
  birth_date_raw STRING OPTIONS (
    description = "Date de naissance brute au format Mainframe AAAAMMJJ (CBK-DATE-NAISSANCE, octets 026-033)."
  ),
  age_years INT64 OPTIONS (
    description = "Âge révolu au batch J-1 décodé depuis 2 octets binaires Packed Decimal PIC S9(03) COMP-3 (CBK-AGE-COMP3, octets 034-035)."
  ),
  segment_clientele STRING OPTIONS (
    description = "Segment commercial Mainframe (CBK-SEG-CLIENTELE, octets 036-047 : JEUNE_ACTIF, MASS_MARKET, AFFLUENT, PATRIMONIAL)."
  ),
  onboarding_date_raw STRING OPTIONS (
    description = "Date d'entrée en relation au format AAAAMMJJ (CBK-DATE-ENTREE-REL, octets 048-055)."
  ),
  closure_date_raw STRING OPTIONS (
    description = "Date de clôture de la relation client au format AAAAMMJJ (CBK-DATE-CLOTURE-REL, octets 056-063 ; '00000000' si dossier actif)."
  ),
  dossier_status STRING OPTIONS (
    description = "Statut administratif du dossier tiers (CBK-STATUT-DOSSIER, octets 064-069 : ACTIF)."
  ),
  last_name STRING OPTIONS (
    description = "Nom patronymique du client décodé depuis EBCDIC CP500 (CBK-NOM-PATRONYMIQUE, octets 070-095)."
  ),
  first_name STRING OPTIONS (
    description = "Prénom usuel du client décodé depuis EBCDIC CP500 (CBK-PRENOM-USUEL, octets 096-115)."
  ),
  csp_code STRING OPTIONS (
    description = "Code catégorie socio-professionnelle interne (CBK-CSP-CODE, octets 116-125 : CADRE_TECH, INGENIEUR, ETUDIANT, EMPLOYE, LIBERAL, RETRAITE, etc.)."
  ),
  batch_date_raw STRING OPTIONS (
    description = "Date d'arrêté du traitement batch Mainframe J-1 au format AAAAMMJJ (CBK-DATE-MAJ-BATCH, octets 126-133)."
  ),
  _source_file STRING OPTIONS (
    description = "URI Cloud Storage du fichier binaire Mainframe .ebcdic source."
  ),
  _ingest_ts TIMESTAMP OPTIONS (
    description = "Horodatage UTC de décodage et d'écriture par le job Dataproc Serverless Spark."
  )
)
CLUSTER BY region_code, segment_clientele
WITH CONNECTION `__PROJECT_ID__.__LOCATION__.__CONNECTION_ID__`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://__BUCKET_LANDING__/iceberg/__DATASET_RAW__/cbk_customers_ref',
  description = "Référentiel signalétique clients Core Banking Mainframe J-1 (79 350 clients décodés par Spark depuis CBK_CUSTOMERS_REF_20261112.ebcdic en RECFM=FB LRECL=140 EBCDIC CP500 + COMP-3). N'inclut pas les 650 clients récents créés en agence sur AWS S3 après le cut-off batch."
);

-- ------------------------------------------------------------------------------
-- 2. Table BigLake Managed Iceberg : cbk_accounts_master (94 350 comptes)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET_RAW__.cbk_accounts_master` (
  account_id STRING OPTIONS (
    description = "Identifiant interne unique du compte (CBK-ACC-ID, octets 001-011, ex: ACC00002026)."
  ),
  num_compte_11 STRING OPTIONS (
    description = "Numéro de compte RIB sur 11 caractères (CBK-NUM-COMPTE-11, octets 012-022). Clé de jointure avec les relevés CFONB 120."
  ),
  customer_id STRING OPTIONS (
    description = "Identifiant du client titulaire (CBK-CUST-ID, octets 023-034 -> cbk_customers_ref.customer_id)."
  ),
  bank_code STRING OPTIONS (
    description = "Code établissement interbancaire Banque Hexagone (CBK-CODE-BANQUE, octets 035-039 : '30002')."
  ),
  code_agence_raw STRING OPTIONS (
    description = "Code agence sur 4 caractères conservé brut sans normalisation (CBK-CODE-AGENCE, octets 040-043 : '0042' vs '42  ' / '    ')."
  ),
  code_guichet_raw STRING OPTIONS (
    description = "Code guichet RIB sur 5 caractères conservé brut sans normalisation (CBK-CODE-GUICHET, octets 044-048 : '00042' vs '42   ' / '     ')."
  ),
  cle_rib STRING OPTIONS (
    description = "Clé de contrôle RIB modulo 97 sur 2 chiffres (CBK-CLE-RIB, octets 049-050)."
  ),
  iban STRING OPTIONS (
    description = "IBAN français ISO 13616 complet sur 27 caractères (CBK-IBAN-FR27, octets 051-077)."
  ),
  account_type STRING OPTIONS (
    description = "Nature du produit bancaire (CBK-TYPE-COMPTE, octets 078-087 : CC_CHQ dépôt à vue, LIVRET_A, LDDS, LIV_MAISON)."
  ),
  currency_iso STRING OPTIONS (
    description = "Code devise ISO de tenue du compte (CBK-DEVISE-ISO, octets 088-090 : EUR)."
  ),
  opening_date_raw STRING OPTIONS (
    description = "Date d'ouverture du compte au format AAAAMMJJ (CBK-DATE-OUVERTURE, octets 091-098)."
  ),
  closure_date_raw STRING OPTIONS (
    description = "Date de clôture du compte au format AAAAMMJJ (CBK-DATE-CLOTURE, octets 099-106 ; '00000000' sur 100 % des comptes ouverts)."
  ),
  account_status STRING OPTIONS (
    description = "Statut opérationnel du compte (CBK-STATUT-COMPTE, octets 107-112 : OUVERT)."
  ),
  rate_bps INT64 OPTIONS (
    description = "Taux nominal de rémunération en points de base décodé depuis 3 octets binaires PIC S9(05) COMP-3 (CBK-TAUX-REMUN-BPS, octets 113-115)."
  ),
  solde_veille_cents INT64 OPTIONS (
    description = "Solde comptable veille J-1 en centimes signés, décodé depuis 8 octets binaires PIC S9(13)V99 COMP-3 (CBK-SOLDE-VEILLE-COMP3, octets 116-123)."
  ),
  solde_veille_eur NUMERIC OPTIONS (
    description = "Solde comptable veille J-1 converti en euros exacts (solde_veille_cents / 100), réconcilié au centime près avec l'arrêté CFONB '07'."
  ),
  last_movement_date_raw STRING OPTIONS (
    description = "Date du dernier mouvement comptabilisé au format AAAAMMJJ (CBK-DATE-DERNIER-MVT, octets 124-131)."
  ),
  product_label STRING OPTIONS (
    description = "Libellé commercial du compte ou livret (CBK-LIBELLE-PRODUIT, octets 132-150)."
  ),
  _source_file STRING OPTIONS (
    description = "URI Cloud Storage du fichier binaire Mainframe .ebcdic source."
  ),
  _ingest_ts TIMESTAMP OPTIONS (
    description = "Horodatage UTC de décodage et d'écriture par le job Dataproc Serverless Spark."
  )
)
CLUSTER BY account_type, customer_id
WITH CONNECTION `__PROJECT_ID__.__LOCATION__.__CONNECTION_ID__`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://__BUCKET_LANDING__/iceberg/__DATASET_RAW__/cbk_accounts_master',
  description = "Référentiel maître des comptes courants et livrets Mainframe z/OS (94 350 comptes décodés depuis CBK_ACCOUNTS_MSTR_20261112.ebcdic en RECFM=FB LRECL=150 EBCDIC CP500 + COMP-3 ; 650 comptes récents AWS S3 en attente de réconciliation batch)."
);

-- ------------------------------------------------------------------------------
-- 3. Table BigLake Managed Iceberg : cbk_cfonb_balances (Soldes CFONB '01' & '07')
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET_RAW__.cbk_cfonb_balances` (
  period_ym STRING OPTIONS (
    description = "Période mensuelle comptable au format AAAAMM ('202506' à '202611')."
  ),
  record_type STRING OPTIONS (
    description = "Code enregistrement CFONB 120 (CFONB-CODE-ENR, pos 001-002 : '01' = Ancien solde début période, '07' = Nouveau solde fin période)."
  ),
  bank_code STRING OPTIONS (
    description = "Code banque CFONB (CFONB-CODE-BANQUE, pos 003-007 : '30002')."
  ),
  code_guichet_raw STRING OPTIONS (
    description = "Code guichet agence sur 5 caractères (CFONB-CODE-GUICHET, pos 012-016)."
  ),
  currency_iso STRING OPTIONS (
    description = "Code devise ISO (CFONB-CODE-DEVISE, pos 017-019 : 'EUR')."
  ),
  num_compte_11 STRING OPTIONS (
    description = "Numéro de compte RIB sur 11 caractères (CFONB-NUM-COMPTE, pos 022-032 -> cbk_accounts_master.num_compte_11)."
  ),
  code_afb STRING OPTIONS (
    description = "Code opération interbancaire AFB/CFONB (CFONB-CODE-AFB, pos 033-034 : '60' ancien solde, '62' nouveau solde)."
  ),
  balance_date_raw STRING OPTIONS (
    description = "Date d'arrêté du solde au format AAAAMMJJ (CFONB-DATE-COMPTA, pos 035-042)."
  ),
  libelle STRING OPTIONS (
    description = "Libellé de la ligne de solde CFONB (CFONB-LIBELLE, pos 053-083)."
  ),
  montant_cfonb_raw STRING OPTIONS (
    description = "Montant brut sur 14 caractères au standard signé CFONB (CFONB-MONTANT-SIGNE, pos 095-108 : 13 chiffres + octet signé '{'/'A'..'I' ou '}'/'J'..'R')."
  ),
  signed_balance_cents INT64 OPTIONS (
    description = "Solde comptable signé décodé en centimes (garantit ancien_solde_01 + somme_mouvements_04 = nouveau_solde_07 au centime près)."
  ),
  signed_balance_eur NUMERIC OPTIONS (
    description = "Solde comptable signé décodé en euros (signed_balance_cents / 100)."
  ),
  _source_file STRING OPTIONS (
    description = "Nom du fichier CFONB (.cfonb.gz ou .cfonb) validé RC=0000 par contrôle du trailer 99CFT_TRL."
  ),
  _ingest_ts TIMESTAMP OPTIONS (
    description = "Horodatage UTC d'ingestion Dataproc Serverless Spark."
  )
)
CLUSTER BY period_ym, record_type, num_compte_11
WITH CONNECTION `__PROJECT_ID__.__LOCATION__.__CONNECTION_ID__`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://__BUCKET_LANDING__/iceberg/__DATASET_RAW__/cbk_cfonb_balances',
  description = "Historique sur 18 mois (202506-202611) des anciens soldes ('01') et nouveaux soldes ('07') mensuels à la norme française CFONB 120 octets (2 875 062 lignes issues des lots validés RC=0000, hors dump 202610_RUN01 en ABEND_S0C7)."
);

-- ------------------------------------------------------------------------------
-- 4. Table BigLake Managed Iceberg : cbk_cfonb_movements (5 500 000 écritures '04'+'05')
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET_RAW__.cbk_cfonb_movements` (
  period_ym STRING OPTIONS (
    description = "Mois comptable du mouvement au format AAAAMM ('202506' à '202611')."
  ),
  bank_code STRING OPTIONS (
    description = "Code banque Banque Hexagone (CFONB-CODE-BANQUE, pos 003-007 : '30002')."
  ),
  code_op_interne STRING OPTIONS (
    description = "Code opération interne Core Banking (CFONB-CODE-OP-INTERNE, pos 008-011 : '0420' salaire/revenu, '0430' remboursement, '0580' virement interne compte-à-livret 58*, '0810' virement SEPA Instant sortant, '0650' prélèvement SEPA, '0310' paiement CB)."
  ),
  code_guichet_raw STRING OPTIONS (
    description = "Code guichet sur 5 caractères conservé brut en couche RAW (CFONB-CODE-GUICHET, pos 012-016 : 12,08 % de valeurs non normalisées '42   ' ou blanches '     ')."
  ),
  currency_iso STRING OPTIONS (
    description = "Code devise ISO (CFONB-CODE-DEVISE, pos 017-019 : 'EUR')."
  ),
  num_compte_11 STRING OPTIONS (
    description = "Numéro de compte RIB sur 11 caractères (CFONB-NUM-COMPTE, pos 022-032 -> cbk_accounts_master.num_compte_11)."
  ),
  code_afb STRING OPTIONS (
    description = "Code opération interbancaire AFB/CFONB (CFONB-CODE-AFB, pos 033-034 : '05' virement reçu, '16' virement émis, '08' prélèvement, '28' carte)."
  ),
  date_compta_raw STRING OPTIONS (
    description = "Date de comptabilisation au format AAAAMMJJ (CFONB-DATE-COMPTA, pos 035-042)."
  ),
  code_rejet STRING OPTIONS (
    description = "Code motif rejet interne (CFONB-CODE-REJET, pos 043-044 : '00' = opération compensée ACSC)."
  ),
  date_valeur_raw STRING OPTIONS (
    description = "Date de valeur brute au format AAAAMMJJ conservée sans nettoyage en RAW (CFONB-DATE-VALEUR, pos 045-052 : contient 1,20 % soit 66 000 anomalies '00000000' ou '99999999')."
  ),
  libelle_court STRING OPTIONS (
    description = "Libellé court de l'opération sur 31 caractères (CFONB-LIBELLE, pos 053-083)."
  ),
  num_ecriture STRING OPTIONS (
    description = "Numéro séquentiel d'écriture sur 7 chiffres dans le lot mensuel (CFONB-NUM-ECRITURE, pos 086-092)."
  ),
  montant_cfonb_raw STRING OPTIONS (
    description = "Montant brut sur 14 caractères encodé au standard signé CFONB (CFONB-MONTANT-SIGNE, pos 095-108)."
  ),
  signed_amount_cents INT64 OPTIONS (
    description = "Montant signé décodé en centimes (> 0 crédit, < 0 débit). Sur 90j [20260815..20261112], les virements '0810' vers néobanques totalisent exactement -242 000 000 000 centimes (-2 420 000 000,00 €)."
  ),
  signed_amount_eur NUMERIC OPTIONS (
    description = "Montant signé décodé en euros (signed_amount_cents / 100)."
  ),
  has_complement_05 BOOLEAN OPTIONS (
    description = "Indique si le mouvement '04' était suivi physiquement d'une ligne complémentaire SEPA '05' (TRUE sur virements/prélèvements SEPA, FALSE sur paiements CB '0310')."
  ),
  counterparty_bic STRING OPTIONS (
    description = "Code BIC de la banque contrepartie extrait par Spark de la ligne complémentaire '05' adjacente (CF05-CONTREPARTIE-BIC, pos 048-059 : REVOLT21XXX, TRBKDEBBXXX, NTSBDEB1XXX, BOURFRPPXXX, DEGIRO2AXXX, HEXAFRLPXXX, etc.)."
  ),
  sepa_end_to_end_id STRING OPTIONS (
    description = "Identifiant bout-en-bout SEPA ISO 20022 extrait de la ligne complémentaire '05' (CF05-END-TO-END-ID, pos 060-095), permettant la jointure avec raw_sepa_payments_pubsub_stream."
  ),
  sepa_motif STRING OPTIONS (
    description = "Motif complémentaire SEPA extrait de la ligne '05' (CF05-MOTIF-SEPA, pos 096-120)."
  ),
  _source_file STRING OPTIONS (
    description = "Nom du fichier CFONB (.cfonb.gz ou .cfonb) validé RC=0000 dont provient l'écriture."
  ),
  _line_offset INT64 OPTIONS (
    description = "Numéro de ligne physique du mouvement '04' dans le fichier source ayant servi au rattachement positionnel de la ligne '05'."
  ),
  _ingest_ts TIMESTAMP OPTIONS (
    description = "Horodatage UTC d'ingestion Dataproc Serverless Spark."
  )
)
CLUSTER BY period_ym, code_op_interne, counterparty_bic
WITH CONNECTION `__PROJECT_ID__.__LOCATION__.__CONNECTION_ID__`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://__BUCKET_LANDING__/iceberg/__DATASET_RAW__/cbk_cfonb_movements',
  description = "Mouvements comptables Core Banking valorisés J+1 sur 18 mois (5 500 000 écritures '04' enrichies par Spark des 3 080 073 lignes complémentaires SEPA '05' adjacentes). Conserve les anomalies métier brutes (dates '00000000'/'99999999' et codes guichets non normalisés) pour dbt SILVER."
);
