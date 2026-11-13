import { DemoId, DemoScenario } from '../types';

export const DEMO_SCENARIOS: Record<DemoId, DemoScenario> = {
  demo1: {
    id: 'demo1',
    shortName: 'Demo 1',
    conversationTitle: 'Agrégation Couche RAW Zero-Copy & Init dbt',
    projectFolder: 'data-days-demo',
    gitBranch: 'main',
    greetingName: 'Clément',
    modelLabel: 'Gemini 4 - Carbon',
    turns: [
      {
        id: 'd1-t1',
        chipLabel: '1. Explorer les silos & fédérer AWS S3',
        prompt:
          "Peux-tu explorer les silos sources de la banque sur data-days-demo (europe-west1) et connecter sans copie le SaaS CRM hébergé sur AWS S3 / Glue ?",
        workedDurationLabel: 'Worked for 5s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "L'inspection des buckets GCS et la création du lien Borderless Lakehouse vers AWS (`s3://hexagone-crm-iceberg`) sont en cours sur `data-days-demo`. Je vous confirme dès que la fédération est active.",
        taskFinishedLabel: 'Borderless Lakehouse AWS S3 federation finished',
        leadConfirmation:
          "La fédération sans copie du silo CRM & Call Center AWS (`eu-west-1`) et l'inventaire Couche 0 sont en ligne dans",
        leadLink: {
          text: 'bigquery.cloud.google.com/dataset/data-days-demo:raw_bank',
          url: 'https://console.cloud.google.com/bigquery?project=data-days-demo',
        },
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: 'Fédération Borderless Lakehouse vers AWS S3 / Glue',
            chips: [
              { kind: 'sql', label: '01_omni_aws_crm.sql' },
              { kind: 'bq', label: 'ext_aws_crm_customers' },
            ],
            bullets: [
              "Connexion directe via BigQuery Omni (`aws-eu-west-1-crm-conn`) aux tables Iceberg distantes sans dupliquer un seul octet (`0 Go` copié) : `80 000` clients répartis sur `8` régions / `450` agences (`+15 000` ouvertures récentes, `0` clôture) et `320 000` notes de RDV & verbatims d'appels.",
            ],
          },
          {
            title: 'Inventaire automatique des 4 autres silos sur GCS & Pub/Sub',
            chips: [{ kind: 'yml', label: 'silos_inventory.yaml' }],
            bullets: [
              "Détection dans `gs://data-days-demo-landing` du lot batch Mainframe fixe `CFONB 120` accompagné de son copybook `copybook_comptes.cpy` (`5,5 M` de lignes), de l'export Finance SAP/PCEC & ALM (`1,2 M` d'écritures), du flux paiements ISO 20022 `pacs.008` (`6,2 M` d'événements) et de `250` contrats promotionnels PDF.",
            ],
          },
        ],
        traces: [
          {
            id: 't1-1',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'discover-assets/SKILL.md',
            lineRange: '#L1-68',
            durationMs: 550,
          },
          {
            id: 't1-2',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'federate-lakehouse-catalog/SKILL.md',
            lineRange: '#L1-94',
            durationMs: 550,
          },
          {
            id: 't1-3',
            action: 'ran',
            commandSummary: 'inspect GCS landing buckets & AWS Glue catalog crm_callcenter_db in eu-west-1',
            durationMs: 750,
          },
          {
            id: 't1-4',
            action: 'analyzed',
            icon: 'md',
            fileName: 'DESIGN_AND_CONTEXT.md',
            lineRange: '#L22-74',
            durationMs: 500,
          },
          {
            id: 't1-5',
            action: 'edited',
            icon: 'sql',
            fileName: '01_omni_aws_crm.sql',
            added: 34,
            removed: 0,
            durationMs: 650,
          },
          {
            id: 't1-6',
            action: 'edited',
            icon: 'yml',
            fileName: 'silos_inventory.yaml',
            added: 22,
            removed: 0,
            durationMs: 500,
          },
          {
            id: 't1-7',
            action: 'ran',
            commandSummary: 'federate AWS S3 Iceberg tables into data-days-demo.raw_bank (europe-west1)',
            durationMs: 800,
          },
        ],
        filesChanged: [
          {
            path: '01_demo1_raw_aggregation/sql/01_omni_aws_crm.sql',
            language: 'sql',
            badge: 'SQL',
            added: 34,
            removed: 0,
            content: `-- Fédération Borderless Lakehouse vers AWS S3 Iceberg (Zéro copie)
CREATE SCHEMA IF NOT EXISTS \`data-days-demo.raw_bank\`
OPTIONS (location = 'europe-west1');

CREATE OR REPLACE EXTERNAL TABLE \`data-days-demo.raw_bank.ext_aws_crm_customers\`
WITH CONNECTION \`aws-eu-west-1.aws-eu-west-1-crm-conn\`
OPTIONS (
  format = 'ICEBERG',
  uris = ['s3://hexagone-crm-iceberg/crm_callcenter_db/customers/metadata/v1.metadata.json']
);

CREATE OR REPLACE EXTERNAL TABLE \`data-days-demo.raw_bank.ext_aws_crm_interactions\`
WITH CONNECTION \`aws-eu-west-1.aws-eu-west-1-crm-conn\`
OPTIONS (
  format = 'ICEBERG',
  uris = ['s3://hexagone-crm-iceberg/crm_callcenter_db/interactions/metadata/v1.metadata.json']
);`,
          },
          {
            path: '01_demo1_raw_aggregation/silos_inventory.yaml',
            language: 'yaml',
            badge: 'YML',
            added: 22,
            removed: 0,
            content: `project: data-days-demo
region: europe-west1
discovered_silos:
  - aws_s3_glue_crm: 80000 customers, 320000 interactions (federated)
  - mainframe_cfonb_120: 5500000 records (copybook_comptes.cpy)
  - sepa_instant_pacs008: 6200000 events
  - finance_sap_pcec_alm: 1200000 journal entries
  - branch_promo_pdfs: 250 PDF files on GCS`,
          },
        ],
        terminalLogs: [
          '$ bq --location=europe-west1 show --connection aws-eu-west-1.aws-eu-west-1-crm-conn',
          'Connection aws-eu-west-1-crm-conn verified (IAM role arn:aws:iam::74829104:role/bq-omni-read).',
          '$ bq query --project_id=data-days-demo --nouse_legacy_sql < 01_omni_aws_crm.sql',
          'Created data-days-demo.raw_bank.ext_aws_crm_customers [80,000 rows federated]',
          'Created data-days-demo.raw_bank.ext_aws_crm_interactions [320,000 rows federated]',
        ],
        subagents: [
          { id: 'sa-1', role: 'AWS Lakehouse Federator', skill: 'federate-lakehouse-catalog', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-1', command: 'bq query 01_omni_aws_crm.sql', target: 'data-days-demo.raw_bank', duration: '1.4s' },
        ],
      },
      {
        id: 'd1-t2',
        chipLabel: '2. Tables Iceberg RAW & Object Table PDF',
        prompt:
          "Décode maintenant le batch Mainframe CFONB 120 via le copybook .cpy, expose les flux paiements ISO 20022 et SAP/ALM en tables BigLake Iceberg managées dans raw_bank, et crée une Object Table sur les 250 PDF promotionnels.",
        workedDurationLabel: 'Worked for 6s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Le décodage du copybook Mainframe et le provisionnement des tables BigLake Iceberg sur `gs://data-days-demo-landing/iceberg` sont lancés. Je vous préviens dès la fin de l'indexation des PDF.",
        taskFinishedLabel: 'BigLake Iceberg tables & GCS Object Table provisioned',
        leadConfirmation:
          "L'ensemble des silos structurés et non structurés est désormais exposé dans `data-days-demo.raw_bank` sur",
        leadLink: {
          text: 'bigquery.cloud.google.com/dataset/data-days-demo:raw_bank',
          url: 'https://console.cloud.google.com/bigquery?project=data-days-demo',
        },
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: 'Tables BigLake Iceberg hébergées (Mainframe, Paiements & Finance)',
            chips: [
              { kind: 'sql', label: '02_raw_iceberg_tables.sql' },
              { kind: 'bq', label: 'raw_sepa_payments' },
            ],
            bullets: [
              "Création au format ouvert `ICEBERG` managé sur `europe-west1` de `raw_cfonb_balances` (`95 000` comptes / `5,5 M` mouvements décodés depuis le `.cpy`), `raw_sepa_payments` (`6,2 M` d'événements `pacs.008` partitionnés par date) et `raw_sap_gl_alm` (`1,2 M` de lignes comptables).",
            ],
          },
          {
            title: 'Object Table GCS pour les contrats agences non structurés',
            chips: [
              { kind: 'sql', label: '03_object_table_pdf.sql' },
              { kind: 'bq', label: 'raw_promo_contracts_pdf' },
            ],
            bullets: [
              "Exposition directe des `250` avenants promotionnels PDF (`gs://data-days-demo-contracts-pdf/promos_2026/*.pdf`) dans BigQuery sans pipeline d'extraction préalable.",
            ],
          },
        ],
        traces: [
          {
            id: 't2-1',
            action: 'analyzed',
            icon: 'cpy',
            fileName: 'copybook_comptes.cpy',
            lineRange: '#L1-48',
            durationMs: 550,
          },
          {
            id: 't2-2',
            action: 'ran',
            commandSummary: 'sample ISO 20022 pacs.008 events & SAP PCEC schema in gs://data-days-demo-landing',
            durationMs: 700,
          },
          {
            id: 't2-3',
            action: 'edited',
            icon: 'sql',
            fileName: '02_raw_iceberg_tables.sql',
            added: 58,
            removed: 0,
            durationMs: 650,
          },
          {
            id: 't2-4',
            action: 'edited',
            icon: 'sql',
            fileName: '03_object_table_pdf.sql',
            added: 14,
            removed: 0,
            durationMs: 500,
          },
          {
            id: 't2-5',
            action: 'ran',
            commandSummary: 'create managed BigLake Iceberg tables & index 250 PDF objects in data-days-demo.raw_bank',
            durationMs: 850,
          },
        ],
        filesChanged: [
          {
            path: '01_demo1_raw_aggregation/sql/02_raw_iceberg_tables.sql',
            language: 'sql',
            badge: 'SQL',
            added: 58,
            removed: 0,
            content: `-- Tables BigLake Iceberg managées sur GCS (europe-west1)
CREATE OR REPLACE TABLE \`data-days-demo.raw_bank.raw_cfonb_balances\` (
  record_code STRING,
  bank_code STRING,
  branch_code_raw STRING,
  account_id STRING,
  value_date_raw STRING,
  amount_cents INT64,
  sens_code STRING,
  raw_cfonb_line STRING
)
CLUSTER BY account_id
WITH CONNECTION \`data-days-demo.europe-west1.biglake-gcs-conn\`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://data-days-demo-landing/iceberg/raw_cfonb_balances'
);

CREATE OR REPLACE TABLE \`data-days-demo.raw_bank.raw_sepa_payments\` (
  event_id STRING,
  end_to_end_id STRING,
  execution_ts TIMESTAMP,
  debtor_account_id STRING,
  creditor_bic STRING,
  tx_status STRING,
  amount_eur NUMERIC(15, 2),
  channel STRING
)
PARTITION BY DATE(execution_ts)
CLUSTER BY tx_status, creditor_bic
WITH CONNECTION \`data-days-demo.europe-west1.biglake-gcs-conn\`
OPTIONS (
  file_format = 'PARQUET',
  table_format = 'ICEBERG',
  storage_uri = 'gs://data-days-demo-landing/iceberg/raw_sepa_payments'
);`,
          },
          {
            path: '01_demo1_raw_aggregation/sql/03_object_table_pdf.sql',
            language: 'sql',
            badge: 'SQL',
            added: 14,
            removed: 0,
            content: `-- Exposition directe des 250 contrats et avenants promotionnels PDF
CREATE OR REPLACE EXTERNAL TABLE \`data-days-demo.raw_bank.raw_promo_contracts_pdf\`
WITH CONNECTION \`data-days-demo.europe-west1.biglake-gcs-conn\`
OPTIONS (
  object_metadata = 'SIMPLE',
  uris = ['gs://data-days-demo-contracts-pdf/promos_2026/*.pdf']
);`,
          },
        ],
        terminalLogs: [
          '$ bq query --project_id=data-days-demo < 02_raw_iceberg_tables.sql',
          'Table data-days-demo:raw_bank.raw_cfonb_balances (ICEBERG) loaded: 5,500,000 rows.',
          'Table data-days-demo:raw_bank.raw_sepa_payments (ICEBERG) loaded: 6,200,000 rows.',
          'Table data-days-demo:raw_bank.raw_sap_gl_alm (ICEBERG) loaded: 1,200,000 rows.',
          '$ bq query --project_id=data-days-demo < 03_object_table_pdf.sql',
          'Object Table raw_promo_contracts_pdf registered: 250 PDF objects indexed.',
        ],
        subagents: [
          { id: 'sa-2', role: 'Mainframe CFONB Copybook Parser', skill: 'discover-assets', status: 'completed' },
          { id: 'sa-3', role: 'BigLake Object Table Builder', skill: 'federate-lakehouse-catalog', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-2', command: 'bq query 02_raw_iceberg_tables.sql', target: 'raw_bank (Iceberg)', duration: '2.1s' },
          { id: 'bg-3', command: 'bq query 03_object_table_pdf.sql', target: '250 PDF on GCS', duration: '0.8s' },
        ],
      },
      {
        id: 'd1-t3',
        chipLabel: '3. Initialiser dbt & doc technique KC',
        prompt:
          "Initialise la structure industrielle dbt sur raw_bank et publie la documentation technique initiale dans Knowledge Catalog.",
        workedDurationLabel: 'Worked for 5s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "La génération du projet `dbt` (`hexagone_bank_lakehouse`) et la synchronisation des métadonnées techniques vers Knowledge Catalog sont en cours.",
        taskFinishedLabel: 'dbt staging & Knowledge Catalog technical sync finished',
        leadConfirmation:
          "Le socle `dbt` est compilé et les fiches techniques des tables `RAW` sont publiées dans",
        leadLink: {
          text: 'console.cloud.google.com/dataplex/search?project=data-days-demo',
          url: 'https://console.cloud.google.com/dataplex?project=data-days-demo',
        },
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: 'Initialisation du projet industriel dbt',
            chips: [
              { kind: 'yml', label: 'dbt_project.yml' },
              { kind: 'yml', label: '_raw_sources.yml' },
            ],
            bullets: [
              "Configuration des couches `staging` (`raw_bank`) et `silver` (`silver_bank`) avec persistance automatique des descriptions vers BigQuery et Knowledge Catalog.",
            ],
          },
          {
            title: 'Premières alertes remontées par la documentation technique',
            chips: [{ kind: 'kc', label: 'Knowledge Catalog · raw_bank' }],
            bullets: [
              "Le profilage initial signale déjà des doublons sur `end_to_end_id` (`~3,4 %`), des statuts techniques `RJCT` / `PDNG` (`8,1 %`) dans `raw_sepa_payments`, des dates Mainframe `00000000` (`~1,2 %`) dans `raw_cfonb_balances` ainsi que `~650` comptes AWS non réconciliés.",
            ],
          },
        ],
        traces: [
          {
            id: 't3-1',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'dbt-bigquery/SKILL.md',
            lineRange: '#L1-112',
            durationMs: 550,
          },
          {
            id: 't3-2',
            action: 'edited',
            icon: 'yml',
            fileName: 'dbt_project.yml',
            added: 28,
            removed: 0,
            durationMs: 550,
          },
          {
            id: 't3-3',
            action: 'edited',
            icon: 'yml',
            fileName: '_raw_sources.yml',
            added: 36,
            removed: 0,
            durationMs: 600,
          },
          {
            id: 't3-4',
            action: 'ran',
            commandSummary: 'dbt compile --select staging.* & sync technical metadata to Knowledge Catalog',
            durationMs: 850,
          },
        ],
        filesChanged: [
          {
            path: '02_demo2_silver_dbt_dq/dbt_project.yml',
            language: 'yaml',
            badge: 'YML',
            added: 28,
            removed: 0,
            content: `name: 'hexagone_bank_lakehouse'
version: '1.0.0'
config-version: 2

profile: 'data_days_demo_bq'

models:
  hexagone_bank_lakehouse:
    staging:
      +materialized: view
      +dataset: raw_bank
    silver:
      +materialized: table
      +dataset: silver_bank
      +persist_docs:
        relation: true
        columns: true`,
          },
          {
            path: '02_demo2_silver_dbt_dq/models/staging/_raw_sources.yml',
            language: 'yaml',
            badge: 'YML',
            added: 36,
            removed: 0,
            content: `version: 2

sources:
  - name: raw_bank
    database: data-days-demo
    schema: raw_bank
    description: "Couche RAW sans copie : BigLake Iceberg, AWS S3 Omni & Object Tables PDF"
    tables:
      - name: ext_aws_crm_customers
      - name: ext_aws_crm_interactions
      - name: raw_cfonb_balances
      - name: raw_sepa_payments
      - name: raw_sap_gl_alm
      - name: raw_promo_contracts_pdf`,
          },
        ],
        terminalLogs: [
          '$ dbt compile --project-dir 02_demo2_silver_dbt_dq',
          'Found 5 staging models, 6 sources in data-days-demo.raw_bank',
          'Synced technical metadata to Knowledge Catalog (europe-west1) — 3 DQ warnings flagged.',
        ],
        subagents: [
          { id: 'sa-4', role: 'dbt Project Architect', skill: 'dbt-bigquery', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-4', command: 'dbt compile && kc sync-raw', target: 'Knowledge Catalog', duration: '1.9s' },
        ],
        artifact: {
          id: 'art-d1',
          title: 'Architecture RAW Zero-Copy & Alertes Initiales',
          subtitle: 'Synthèse générée par Antigravity · Demo 1',
          markdownSummary: {
            heading: 'Bilan Couche RAW (data-days-demo · europe-west1)',
            metrics: [
              { label: 'Sources unifiées', value: '5 silos', tone: 'positive' },
              { label: 'Copie physique AWS → GCP', value: '0 octet', tone: 'positive' },
              { label: 'Anomalies RAW détectées', value: '3 familles critiques', tone: 'warning' },
            ],
            bullets: [
              'AWS S3 CRM (80k clients, 320k notes) fédéré via BigQuery Omni.',
              'Mainframe CFONB (5,5M), SEPA Instant (6,2M) et SAP/ALM (1,2M) en tables Iceberg managées.',
              '250 contrats promotionnels PDF exposés via Object Table GCS.',
              'Passage requis en Demo 2 : nettoyage dbt SILVER + scans Auto Data Quality.',
            ],
          },
        },
      },
    ],
  },

  demo2: {
    id: 'demo2',
    shortName: 'Demo 2',
    conversationTitle: 'Industrialisation dbt SILVER, Auto DQ & 5 Data Products',
    projectFolder: 'data-days-demo',
    gitBranch: 'feat/silver-data-products',
    greetingName: 'Clément',
    modelLabel: 'Gemini 4 - Carbon',
    turns: [
      {
        id: 'd2-t1',
        chipLabel: '1. Lancer le scan Auto Data Quality RAW',
        prompt:
          "Peux-tu lancer un scan Auto Data Quality complet sur les tables raw_bank et détailler toutes les anomalies avant qu'on construise la couche SILVER ?",
        workedDurationLabel: 'Worked for 5s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Le scan Auto Data Quality Dataplex / BigQuery est en cours d'exécution sur les `13,2 M` d'enregistrements de `data-days-demo.raw_bank`.",
        taskFinishedLabel: 'Auto Data Quality scan on raw_bank finished',
        leadConfirmation:
          "L'audit complet de qualité sur `raw_bank` est disponible dans",
        leadLink: {
          text: 'console.cloud.google.com/dataplex/govern/quality?project=data-days-demo',
          url: 'https://console.cloud.google.com/dataplex?project=data-days-demo',
        },
        sectionHeading: 'Anomalies identifiées dans la couche RAW :',
        items: [
          {
            title: 'Doublons réseau et rejets dans le flux paiements SEPA',
            chips: [
              { kind: 'bq', label: 'raw_sepa_payments' },
              { kind: 'yml', label: 'raw_dq_audit_rules.yaml' },
            ],
            bullets: [
              "`3,4 %` d'événements en doublon sur `end_to_end_id` (`210 800` retries techniques) et `8,1 %` de messages non compensés (`RJCT` / `PDNG`) mélangés aux virements exécutés `ACSC`.",
            ],
          },
          {
            title: 'Dates Mainframe invalides et clés orphelines inter-silos',
            chips: [{ kind: 'bq', label: 'raw_cfonb_balances' }],
            bullets: [
              "`1,2 %` de dates de valeur encodées à `00000000` ou `99999999`, codes agences non normalisés (`'0042'` vs `'42  '`), et `650` comptes ouverts récemment sur AWS S3 pas encore réconciliés dans le batch Mainframe du soir.",
            ],
          },
        ],
        traces: [
          {
            id: 'd2-tr1',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'data-autocleaning/SKILL.md',
            lineRange: '#L1-86',
            durationMs: 550,
          },
          {
            id: 'd2-tr2',
            action: 'analyzed',
            icon: 'yml',
            fileName: '_raw_sources.yml',
            lineRange: '#L1-36',
            durationMs: 450,
          },
          {
            id: 'd2-tr3',
            action: 'ran',
            commandSummary: 'profile uniqueness, date formats & cross-silo keys in data-days-demo.raw_bank',
            durationMs: 850,
          },
          {
            id: 'd2-tr4',
            action: 'edited',
            icon: 'yml',
            fileName: 'raw_dq_audit_rules.yaml',
            added: 32,
            removed: 0,
            durationMs: 650,
          },
        ],
        filesChanged: [
          {
            path: '02_demo2_silver_dbt_dq/dq_scans/raw_dq_audit_rules.yaml',
            language: 'yaml',
            badge: 'YML',
            added: 32,
            removed: 0,
            content: `dataplex_auto_dq:
  project: data-days-demo
  location: europe-west1
  findings:
    raw_sepa_payments:
      duplicate_end_to_end_id_pct: 3.40
      non_settled_status_rjct_pdng_pct: 8.10
    raw_cfonb_balances:
      invalid_date_00000000_99999999_pct: 1.20
      unnormalized_branch_code_rows: 148200
    cross_silo_aws_mainframe:
      orphan_recent_accounts: 650`,
          },
        ],
        terminalLogs: [
          '$ gcloud dataplex datascans run raw-bank-dq-scan --project=data-days-demo --location=europe-west1',
          '[FAIL] raw_sepa_payments.end_to_end_id uniqueness: 96.60% (threshold 100%)',
          '[FAIL] raw_cfonb_balances.value_date_raw valid_date: 98.80% (threshold 100%)',
          '[WARN] cross-silo AWS CRM <-> Mainframe account key match: 650 unmatched J0 accounts',
        ],
        subagents: [
          { id: 'sa-d2-1', role: 'Data Quality Auditor', skill: 'data-autocleaning', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-d2-1', command: 'dataplex datascans run raw-bank-dq', target: 'raw_bank', duration: '2.2s' },
        ],
      },
      {
        id: 'd2-t2',
        chipLabel: '2. Générer les modèles dbt SILVER & tests DQ',
        prompt:
          "Génère les 5 modèles dbt SILVER dans silver_bank pour corriger toutes ces anomalies, extraire les 250 PDF via BigQuery AI et intégrer les tests de qualité schema.yml.",
        workedDurationLabel: 'Worked for 6s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Écriture des 5 transformations SQL `dbt` dans `models/silver/` et du contrat de tests `schema.yml` en cours.",
        taskFinishedLabel: '5 dbt SILVER models & 24 DQ assertions generated',
        leadConfirmation:
          "Les modèles `dbt` de la couche `SILVER` et l'extraction structurée des contrats PDF sont prêts dans `02_demo2_silver_dbt_dq/models/silver`.",
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: 'Dédoublonnage SEPA et normalisation Mainframe',
            chips: [
              { kind: 'sql', label: 'dp_payment_flows.sql' },
              { kind: 'sql', label: 'dp_accounts_balances.sql' },
            ],
            bullets: [
              "Filtrage strict sur `tx_status = 'ACSC'` avec `ROW_NUMBER() OVER (PARTITION BY end_to_end_id)`, correction des dates `00000000`, padding des codes agences sur `5` caractères et réconciliation des `650` comptes récents AWS S3.",
            ],
          },
          {
            title: 'Extraction structurée des 250 PDF et tests automatisés',
            chips: [
              { kind: 'sql', label: 'dp_contracts_promos.sql' },
              { kind: 'yml', label: 'schema.yml' },
            ],
            bullets: [
              "Utilisation de `AI.GENERATE_TABLE` sur `raw_promo_contracts_pdf` pour extraire les taux boostés et primes engagées en agence, couvert par `24` tests `unique`, `not_null` et `accepted_values`.",
            ],
          },
        ],
        traces: [
          {
            id: 'd2-tr5',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'bigquery-ai-ml/SKILL.md',
            lineRange: '#L1-104',
            durationMs: 500,
          },
          {
            id: 'd2-tr6',
            action: 'edited',
            icon: 'sql',
            fileName: 'dp_accounts_balances.sql',
            added: 38,
            removed: 0,
            durationMs: 500,
          },
          {
            id: 'd2-tr7',
            action: 'edited',
            icon: 'sql',
            fileName: 'dp_payment_flows.sql',
            added: 31,
            removed: 0,
            durationMs: 500,
          },
          {
            id: 'd2-tr8',
            action: 'edited',
            icon: 'sql',
            fileName: 'dp_contracts_promos.sql',
            added: 27,
            removed: 0,
            durationMs: 500,
          },
          {
            id: 'd2-tr9',
            action: 'edited',
            icon: 'yml',
            fileName: 'schema.yml',
            added: 44,
            removed: 0,
            durationMs: 550,
          },
          {
            id: 'd2-tr10',
            action: 'ran',
            commandSummary: 'dbt parse --project-dir 02_demo2_silver_dbt_dq',
            durationMs: 650,
          },
        ],
        filesChanged: [
          {
            path: '02_demo2_silver_dbt_dq/models/silver/dp_payment_flows.sql',
            language: 'sql',
            badge: 'SQL',
            added: 31,
            removed: 0,
            content: `{{ config(
    materialized='table',
    partition_by={'field': 'execution_date', 'data_type': 'date'},
    cluster_by=['creditor_bic', 'is_neobank_outflow']
) }}

WITH deduplicated AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY end_to_end_id
      ORDER BY execution_ts DESC
    ) AS rn
  FROM {{ source('raw_bank', 'raw_sepa_payments') }}
)
SELECT
  end_to_end_id,
  DATE(execution_ts) AS execution_date,
  execution_ts,
  debtor_account_id,
  creditor_bic,
  amount_eur,
  creditor_bic IN ('REVOLT21', 'TRBKDEBB', 'N26BDEBB', 'BOUSFRPP') AS is_neobank_outflow
FROM deduplicated
WHERE rn = 1
  AND tx_status = 'ACSC'`,
          },
          {
            path: '02_demo2_silver_dbt_dq/models/silver/schema.yml',
            language: 'yaml',
            badge: 'YML',
            added: 44,
            removed: 0,
            content: `version: 2

models:
  - name: dp_accounts_balances
    description: "Comptes & soldes valorisés J+1 normalisés et réconciliés (95 000 comptes)"
    columns:
      - name: account_id
        tests: [unique, not_null]
      - name: branch_code
        tests: [not_null]
  - name: dp_payment_flows
    description: "Flux paiements SEPA Instant compensés ACSC et dédoublonnés"
    columns:
      - name: end_to_end_id
        tests: [unique, not_null]
  - name: dp_customers_interactions
    description: "80 000 clients, RDV agences & 320 000 verbatims call center (Borderless AWS)"
  - name: dp_finance_gl_alm
    description: "Écritures comptables SAP/PCEC, budget & refinancement trésorerie ALM"
  - name: dp_contracts_promos
    description: "250 contrats & offres promotionnelles PDF extraits par BigQuery AI"`,
          },
        ],
        terminalLogs: [
          '$ dbt parse --project-dir 02_demo2_silver_dbt_dq',
          'Parsed 5 silver models and 24 data quality assertions.',
        ],
        subagents: [
          { id: 'sa-d2-2', role: 'dbt Silver Pipeline Engineer', skill: 'dbt-bigquery', status: 'completed' },
          { id: 'sa-d2-3', role: 'Unstructured PDF Extractor', skill: 'bigquery-ai-ml', status: 'completed' },
        ],
        backgroundTasks: [],
      },
      {
        id: 'd2-t3',
        chipLabel: '3. Exécuter dbt build & publier les 5 Data Products',
        prompt:
          "Lance dbt build sur data-days-demo et publie les 5 Data Products élémentaires dans Knowledge Catalog.",
        workedDurationLabel: 'Worked for 6s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Exécution de `dbt build --select silver.*` sur `data-days-demo` (`europe-west1`) et publication des Data Products dans Knowledge Catalog en cours.",
        taskFinishedLabel: 'dbt build (29/29 PASS) & Knowledge Catalog publication finished',
        leadConfirmation:
          "Les 5 Data Products `SILVER` sont matérialisés à `100 %` de Data Quality et publiés dans",
        leadLink: {
          text: 'console.cloud.google.com/dataplex/dp?project=data-days-demo',
          url: 'https://console.cloud.google.com/dataplex?project=data-days-demo',
        },
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: '5 Data Products élémentaires certifiés techniquement (`100 %` DQ PASS)',
            chips: [
              { kind: 'yml', label: 'silver_data_products.yaml' },
              { kind: 'kc', label: 'Knowledge Catalog' },
            ],
            bullets: [
              "Publication de `dp_accounts_balances`, `dp_payment_flows` (`2 420 000 000 €` de virements SEPA Instant sortants vers néobanques sur 90j, dont `68,0 %` chez les `18-32 ans` entre le 1er et le 5 du mois), `dp_customers_interactions`, `dp_finance_gl_alm` et `dp_contracts_promos`.",
            ],
          },
          {
            title: 'Point de vigilance avant exposition aux agents Finance',
            chips: [{ kind: 'bq', label: 'dp_finance_gl_alm' }],
            bullets: [
              "Les schémas `SILVER` sont désormais 100 % propres techniquement (`0` doublon, `0` NULL), mais ne contiennent pas encore les règles métier implicites du contrôle de gestion CFO.",
            ],
          },
        ],
        traces: [
          {
            id: 'd2-tr11',
            action: 'ran',
            commandSummary: 'dbt build --select silver.* on data-days-demo.silver_bank (29/29 PASS)',
            durationMs: 950,
          },
          {
            id: 'd2-tr12',
            action: 'edited',
            icon: 'yml',
            fileName: 'silver_data_products.yaml',
            added: 29,
            removed: 0,
            durationMs: 600,
          },
          {
            id: 'd2-tr13',
            action: 'ran',
            commandSummary: 'publish 5 certified Data Products to Knowledge Catalog (europe-west1)',
            durationMs: 850,
          },
        ],
        filesChanged: [
          {
            path: '02_demo2_silver_dbt_dq/kc_products/silver_data_products.yaml',
            language: 'yaml',
            badge: 'YML',
            added: 29,
            removed: 0,
            content: `data_products:
  domain: retail_banking_france
  project: data-days-demo
  location: europe-west1
  products:
    - id: dp_accounts_balances
      dq_score: 100.0
    - id: dp_payment_flows
      dq_score: 100.0
    - id: dp_customers_interactions
      dq_score: 100.0
    - id: dp_finance_gl_alm
      dq_score: 100.0
    - id: dp_contracts_promos
      dq_score: 100.0`,
          },
        ],
        terminalLogs: [
          '$ dbt build --select silver.*',
          'PASS=29 WARN=0 ERROR=0 SKIP=0 TOTAL=29 [3.4s]',
          '$ kcmd publish-products --file kc_products/silver_data_products.yaml',
          'Published 5 Data Products to Knowledge Catalog (status: CERTIFIED_DQ).',
        ],
        subagents: [
          { id: 'sa-d2-4', role: 'Knowledge Catalog Publisher', skill: 'dbt-bigquery', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-d2-2', command: 'dbt build --select silver.*', target: 'data-days-demo.silver_bank', duration: '3.4s' },
        ],
        artifact: {
          id: 'art-d2',
          title: 'Catalogue des 5 Data Products SILVER',
          subtitle: 'Certifiés 100 % Auto Data Quality · Demo 2',
          markdownSummary: {
            heading: '5 Data Products opérationnels dans silver_bank',
            metrics: [
              { label: 'dp_accounts_balances', value: '95 000 comptes', tone: 'positive' },
              { label: 'dp_payment_flows', value: '5,49 M flux ACSC', tone: 'positive' },
              { label: 'dp_contracts_promos', value: '250 PDF structurés', tone: 'positive' },
            ],
            bullets: [
              '210 800 doublons techniques et 502 200 statuts RJCT/PDNG purgés.',
              '66 000 dates CFONB corrompues corrigées et 650 comptes AWS réconciliés.',
              'Prêt pour le branchement du BQ Agent Finance dans Gemini Enterprise.',
            ],
          },
        },
      },
    ],
  },

  demo3: {
    id: 'demo3',
    shortName: 'Demo 3',
    conversationTitle: 'Sémantique Knowledge Catalog, Vidéos Métier & Vérité CFO',
    projectFolder: 'data-days-demo',
    gitBranch: 'feat/kc-cfo-semantics',
    greetingName: 'Clément',
    modelLabel: 'Gemini 4 - Carbon',
    turns: [
      {
        id: 'd3-t1',
        chipLabel: '1. Auditer le faux résultat (+42,80 M€) & ingérer vidéos .mp4',
        prompt:
          "Pourquoi le BQ Agent sur silver_bank annonce +42,80 M€ de hausse de PNB au lieu d'une baisse ? Ingère les catalogues legacy et les 2 vidéos d'interviews métier (.mp4) pour extraire les vraies règles comptables.",
        workedDurationLabel: 'Worked for 6s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Analyse comparative de la requête SQL naïve (`+42,80 M€`), des exports legacy (`collibra_export_2021.csv`) et transcription multimodale des 2 interviews `.mp4` en cours.",
        taskFinishedLabel: 'Legacy glossaries & multimodal video extraction finished',
        leadConfirmation:
          "L'origine de l'écart sémantique est identifiée et les règles certifiées du Comité ALM ont été extraites dans `03_demo3_kc_semantics_cfo/bundle`.",
        sectionHeading: 'Ce qui a été identifié et extrait :',
        items: [
          {
            title: 'Explication du faux résultat `+42,80 M€` sur `dp_finance_gl_alm`',
            chips: [{ kind: 'yml', label: 'collibra_export_2021.csv' }],
            bullets: [
              "Sans contexte métier, le SQL naïf additionne `gross_amount_eur` sans appliquer le code sens comptable `sens_dc` (`D` / `C`), inclut les comptes de liaison internes `58*` (compte-à-livret) et ignore les engagements hors-bilan.",
            ],
          },
          {
            title: 'Extraction multimodale des 2 vidéos d’experts métier',
            chips: [
              { kind: 'mp4', label: 'interview_directeur_alm.mp4' },
              { kind: 'mp4', label: 'interview_pilotage_reseau.mp4' },
            ],
            bullets: [
              "Formalisation en Open Knowledge Format (`net_interest_margin_gap.md`) des 4 règles impératives : signe Débit/Crédit, exclusion des comptes `58%`, imputation du refinancement €STR à `398 bps` sur les `2,42 Md€` évaporés (`-24,12 M€`) et déduction des primes/taux boostés des `250` avenants PDF (`-14,30 M€`).",
            ],
          },
        ],
        traces: [
          {
            id: 'd3-tr1',
            action: 'analyzed',
            icon: 'dak',
            fileName: 'curate-context/SKILL.md',
            lineRange: '#L1-98',
            durationMs: 500,
          },
          {
            id: 'd3-tr2',
            action: 'analyzed',
            icon: 'csv',
            fileName: 'collibra_export_2021.csv',
            lineRange: '#L1-145',
            durationMs: 500,
          },
          {
            id: 'd3-tr3',
            action: 'analyzed',
            icon: 'mp4',
            fileName: 'interview_directeur_alm.mp4',
            durationMs: 700,
          },
          {
            id: 'd3-tr4',
            action: 'analyzed',
            icon: 'mp4',
            fileName: 'interview_pilotage_reseau.mp4',
            durationMs: 650,
          },
          {
            id: 'd3-tr5',
            action: 'edited',
            icon: 'md',
            fileName: 'net_interest_margin_gap.md',
            added: 42,
            removed: 0,
            durationMs: 650,
          },
        ],
        filesChanged: [
          {
            path: '03_demo3_kc_semantics_cfo/bundle/metrics/net_interest_margin_gap.md',
            language: 'markdown',
            badge: 'OKF',
            added: 42,
            removed: 0,
            content: `---
kind: metric
id: cfo_pnb_budget_variance_eur
owner: direction_finance_alm
status: certified
tables:
  - data-days-demo.silver_bank.dp_finance_gl_alm
  - data-days-demo.silver_bank.dp_contracts_promos
---
# Écart de Marge Nette d'Intérêt (PNB) vs Budget

## Règle de gestion certifiée (Source : Comité ALM & Contrôle de Gestion)
1. **Signe comptable obligatoire** : pondérer \`gross_amount_eur\` par \`CASE WHEN sens_dc = 'D' THEN -1 ELSE 1 END\`.
2. **Neutralisation intra-groupe** : exclure tous les comptes techniques de liaison \`pcec_account LIKE '58%'\`.
3. **Coût de refinancement ALM (€STR)** : inclure la charge de remplacement des dépôts à vue évaporés (\`-24 120 000,00 €\` sur 90j à 398 bps).
4. **Coût commercial hors-bilan PDF** : déduire \`SUM(committed_promo_cost_eur)\` issu de \`dp_contracts_promos\` (\`-14 300 000,00 €\`).`,
          },
        ],
        terminalLogs: [
          '$ kcmd import-legacy 03_demo3_kc_semantics_cfo/legacy_catalogs/',
          'Detected 4 semantic conflicts between Commercial CRM (2021) and Finance PCEC.',
          '$ python extract_video_knowledge.py --inputs interviews_metier/*.mp4',
          'Extracted 4 mandatory accounting rules -> bundle/metrics/net_interest_margin_gap.md',
        ],
        subagents: [
          { id: 'sa-d3-1', role: 'Multimodal Video Analyst', skill: 'curate-context', status: 'completed' },
          { id: 'sa-d3-2', role: 'Legacy Glossary Reconciler', skill: 'curate-context', status: 'completed' },
        ],
        backgroundTasks: [],
      },
      {
        id: 'd3-t2',
        chipLabel: '2. Publier les 3 glossaires KC & vérifier le PNB (-38,42 M€)',
        prompt:
          "Publie les 3 glossaires métier et le Context Set certifié dans Knowledge Catalog sur data-days-demo, puis vérifie l'écart exact de PNB CFO.",
        workedDurationLabel: 'Worked for 5s',
        workGroupSummary: 'Explored files, ran commands, edited files',
        intermediateMessage:
          "Validation `kcmd` et publication des 3 glossaires métier ainsi que du graphe sémantique dans Knowledge Catalog (`data-days-demo`) en cours.",
        taskFinishedLabel: 'Knowledge Catalog context set & 3 business glossaries published',
        leadConfirmation:
          "L'ancrage sémantique du `BQ Agent` est actif et certifié au centime près dans",
        leadLink: {
          text: 'console.cloud.google.com/dataplex/glossaries?project=data-days-demo',
          url: 'https://console.cloud.google.com/dataplex?project=data-days-demo',
        },
        sectionHeading: 'Ce qui a été mis en place :',
        items: [
          {
            title: 'Publication des 3 glossaires métier et du Context Set OKF',
            chips: [
              { kind: 'kc', label: 'Finance & ALM' },
              { kind: 'kc', label: 'Paiements & Comptes' },
              { kind: 'kc', label: 'Client & Commercial' },
            ],
            bullets: [
              "Rattachement direct des définitions gouvernées aux 5 Data Products `silver_bank` avec `-78 %` de tokens consommés lors de la génération SQL par les agents.",
            ],
          },
          {
            title: 'Vérification de la vérité financière CFO (`-38,42 M€`)',
            chips: [
              { kind: 'sql', label: 'governed_cfo_pnb_variance.sql' },
              { kind: 'bq', label: 'v_cfo_certified_pnb_variance' },
            ],
            bullets: [
              "Passage de `+42 800 000,00 €` (faux résultat naïf) à exactement `-38 420 000,00 €` d'écart net de PNB vs budget (`-24 120 000,00 €` de coût de refinancement €STR ALM + `-14 300 000,00 €` engagés dans les `250` PDF d'agence). Le même `BQ Agent` peut maintenant être ré-interrogé en direct dans Gemini Enterprise.",
            ],
          },
        ],
        traces: [
          {
            id: 'd3-tr6',
            action: 'edited',
            icon: 'sql',
            fileName: 'governed_cfo_pnb_variance.sql',
            added: 27,
            removed: 0,
            durationMs: 600,
          },
          {
            id: 'd3-tr7',
            action: 'ran',
            commandSummary: 'kcmd validate bundle/ && kcmd publish --project data-days-demo',
            durationMs: 850,
          },
          {
            id: 'd3-tr8',
            action: 'ran',
            commandSummary: 'verify certified PNB variance view (-38,420,000.00 EUR) on data-days-demo.gold_bank',
            durationMs: 800,
          },
        ],
        filesChanged: [
          {
            path: '03_demo3_kc_semantics_cfo/sql/governed_cfo_pnb_variance.sql',
            language: 'sql',
            badge: 'SQL',
            added: 27,
            removed: 0,
            content: `-- Vue gouvernée certifiée par Knowledge Catalog (Context Set OKF v0.2)
CREATE OR REPLACE VIEW \`data-days-demo.gold_bank.v_cfo_certified_pnb_variance\` AS
WITH gl_net AS (
  SELECT
    SUM(gross_amount_eur * CASE WHEN sens_dc = 'D' THEN -1 ELSE 1 END) AS net_gl_alm_variance_eur
  FROM \`data-days-demo.silver_bank.dp_finance_gl_alm\`
  WHERE NOT STARTS_WITH(pcec_account, '58') -- Exclusion virements internes
),
pdf_promos AS (
  SELECT
    -SUM(committed_promo_cost_eur) AS pdf_promo_impact_eur
  FROM \`data-days-demo.silver_bank.dp_contracts_promos\`
)
SELECT
  gl_net.net_gl_alm_variance_eur,                       -- -24 120 000.00 € (coût €STR ALM)
  pdf_promos.pdf_promo_impact_eur,                      -- -14 300 000.00 € (250 PDF agences)
  gl_net.net_gl_alm_variance_eur + pdf_promos.pdf_promo_impact_eur AS certified_pnb_variance_eur -- -38 420 000.00 €
FROM gl_net CROSS JOIN pdf_promos;`,
          },
        ],
        terminalLogs: [
          '$ kcmd validate bundle/ && kcmd publish bundle/ --project=data-days-demo',
          'Published 3 glossaries (Finance & ALM, Paiements & Comptes, Client & Commercial).',
          '$ bq query --project_id=data-days-demo "SELECT * FROM gold_bank.v_cfo_certified_pnb_variance"',
          '+-------------------------+----------------------+----------------------------+',
          '| net_gl_alm_variance_eur | pdf_promo_impact_eur | certified_pnb_variance_eur |',
          '+-------------------------+----------------------+----------------------------+',
          '|            -24120000.00 |         -14300000.00 |               -38420000.00 |',
          '+-------------------------+----------------------+----------------------------+',
        ],
        subagents: [
          { id: 'sa-d3-3', role: 'Knowledge Catalog Steward', skill: 'curate-context', status: 'completed' },
        ],
        backgroundTasks: [
          { id: 'bg-d3-1', command: 'kcmd publish bundle/', target: 'Knowledge Catalog (3 glossaires)', duration: '1.7s' },
        ],
        artifact: {
          id: 'art-d3',
          title: 'Réconciliation PNB CFO : Fake vs Certifié KC',
          subtitle: 'Preuve mathématique au centime près · Demo 3',
          markdownSummary: {
            heading: 'Écart PNB Trimestriel (data-days-demo)',
            metrics: [
              { label: 'Fuite dépôts SEPA (90j)', value: '2 420 000 000,00 €', tone: 'warning' },
              { label: 'Coût refinancement €STR', value: '-24 120 000,00 €', tone: 'ruby' },
              { label: 'Engagements 250 PDF', value: '-14 300 000,00 €', tone: 'ruby' },
              { label: 'Écart PNB Net Certifié', value: '-38 420 000,00 €', tone: 'positive' },
            ],
            bullets: [
              '68,0 % de la fuite provient des 18-32 ans entre le 1er et le 5 du mois vers REVOLT21 / TRBKDEBB.',
              'Le BQ Agent ancré sur Knowledge Catalog passe de +42,80 M€ (faux) à -38,42 M€ (exact).',
              'Consommation de tokens divisée par 4,5 grâce au graphe sémantique gouverné.',
            ],
          },
        },
      },
    ],
  },
};
