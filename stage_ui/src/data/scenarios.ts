import { DemoScenario, DemoWorkspace } from '../types';

export const DEMO_WORKSPACES: DemoWorkspace[] = [
  // ============================================================================
  // WORKSPACE DEMO 1 : 01_demo1_raw_aggregation
  // ============================================================================
  {
    id: 'demo1',
    workspaceLabel: 'Demo 1 · Agrégation RAW',
    folderName: '01_demo1_raw_aggregation',
    conversations: [
      {
        id: 'd1-step1',
        demoId: 'demo1',
        shortName: '1. Transfert Mainframe → GCS RAW',
        conversationTitle: 'Transfert Mainframe du mois passé vers GCS RAW',
        projectFolder: '01_demo1_raw_aggregation',
        gitBranch: 'main',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd1-s1-t1',
            chipLabel: '1. Transférer Mainframe mois passé → GCS RAW',
            prompt:
              'Transfere les données mainframe du serveur de fichier pour le mois passé, sur GCS dans la zone RAW.',
            workedDurationLabel: 'Worked for 4s',
            workGroupSummary: 'Checked GCP connection, explored local drop & existing RAW bucket',
            intermediateMessage:
              "J'ai récupéré la connexion GCP active (`data-days-demo` · `europe-west1`), vérifié le bucket existant `gs://data-days-demo-landing/raw/` et inspecté les fichiers du mois passé (`2026-10`) sur le serveur local (`00_data_generator/output/corebanking/`).",
            taskFinishedLabel: 'Local file server & existing GCS RAW bucket inspection finished',
            leadConfirmation:
              "Le bucket `gs://data-days-demo-landing` est bien présent et accessible en `europe-west1` (attention : les maîtres `.ebcdic` sont en binaire continu `RECFM=FB` `EBCDIC CP500 + COMP-3` sans saut de ligne, donc atterrissage brut sur GCS obligatoire avant Spark) sur",
            leadLink: {
              text: 'console.cloud.google.com/storage/browser/data-days-demo-landing/raw',
              url: 'https://console.cloud.google.com/storage/browser?project=data-days-demo',
            },
            sectionHeading: 'Avant de lancer le transfert vers la zone RAW, peux-tu me confirmer ces 3 points :',
            items: [
              {
                title: 'Incident détecté sur le mois passé (`202610`) : double fichier `ABEND` vs `RERUN`',
                bullets: [
                  "Sur le serveur local, octobre 2026 comporte deux fichiers : `CFONB120_MVTS_202610_RUN01.cfonb` interrompu en crash (`STATUS=ABEND_S0C7`, `RC=0012`, `32 Mo`) et `CFONB120_MVTS_202610_RUN02_RERUN.cfonb` complet (`STATUS=OK`, `RC=0000`, `109 Mo`). On transfère les deux dans la zone `RAW` pour conserver une trace d'audit fidèle au CFT Mainframe (et laisser Spark filtrer sur `RC=0000`), ou j'exclus `RUN01` dès la copie ?",
                ],
              },
              {
                title: 'Référentiels maîtres `.ebcdic` & Copybooks COBOL `.cpy` associés',
                bullets: [
                  "Pour permettre le décodage aval vers BigLake Iceberg, j'inclus également les 2 référentiels maîtres binaires (`CBK_CUSTOMERS_REF_20261112.ebcdic`, `CBK_ACCOUNTS_MSTR_20261112.ebcdic`), le bordereau `MANIFEST_Z_OS_DROP.ctl` et les 3 schémas `copybooks/*.cpy` ?",
                ],
              },
              {
                title: 'Chemin cible dans le bucket existant & intégrité binaire stricte',
                bullets: [
                  "Je dépose le lot sous `gs://data-days-demo-landing/raw/corebanking/202610/` via `gcloud storage cp` parallélisé sans transcodage texte (indispensable pour ne pas corrompre les octets `COMP-3`), avec attribution `datacloud.antigravity` ?",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s1-tr1',
                action: 'ran',
                commandSummary: 'MCP data-agent-kit/get_active_gcp_connection → data-days-demo (europe-west1)',
                durationMs: 450,
              },
              {
                id: 'd1-s1-tr2',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'gcp-data-pipelines/SKILL.md',
                lineRange: '#L1-106',
                durationMs: 450,
              },
              {
                id: 'd1-s1-tr3',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'discover-assets/SKILL.md',
                lineRange: '#L1-68',
                durationMs: 450,
              },
              {
                id: 'd1-s1-tr4',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'accidental-data-loss-prevention/SKILL.md',
                lineRange: '#L1-32',
                durationMs: 400,
              },
              {
                id: 'd1-s1-tr5',
                action: 'analyzed',
                icon: 'md',
                fileName: 'MANIFEST_Z_OS_DROP.ctl',
                lineRange: '#L1-28',
                durationMs: 500,
              },
              {
                id: 'd1-s1-tr6',
                action: 'ran',
                commandSummary: 'verify existing bucket gs://data-days-demo-landing/raw/ & inspect local 202610 files',
                durationMs: 700,
              },
            ],
            filesChanged: [],
            terminalLogs: [
              '$ mcp call data-agent-kit get_active_gcp_connection',
              '{ "project_id": "data-days-demo", "region": "europe-west1", "bq_location": "europe-west1" }',
              '$ CLOUDSDK_METRICS_ENVIRONMENT="datacloud.antigravity" gcloud storage ls gs://data-days-demo-landing/raw/',
              'gs://data-days-demo-landing/raw/ [BUCKET EXISTS — europe-west1]',
              '$ ls -lh 00_data_generator/output/corebanking/*202610* 00_data_generator/output/corebanking/*.ebcdic',
              'CFONB120_MVTS_202610_RUN01.cfonb       32M  [99CFT_TRL STATUS=ABEND_S0C7 RC=0012]',
              'CFONB120_MVTS_202610_RUN02_RERUN.cfonb 109M [99CFT_TRL STATUS=OK         RC=0000]',
              'CBK_CUSTOMERS_REF_20261112.ebcdic      11M  [RECFM=FB LRECL=140 EBCDIC CP500 + COMP-3]',
              'CBK_ACCOUNTS_MSTR_20261112.ebcdic      13M  [RECFM=FB LRECL=150 EBCDIC CP500 + COMP-3]',
            ],
            subagents: [
              { id: 'sa-d1-s1a', role: 'GCP Solutions Architect', skill: 'gcp-data-pipelines', status: 'completed' },
            ],
            backgroundTasks: [],
          },
          {
            id: 'd1-s1-t2',
            chipLabel: '2. Confirmer et exécuter le transfert vers GCS RAW',
            prompt:
              "Oui : transfère les deux fichiers d'octobre dans la zone RAW pour l'auditabilité CFT, inclus aussi les maîtres .ebcdic, le manifeste .ctl et les copybooks .cpy, en copie binaire stricte vers gs://data-days-demo-landing/raw/corebanking/202610/.",
            workedDurationLabel: 'Worked for 4s',
            workGroupSummary: 'Applied resource attribution & transferred binary Mainframe drop to GCS RAW',
            intermediateMessage:
              "Transfert parallélisé `gcloud storage cp` vers `gs://data-days-demo-landing/raw/corebanking/202610/` en cours avec préservation binaire stricte.",
            taskFinishedLabel: 'Mainframe October drop transferred to gs://data-days-demo-landing/raw/',
            leadConfirmation:
              "Les fichiers Mainframe du mois passé, les référentiels `.ebcdic` et les Copybooks `.cpy` sont déposés sans altération binaire dans",
            leadLink: {
              text: 'gs://data-days-demo-landing/raw/corebanking/202610/',
              url: 'https://console.cloud.google.com/storage/browser?project=data-days-demo',
            },
            sectionHeading: 'Ce qui a été transféré et vérifié :',
            items: [
              {
                title: 'Copie binaire fidèle au bordereau CFT (`datacloud.antigravity`)',
                bullets: [
                  "Dépôt de `CFONB120_MVTS_202610_RUN01.cfonb` (`ABEND_S0C7` conservé pour traçabilité d'exploitation) et `CFONB120_MVTS_202610_RUN02_RERUN.cfonb` (`RC=0000`, `109 Mo`) sans transcodage.",
                ],
              },
              {
                title: 'Référentiels `EBCDIC + COMP-3` & Copybooks COBOL prêts pour Spark',
                bullets: [
                  "Présence vérifiée de `CBK_CUSTOMERS_REF_20261112.ebcdic` (`79 350` blocs de `140` octets), `CBK_ACCOUNTS_MSTR_20261112.ebcdic` (`94 350` blocs de `150` octets) et des 3 fichiers `copybooks/*.cpy`.",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s1-tr7',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'enforcing-resource-attribution/SKILL.md',
                lineRange: '#L97-138',
                durationMs: 450,
              },
              {
                id: 'd1-s1-tr8',
                action: 'ran',
                commandSummary: 'gcloud storage cp Mainframe 202610 + .ebcdic + copybooks → gs://data-days-demo-landing/raw/corebanking/202610/',
                durationMs: 900,
              },
              {
                id: 'd1-s1-tr9',
                action: 'ran',
                commandSummary: 'verify object sizes & CRC32C hashes in gs://data-days-demo-landing/raw/corebanking/202610/',
                durationMs: 550,
              },
            ],
            filesChanged: [],
            terminalLogs: [
              '$ CLOUDSDK_METRICS_ENVIRONMENT="datacloud.antigravity" gcloud storage cp --recursive 00_data_generator/output/corebanking/*202610* 00_data_generator/output/corebanking/*.ebcdic 00_data_generator/output/corebanking/MANIFEST_Z_OS_DROP.ctl 00_data_generator/output/corebanking/copybooks gs://data-days-demo-landing/raw/corebanking/202610/',
              'Copying file://.../CFONB120_MVTS_202610_RUN01.cfonb [32.1 MiB]',
              'Copying file://.../CFONB120_MVTS_202610_RUN02_RERUN.cfonb [109.4 MiB]',
              'Copying file://.../CBK_CUSTOMERS_REF_20261112.ebcdic [10.6 MiB]',
              'Copying file://.../CBK_ACCOUNTS_MSTR_20261112.ebcdic [13.5 MiB]',
              'Completed 8/8 objects — CRC32C binary checksums verified.',
            ],
            subagents: [
              { id: 'sa-d1-s1b', role: 'GCS Landing Transfer Agent', skill: 'enforcing-resource-attribution', status: 'completed' },
            ],
            backgroundTasks: [
              { id: 'bg-d1-s1', command: 'gcloud storage cp → raw/corebanking/202610/', target: 'gs://data-days-demo-landing', duration: '1.8s' },
            ],
          },
        ],
      },

      // --- Étape 2 de la Démo 1 : Parsing Spark -> BigLake Iceberg ---
      {
        id: 'd1-step2',
        demoId: 'demo1',
        shortName: '2. Parsing Spark → BigLake Iceberg',
        conversationTitle: 'Décodage Copybooks Mainframe via Spark vers BigLake Iceberg',
        projectFolder: '01_demo1_raw_aggregation',
        gitBranch: 'main',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd1-s2-t1',
            chipLabel: '1. Analyser les copybooks & préparer le parsing Iceberg',
            prompt:
              'Explore les fichiers Mainframe déposés dans gs://data-days-demo-landing/raw/corebanking/ et leurs copybooks .cpy pour en faire des tables BigQuery Iceberg dans raw_bank.',
            workedDurationLabel: 'Worked for 4s',
            workGroupSummary: 'Analyzed COBOL copybooks & BigLake Iceberg skills',
            intermediateMessage:
              "J'ai lu les 3 Copybooks COBOL (`CBK_CUSTOMERS_REF.cpy`, `CBK_ACCOUNTS_MSTR.cpy`, `CFONB120_BAL_OPS.cpy`) et inspecté le dataset `data-days-demo.raw_bank`.",
            taskFinishedLabel: 'COBOL copybooks & Spark BigLake Iceberg plan ready',
            leadConfirmation:
              "Le décodage exige **Managed Spark (`gcp-spark`)** : les maîtres utilisent du `COMP-3` Packed Decimal binaire sans `\n` et les relevés CFONB répartissent chaque virement SEPA sur une ligne `04` suivie physiquement d'une ligne complémentaire `05` (`BIC` + `EndToEndId`).",
            sectionHeading: 'Confirme-moi ces 3 arbitrages avant de générer et lancer le job Spark :',
            items: [
              {
                title: 'Contrôle des trailers CFT & rejet automatique du `RUN01` en `ABEND`',
                chips: [{ kind: 'py', label: 'CFONB120_BAL_OPS.cpy' }],
                bullets: [
                  "J'écarte automatiquement tout fichier dont le trailer `99CFT_TRL` n'a pas `RC=0000` (ce qui filtre `202610_RUN01.cfonb` en `ABEND_S0C7`) et je vérifie le compteur `CHECKSUM_MVTS_04` ?",
                ],
              },
              {
                title: 'Fusion par ordre physique `CFONB 04 + 05` & 4 tables BigLake Managed Iceberg',
                bullets: [
                  "Je rattache chaque ligne `05` à sa ligne `04` parente par fenêtre d'offset physique (`LEAD`) et j'écris 4 tables BigLake Managed Iceberg dans `raw_bank` : `cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances` (`01`/`07`) et `cbk_cfonb_movements` (`04+05`) ?",
                ],
              },
              {
                title: 'Préservation des valeurs métier brutes en couche `RAW`',
                bullets: [
                  "J'ai détecté dans l'échantillon `~1,2 %` de dates de valeur `00000000` / `99999999` et des codes guichets décalés (`'42   '`). On conserve ces valeurs brutes intactes en `RAW` (pour les auditer et corriger dans `dbt` en couche `SILVER`), et sur quel profil Spark Connect dois-je exécuter ?",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s2-tr1',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'gcp-spark/SKILL.md',
                lineRange: '#L50-228',
                durationMs: 500,
              },
              {
                id: 'd1-s2-tr2',
                action: 'analyzed',
                icon: 'cpy',
                fileName: 'CBK_CUSTOMERS_REF.cpy',
                lineRange: '#L1-41',
                durationMs: 450,
              },
              {
                id: 'd1-s2-tr3',
                action: 'analyzed',
                icon: 'cpy',
                fileName: 'CBK_ACCOUNTS_MSTR.cpy',
                lineRange: '#L1-47',
                durationMs: 450,
              },
              {
                id: 'd1-s2-tr4',
                action: 'analyzed',
                icon: 'cpy',
                fileName: 'CFONB120_BAL_OPS.cpy',
                lineRange: '#L1-89',
                durationMs: 500,
              },
              {
                id: 'd1-s2-tr5',
                action: 'ran',
                commandSummary: 'MCP bigquery/get_dataset_info data-days-demo.raw_bank & list Spark Connect profiles',
                durationMs: 650,
              },
            ],
            filesChanged: [],
            terminalLogs: [
              '$ gcloud dataproc session-templates list --location=europe-west1 --project=data-days-demo',
              'NAME: hexagone-spark-connect (RUNTIME: 2.2, BIGLAKE_ICEBERG_ENABLED=true)',
            ],
            subagents: [
              { id: 'sa-d1-s2a', role: 'Mainframe Copybook Analyst', skill: 'gcp-spark', status: 'completed' },
            ],
            backgroundTasks: [],
          },
          {
            id: 'd1-s2-t2',
            chipLabel: '2. Confirmer & lancer Managed Spark → BigLake Iceberg',
            prompt:
              "Oui sur les 3 points : filtre RC=0000 + checksum, recolle 04+05 dans les 4 tables BigLake Managed Iceberg, et ne touche à aucune valeur métier en RAW (on gérera la Data Quality dans dbt). Lance sur hexagone-spark-connect !",
            workedDurationLabel: 'Worked for 6s',
            workGroupSummary: 'Authored PySpark job & materialized 4 BigLake Iceberg tables',
            intermediateMessage:
              "Exécution sur `ManagedSparkSession` (`hexagone-spark-connect`) : décodage `EBCDIC CP500 + COMP-3`, rejet de `RUN01` (`RC=0012`) et écriture des 4 tables BigLake Managed Iceberg dans `raw_bank`.",
            taskFinishedLabel: 'Managed Spark → 4 BigLake Iceberg tables in raw_bank finished',
            leadConfirmation:
              "Les 4 tables Core Banking au format ouvert **BigLake Managed Iceberg** sont matérialisées et interrogeables immédiatement dans",
            leadLink: {
              text: 'bigquery.cloud.google.com/dataset/data-days-demo:raw_bank',
              url: 'https://console.cloud.google.com/bigquery?project=data-days-demo',
            },
            sectionHeading: 'Ce qui a été mis en place :',
            items: [
              {
                title: 'Décodage binaire `EBCDIC CP500 + COMP-3` des référentiels maîtres',
                chips: [
                  { kind: 'py', label: 'parse_corebanking_iceberg.py' },
                  { kind: 'bq', label: 'cbk_accounts_master' },
                ],
                bullets: [
                  "Création de `cbk_customers_ref` (`79 350` clients) et `cbk_accounts_master` (`94 350` comptes avec soldes `COMP-3` sur 8 octets décodés au centime près).",
                ],
              },
              {
                title: 'Filtrage `ABEND` & reconstruction multi-lignes `CFONB 04 + 05`',
                chips: [
                  { kind: 'bq', label: 'cbk_cfonb_balances' },
                  { kind: 'bq', label: 'cbk_cfonb_movements' },
                ],
                bullets: [
                  "Exclusion automatique de `202610_RUN01.cfonb` (`ABEND_S0C7`), rattachement des `3 080 073` compléments `05` (`BIC` + `EndToEndId`) sur les `5 500 000` mouvements `04`, et conservation fidèle en `RAW` des anomalies métier (`66 000` dates `00000000`/`99999999` et guichets décalés).",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s2-tr6',
                action: 'edited',
                icon: 'py',
                fileName: 'parse_corebanking_iceberg.py',
                added: 96,
                removed: 0,
                durationMs: 650,
              },
              {
                id: 'd1-s2-tr7',
                action: 'ran',
                commandSummary: 'python3 -m py_compile 01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py',
                durationMs: 400,
              },
              {
                id: 'd1-s2-tr8',
                action: 'ran',
                commandSummary: 'ManagedSparkSession (hexagone-spark-connect) → write 4 BigLake Iceberg tables',
                durationMs: 950,
              },
            ],
            filesChanged: [
              {
                path: '01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py',
                language: 'python',
                badge: 'PY',
                added: 96,
                removed: 0,
                content: `from google.cloud.managed_spark_connect import ManagedSparkSession
from pyspark.sql import Window, functions as F

spark = (
    ManagedSparkSession.builder
    .projectId("data-days-demo")
    .location("europe-west1")
    .runtimeProfile("hexagone-spark-connect")
    .getOrCreate()
)

# 1. Filtre les fichiers CFONB dont le trailer 99CFT_TRL a RC == '0000' (écarte 202610_RUN01 ABEND_S0C7)
raw_lines = (
    spark.read.text("gs://data-days-demo-landing/raw/corebanking/**/*.cfonb*")
    .withColumn("_source_file", F.input_file_name())
    .withColumn("_line_offset", F.monotonically_increasing_id())
)

# 2. Recolle la ligne complémentaire '05' (BIC & EndToEndId SEPA) située physiquement sous son '04'
w_phys = Window.partitionBy("_source_file").orderBy("_line_offset")
stitched = raw_lines.withColumn("_next_line", F.lead("value").over(w_phys))

movements_df = (
    stitched.filter(F.substring("value", 1, 2) == "04")
    .select(
        F.substring("value", 8, 4).alias("code_op_interne"),
        F.substring("value", 12, 5).alias("code_guichet_raw"),
        F.substring("value", 22, 11).alias("num_compte_11"),
        F.substring("value", 35, 8).alias("date_compta"),
        F.substring("value", 45, 8).alias("date_valeur_raw"),  # Conserve '00000000' en RAW !
        F.when(F.substring("_next_line", 1, 2) == "05", F.trim(F.substring("_next_line", 48, 12))).alias("counterparty_bic"),
        F.when(F.substring("_next_line", 1, 2) == "05", F.trim(F.substring("_next_line", 60, 36))).alias("sepa_end_to_end_id"),
        "_source_file",
    )
)
movements_df.writeTo("biglake.raw_bank.cbk_cfonb_movements").using("iceberg").createOrReplace()`,
              },
            ],
            terminalLogs: [
              '$ python 01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py',
              '[SKIP] CFONB120_MVTS_202610_RUN01.cfonb rejected (99CFT_TRL STATUS=ABEND_S0C7 RC=0012)',
              '[OK] biglake.raw_bank.cbk_customers_ref (ICEBERG): 79,350 rows decoded from EBCDIC CP500 + COMP-3',
              '[OK] biglake.raw_bank.cbk_accounts_master (ICEBERG): 94,350 rows decoded from EBCDIC CP500 + COMP-3',
              '[OK] biglake.raw_bank.cbk_cfonb_balances (ICEBERG): 2,875,062 balance snapshots (01/07)',
              '[OK] biglake.raw_bank.cbk_cfonb_movements (ICEBERG): 5,500,000 movements (3,080,073 05-lines stitched)',
            ],
            subagents: [
              { id: 'sa-d1-s2b', role: 'PySpark BigLake Iceberg Engineer', skill: 'gcp-spark', status: 'completed' },
            ],
            backgroundTasks: [
              { id: 'bg-d1-s2', command: 'ManagedSparkSession → BigLake Iceberg', target: 'data-days-demo.raw_bank', duration: '4.2s' },
            ],
          },
        ],
      },

      // --- Étape 3 de la Démo 1 : Fédération AWS S3 & PDF Object Table ---
      {
        id: 'd1-step3',
        demoId: 'demo1',
        shortName: '3. Fédération AWS S3 & Object Table PDF',
        conversationTitle: 'Borderless Lakehouse AWS S3 & Contrats PDF Object Table',
        projectFolder: '01_demo1_raw_aggregation',
        gitBranch: 'main',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd1-s3-t1',
            chipLabel: '1. Fédérer AWS S3 (Zéro-Copie) & exposer les 250 PDF',
            prompt:
              "Connecte sans copie le SaaS CRM hébergé sur AWS S3 / Glue, expose les flux paiements ISO 20022 et SAP/ALM dans raw_bank, et crée une Object Table sur les 250 PDF promotionnels.",
            workedDurationLabel: 'Worked for 5s',
            workGroupSummary: 'Federated AWS Glue S3 catalog & registered GCS Object Table',
            intermediateMessage:
              "Création du lien Borderless Lakehouse vers AWS (`s3://hexagone-crm-iceberg`) et indexation des `250` PDF promotionnels via Object Table en cours sur `data-days-demo.raw_bank`.",
            taskFinishedLabel: 'AWS S3 Omni federation & GCS PDF Object Table provisioned',
            leadConfirmation:
              "L'ensemble des silos multi-cloud et non structurés est désormais unifié sans copie dans `data-days-demo.raw_bank` sur",
            leadLink: {
              text: 'bigquery.cloud.google.com/dataset/data-days-demo:raw_bank',
              url: 'https://console.cloud.google.com/bigquery?project=data-days-demo',
            },
            sectionHeading: 'Ce qui a été mis en place :',
            items: [
              {
                title: 'Fédération Borderless Lakehouse vers AWS S3 / Glue (`0 octet` copié)',
                chips: [
                  { kind: 'sql', label: '01_omni_aws_crm.sql' },
                  { kind: 'bq', label: 'ext_aws_crm_customers' },
                ],
                bullets: [
                  "Connexion directe via BigQuery Omni (`aws-eu-west-1-crm-conn`) aux tables Iceberg distantes : `80 000` clients sur `8` régions / `450` agences (`+15 000` ouvertures récentes, `0` clôture) et `320 000` verbatims RDV & appels.",
                ],
              },
              {
                title: 'Flux SEPA / SAP Iceberg & Object Table GCS sur les 250 PDF',
                chips: [
                  { kind: 'sql', label: '03_object_table_pdf.sql' },
                  { kind: 'bq', label: 'raw_promo_contracts_pdf' },
                ],
                bullets: [
                  "Exposition de `raw_sepa_payments` (`6,2 M` d'événements `pacs.008`), `raw_sap_gl_alm` (`1,2 M` d'écritures) et des `250` avenants promotionnels PDF (`gs://data-days-demo-contracts-pdf/promos_2026/*.pdf`).",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s3-tr1',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'federate-lakehouse-catalog/SKILL.md',
                lineRange: '#L1-94',
                durationMs: 500,
              },
              {
                id: 'd1-s3-tr2',
                action: 'edited',
                icon: 'sql',
                fileName: '01_omni_aws_crm.sql',
                added: 34,
                removed: 0,
                durationMs: 600,
              },
              {
                id: 'd1-s3-tr3',
                action: 'edited',
                icon: 'sql',
                fileName: '03_object_table_pdf.sql',
                added: 14,
                removed: 0,
                durationMs: 500,
              },
              {
                id: 'd1-s3-tr4',
                action: 'ran',
                commandSummary: 'federate AWS Glue S3 tables & register 250 PDF Object Table in raw_bank',
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
              '$ bq query --label datacloud:antigravity --project_id=data-days-demo --nouse_legacy_sql < 01_omni_aws_crm.sql',
              'Created data-days-demo.raw_bank.ext_aws_crm_customers [80,000 rows federated — 0 B copied]',
              'Created data-days-demo.raw_bank.ext_aws_crm_interactions [320,000 rows federated — 0 B copied]',
              '$ bq query --label datacloud:antigravity --project_id=data-days-demo --nouse_legacy_sql < 03_object_table_pdf.sql',
              'Object Table raw_promo_contracts_pdf registered: 250 PDF objects indexed.',
            ],
            subagents: [
              { id: 'sa-d1-s3', role: 'AWS Lakehouse Federator', skill: 'federate-lakehouse-catalog', status: 'completed' },
            ],
            backgroundTasks: [
              { id: 'bg-d1-s3', command: 'bq query 01_omni_aws_crm.sql', target: 'raw_bank (AWS Omni)', duration: '1.4s' },
            ],
          },
        ],
      },

      // --- Étape 4 de la Démo 1 : Init dbt & Doc KC ---
      {
        id: 'd1-step4',
        demoId: 'demo1',
        shortName: '4. Init dbt & Doc Knowledge Catalog',
        conversationTitle: 'Initialisation dbt staging & Documentation Knowledge Catalog',
        projectFolder: '01_demo1_raw_aggregation',
        gitBranch: 'main',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd1-s4-t1',
            chipLabel: '1. Initialiser dbt & publier la doc technique KC',
            prompt:
              'Initialise la structure industrielle dbt sur raw_bank et publie la documentation technique initiale dans Knowledge Catalog.',
            workedDurationLabel: 'Worked for 5s',
            workGroupSummary: 'Generated dbt project & synced technical metadata to Knowledge Catalog',
            intermediateMessage:
              "Génération du projet `dbt` (`hexagone_bank_lakehouse`) et synchronisation des métadonnées techniques vers Knowledge Catalog en cours.",
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
                  "Déclaration des tables Iceberg Mainframe (`cbk_*`), AWS Omni (`ext_aws_*`), flux SEPA/SAP et Object Table PDF avec persistance automatique vers Knowledge Catalog.",
                ],
              },
              {
                title: 'Premières alertes remontées par la documentation technique',
                chips: [{ kind: 'kc', label: 'Knowledge Catalog · raw_bank' }],
                bullets: [
                  "Le profilage initial met déjà en évidence `~3,4 %` de doublons `end_to_end_id`, `8,1 %` de statuts `RJCT` / `PDNG`, `1,2 %` de dates Mainframe `00000000` / `99999999` et `650` comptes AWS non réconciliés.",
                ],
              },
            ],
            traces: [
              {
                id: 'd1-s4-tr1',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'dbt-bigquery/SKILL.md',
                lineRange: '#L1-112',
                durationMs: 500,
              },
              {
                id: 'd1-s4-tr2',
                action: 'edited',
                icon: 'yml',
                fileName: 'dbt_project.yml',
                added: 28,
                removed: 0,
                durationMs: 500,
              },
              {
                id: 'd1-s4-tr3',
                action: 'edited',
                icon: 'yml',
                fileName: '_raw_sources.yml',
                added: 38,
                removed: 0,
                durationMs: 550,
              },
              {
                id: 'd1-s4-tr4',
                action: 'ran',
                commandSummary: 'dbt compile --select staging.* & sync technical metadata to Knowledge Catalog',
                durationMs: 800,
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
                added: 38,
                removed: 0,
                content: `version: 2

sources:
  - name: raw_bank
    database: data-days-demo
    schema: raw_bank
    description: "Couche RAW : BigLake Iceberg Mainframe, AWS S3 Omni & Object Tables PDF"
    tables:
      - name: cbk_customers_ref
      - name: cbk_accounts_master
      - name: cbk_cfonb_balances
      - name: cbk_cfonb_movements
      - name: ext_aws_crm_customers
      - name: ext_aws_crm_interactions
      - name: raw_sepa_payments
      - name: raw_sap_gl_alm
      - name: raw_promo_contracts_pdf`,
              },
            ],
            terminalLogs: [
              '$ dbt compile --project-dir 02_demo2_silver_dbt_dq',
              'Found 9 sources in data-days-demo.raw_bank',
              'Synced technical metadata to Knowledge Catalog (europe-west1) — 3 DQ warnings flagged.',
            ],
            subagents: [
              { id: 'sa-d1-s4', role: 'dbt Project Architect', skill: 'dbt-bigquery', status: 'completed' },
            ],
            backgroundTasks: [
              { id: 'bg-d1-s4', command: 'dbt compile && kc sync-raw', target: 'Knowledge Catalog', duration: '1.9s' },
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
                  'Mainframe z/OS (EBCDIC+COMP3 & CFONB 04+05) décodé par Managed Spark en BigLake Iceberg.',
                  'AWS S3 CRM (80k clients, 320k notes) fédéré sans copie via BigQuery Omni.',
                  '250 contrats promotionnels PDF exposés via Object Table GCS.',
                  'Passage requis en Demo 2 : nettoyage dbt SILVER + scans Auto Data Quality.',
                ],
              },
            },
          },
        ],
      },
    ],
  },

  // ============================================================================
  // WORKSPACE DEMO 2 : 02_demo2_silver_dbt_dq
  // ============================================================================
  {
    id: 'demo2',
    workspaceLabel: 'Demo 2 · SILVER & Data Quality',
    folderName: '02_demo2_silver_dbt_dq',
    conversations: [
      {
        id: 'd2-step1',
        demoId: 'demo2',
        shortName: '1. Scan Auto Data Quality RAW',
        conversationTitle: 'Audit Auto Data Quality sur la couche RAW',
        projectFolder: '02_demo2_silver_dbt_dq',
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
            leadConfirmation: "L'audit complet de qualité sur `raw_bank` est disponible dans",
            leadLink: {
              text: 'console.cloud.google.com/dataplex/govern/quality?project=data-days-demo',
              url: 'https://console.cloud.google.com/dataplex?project=data-days-demo',
            },
            sectionHeading: 'Anomalies identifiées dans la couche RAW & arbitrages proposés :',
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
                chips: [{ kind: 'bq', label: 'cbk_cfonb_movements' }],
                bullets: [
                  "`1,2 %` de dates de valeur encodées à `00000000` ou `99999999` (`66 000` lignes), codes agences non normalisés (`'0042'` vs `'42  '`), et `650` comptes récents créés sur AWS S3 pas encore réconciliés dans le Mainframe J-1.",
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
                lineRange: '#L1-38',
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
    cbk_cfonb_movements:
      invalid_date_00000000_99999999_pct: 1.20
      unnormalized_branch_code_rows: 664637
    cross_silo_aws_mainframe:
      orphan_recent_accounts: 650`,
              },
            ],
            terminalLogs: [
              '$ gcloud dataplex datascans run raw-bank-dq-scan --project=data-days-demo --location=europe-west1',
              '[FAIL] raw_sepa_payments.end_to_end_id uniqueness: 96.60% (threshold 100%)',
              '[FAIL] cbk_cfonb_movements.date_valeur_raw valid_date: 98.80% (threshold 100%)',
              '[WARN] cross-silo AWS CRM <-> Mainframe account key match: 650 unmatched J0 accounts',
            ],
            subagents: [
              { id: 'sa-d2-1', role: 'Data Quality Auditor', skill: 'data-autocleaning', status: 'completed' },
            ],
            backgroundTasks: [
              { id: 'bg-d2-1', command: 'dataplex datascans run raw-bank-dq', target: 'raw_bank', duration: '2.2s' },
            ],
          },
        ],
      },
      {
        id: 'd2-step2',
        demoId: 'demo2',
        shortName: '2. Modèles dbt SILVER & Tests DQ',
        conversationTitle: 'Génération des 5 modèles dbt SILVER et contrats schema.yml',
        projectFolder: '02_demo2_silver_dbt_dq',
        gitBranch: 'feat/silver-data-products',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd2-t2',
            chipLabel: '1. Générer les 5 modèles dbt SILVER & tests DQ',
            prompt:
              'Génère les 5 modèles dbt SILVER dans silver_bank pour corriger toutes ces anomalies, extraire les 250 PDF via BigQuery AI et intégrer les tests de qualité schema.yml.',
            workedDurationLabel: 'Worked for 6s',
            workGroupSummary: 'Explored files, ran commands, edited files',
            intermediateMessage:
              'Écriture des 5 transformations SQL `dbt` dans `models/silver/` et du contrat de tests `schema.yml` en cours.',
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
                  "Filtrage strict sur `tx_status = 'ACSC'` avec `ROW_NUMBER() OVER (PARTITION BY end_to_end_id)`, fallback sur `date_compta` quand `date_valeur_raw IN ('00000000','99999999')`, normalisation `LPAD` des agences et réconciliation des `650` comptes AWS S3.",
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
  creditor_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX') AS is_neobank_outflow
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
        ],
      },
      {
        id: 'd2-step3',
        demoId: 'demo2',
        shortName: '3. Build & 5 Data Products KC',
        conversationTitle: 'Exécution dbt build & Publication des 5 Data Products',
        projectFolder: '02_demo2_silver_dbt_dq',
        gitBranch: 'feat/silver-data-products',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd2-t3',
            chipLabel: '1. Exécuter dbt build & publier les 5 Data Products',
            prompt:
              'Lance dbt build sur data-days-demo et publie les 5 Data Products élémentaires dans Knowledge Catalog.',
            workedDurationLabel: 'Worked for 6s',
            workGroupSummary: 'Explored files, ran commands, edited files',
            intermediateMessage:
              "Exécution de `dbt build --select silver.*` sur `data-days-demo` (`europe-west1`) et publication des Data Products dans Knowledge Catalog en cours.",
            taskFinishedLabel: 'dbt build (29/29 PASS) & Knowledge Catalog publication finished',
            leadConfirmation:
              'Les 5 Data Products `SILVER` sont matérialisés à `100 %` de Data Quality et publiés dans',
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
    ],
  },

  // ============================================================================
  // WORKSPACE DEMO 3 : 03_demo3_kc_semantics_cfo
  // ============================================================================
  {
    id: 'demo3',
    workspaceLabel: 'Demo 3 · Knowledge Catalog & CFO',
    folderName: '03_demo3_kc_semantics_cfo',
    conversations: [
      {
        id: 'd3-step1',
        demoId: 'demo3',
        shortName: '1. Audit Faux PNB (+42,8 M€) & Vidéos',
        conversationTitle: 'Audit du crash sémantique & Extraction multimodale .mp4',
        projectFolder: '03_demo3_kc_semantics_cfo',
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
        ],
      },
      {
        id: 'd3-step2',
        demoId: 'demo3',
        shortName: '2. Publication KC & Vérité (-38,42 M€)',
        conversationTitle: 'Publication des 3 Glossaires KC & Vérification CFO',
        projectFolder: '03_demo3_kc_semantics_cfo',
        gitBranch: 'feat/kc-cfo-semantics',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd3-t2',
            chipLabel: '1. Publier les 3 glossaires KC & vérifier le PNB (-38,42 M€)',
            prompt:
              "Publie les 3 glossaires métier et le Context Set certifié dans Knowledge Catalog sur data-days-demo, puis vérifie l'écart exact de PNB CFO.",
            workedDurationLabel: 'Worked for 5s',
            workGroupSummary: 'Explored files, ran commands, edited files',
            intermediateMessage:
              'Validation `kcmd` et publication des 3 glossaires métier ainsi que du graphe sémantique dans Knowledge Catalog (`data-days-demo`) en cours.',
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
                  'Rattachement direct des définitions gouvernées aux 5 Data Products `silver_bank` avec `-78 %` de tokens consommés lors de la génération SQL par les agents.',
                ],
              },
              {
                title: 'Vérification de la vérité financière CFO (`-38,42 M€`)',
                chips: [
                  { kind: 'sql', label: 'governed_cfo_pnb_variance.sql' },
                  { kind: 'bq', label: 'v_cfo_certified_pnb_variance' },
                ],
                bullets: [
                  "Passage de `+42 800 000,00 €` (faux résultat naïf) à exactement `-38 420 000,00 €` d'écart net de PNB vs budget (`-24 120 000,00 €` de coût de refinancement €STR ALM + `-14 300 000,00 €` engagés dans les `250` PDF d'agence).",
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
    ],
  },

  // ============================================================================
  // WORKSPACE DEMO 4 : 04_demo4_scale_mobile_adk
  // ============================================================================
  {
    id: 'demo4',
    workspaceLabel: 'Demo 4 · Scale Mobile & ADK',
    folderName: '04_demo4_scale_mobile_adk',
    conversations: [
      {
        id: 'd4-step1',
        demoId: 'demo4',
        shortName: '1. Modèles BQML & Budget Insight',
        conversationTitle: 'Prévisions AI.FORECAST & Propension Offres dans BigQuery',
        projectFolder: '04_demo4_scale_mobile_adk',
        gitBranch: 'feat/mobile-adk-agents',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd4-t1',
            chipLabel: '1. Calculer Budget Insight & propension Livret Boost',
            prompt:
              "À partir des Data Products silver_bank et des règles Knowledge Catalog, génère les requêtes BigQuery AI (AI.FORECAST reste à vivre & détection dérive abonnements) pour alimenter les agents mobiles.",
            workedDurationLabel: 'Worked for 5s',
            workGroupSummary: 'Analyzed SILVER schemas, generated BQML forecast & offer eligibility SQL',
            intermediateMessage:
              "Calcul des projections de reste à vivre (`AI.FORECAST` TimesFM) et détection des hausses d'abonnements sur les `80 000` clients dans BigQuery en cours.",
            taskFinishedLabel: 'BigQuery AI Budget Insights & Offer Propensity computed',
            leadConfirmation:
              "Les features prédictives sont matérialisées dans `gold_bank.customer_mobile_insights` (client témoin `CUST00002026` Lucas Martin : hausse abonnement `+4,00 €`, remboursement santé `+42,00 €`, excédent fin de mois prévu `+300,00 €` éligible au *Livret Boost Maison 4 %*).",
            sectionHeading: 'Ce qui a été mis en place :',
            items: [
              {
                title: 'Prévision budgétaire `AI.FORECAST` & détection d’anomalies récurrentes',
                chips: [{ kind: 'sql', label: '01_bqml_budget_insights.sql' }],
                bullets: [
                  "Identification automatique du passage `STRMFLIX` de `15,99 €` à `19,99 €` (`+4,00 €`) et projection du solde net fin de mois à `+300,00 €`.",
                ],
              },
            ],
            traces: [
              {
                id: 'd4-tr1',
                action: 'analyzed',
                icon: 'dak',
                fileName: 'bigquery-ai-ml/SKILL.md',
                lineRange: '#L1-104',
                durationMs: 500,
              },
              {
                id: 'd4-tr2',
                action: 'edited',
                icon: 'sql',
                fileName: '01_bqml_budget_insights.sql',
                added: 36,
                removed: 0,
                durationMs: 600,
              },
              {
                id: 'd4-tr3',
                action: 'ran',
                commandSummary: 'bq query --label datacloud:antigravity 01_bqml_budget_insights.sql',
                durationMs: 850,
              },
            ],
            filesChanged: [
              {
                path: '04_demo4_scale_mobile_adk/sql/01_bqml_budget_insights.sql',
                language: 'sql',
                badge: 'SQL',
                added: 36,
                removed: 0,
                content: `-- Calcul analytique à l'échelle dans BigQuery avant synchronisation AlloyDB (<15ms)
CREATE OR REPLACE TABLE \`data-days-demo.gold_bank.customer_mobile_insights\` AS
SELECT
  customer_id,
  account_id,
  detected_subscription_delta_eur,
  forecast_eom_surplus_eur,
  IF(forecast_eom_surplus_eur >= 100, 'LIVRET_BOOST_MAISON_4PCT', NULL) AS recommended_offer_code
FROM \`data-days-demo.gold_bank.v_budget_forecast_candidates\`;`,
              },
            ],
            terminalLogs: [
              '$ bq query --label datacloud:antigravity < 01_bqml_budget_insights.sql',
              'CUST00002026 (Lucas Martin): sub_delta=+4.00 EUR | eom_surplus=+300.00 EUR | offer=LIVRET_BOOST_MAISON_4PCT',
            ],
            subagents: [
              { id: 'sa-d4-1', role: 'BigQuery AI ML Engineer', skill: 'bigquery-ai-ml', status: 'completed' },
            ],
            backgroundTasks: [],
          },
        ],
      },
      {
        id: 'd4-step2',
        demoId: 'demo4',
        shortName: '2. Synchro AlloyDB (<15ms) & ADK',
        conversationTitle: 'Synchronisation AlloyDB & Exposition aux 3 Agents ADK',
        projectFolder: '04_demo4_scale_mobile_adk',
        gitBranch: 'feat/mobile-adk-agents',
        greetingName: 'Clément',
        modelLabel: 'Gemini 4 - Carbon',
        turns: [
          {
            id: 'd4-t2',
            chipLabel: '1. Synchroniser vers AlloyDB & brancher les 3 agents ADK',
            prompt:
              "Configure alloydb_sync pour exposer ces insights en moins de 15 ms avec le flux temps réel du jour J aux 3 agents ADK (Budget Insight, Conseil Offres, Action).",
            workedDurationLabel: 'Worked for 5s',
            workGroupSummary: 'Configured alloydb_sync & ADK operational tools',
            intermediateMessage:
              "Synchronisation `alloydb_sync` vers `bank-digital-primary` (`mobile_bank`) et déploiement des tools ADK en cours.",
            taskFinishedLabel: 'alloydb_sync (<15ms) & 3 ADK Mobile Agents ready',
            leadConfirmation:
              "Les insights BigQuery et le solde temps réel sont servis en `8,4 ms` depuis `AlloyDB` aux 3 agents `ADK` de l'application Android.",
            sectionHeading: 'Ce qui a été mis en place :',
            items: [
              {
                title: 'Pont opérationnel `alloydb_sync` (`BigQuery → AlloyDB`)',
                chips: [{ kind: 'py', label: 'adk_mobile_agents.py' }],
                bullets: [
                  "Lecture opérationnelle `< 15 ms` combinant les insights `BQML` (`J-1`) et les événements temps réel du jour `J`, avec exécution transactionnelle 1-clic du virement d'épargne interne.",
                ],
              },
            ],
            traces: [
              {
                id: 'd4-tr4',
                action: 'edited',
                icon: 'py',
                fileName: 'adk_mobile_agents.py',
                added: 48,
                removed: 0,
                durationMs: 650,
              },
              {
                id: 'd4-tr5',
                action: 'ran',
                commandSummary: 'sync gold_bank.customer_mobile_insights → AlloyDB mobile_bank (p99 = 8.4ms)',
                durationMs: 800,
              },
            ],
            filesChanged: [
              {
                path: '04_demo4_scale_mobile_adk/agents/adk_mobile_agents.py',
                language: 'python',
                badge: 'PY',
                added: 48,
                removed: 0,
                content: `from google.adk.agents import Agent

budget_insight_agent = Agent(
    name="budget_insight_agent",
    model="gemini-2.5-flash",
    instruction="Présente les événements marquants depuis la dernière connexion et le reste à vivre prévu.",
)

offer_advisor_agent = Agent(
    name="offer_advisor_agent",
    model="gemini-2.5-flash",
    instruction="Propose le Livret Boost Maison 4% uniquement si forecast_eom_surplus_eur > 0.",
)

action_execution_agent = Agent(
    name="action_execution_agent",
    model="gemini-2.5-flash",
    instruction="Exécute de façon transactionnelle dans AlloyDB le virement d'épargne validé en 1-clic.",
)`,
              },
            ],
            terminalLogs: [
              '$ python verify_alloydb_latency.py --customer CUST00002026',
              'AlloyDB read p99 latency: 8.4 ms — 3 ADK agents online on Agent Runtime.',
            ],
            subagents: [
              { id: 'sa-d4-2', role: 'AlloyDB & ADK Runtime Architect', skill: 'cloud-databases-onboarding', status: 'completed' },
            ],
            backgroundTasks: [],
          },
        ],
      },
    ],
  },
];

export const ALL_CONVERSATIONS: Record<string, DemoScenario> = Object.fromEntries(
  DEMO_WORKSPACES.flatMap((ws) => ws.conversations.map((conv) => [conv.id, conv]))
);
