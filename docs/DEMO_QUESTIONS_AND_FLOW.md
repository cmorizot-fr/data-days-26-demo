# Fil conducteur des échanges live & Skills Data Agent Kit (`DAK`) — Paris Data Summit 2026

> [!IMPORTANT]
> Ce document constitue le **script conversationnel de référence** mémorisé pour `Antigravity (AGY)` (lié depuis [`AGENTS.md`](../AGENTS.md)) et l'aide-mémoire de scène des intervenants.
> **Organisation de l'interface** : **1 Workspace par Démo** (`01_demo1_raw_aggregation` .. `04_demo4_scale_mobile_adk`), et sous chaque Workspace, **1 Conversation par Étape de la démo**. Les buckets GCS existent déjà.

---

## Cartographie globale des Skills & MCP `Data Agent Kit` mobilisés

| Workspace Démo & Étape | MCP Servers sollicités | Skills `DAK` activés | Rôle clé dans la démo |
| :--- | :--- | :--- | :--- |
| **Démo #1 — Étape 1**<br>*Transfert Mainframe → GCS `RAW`* | `data-agent-kit` (`get_active_gcp_connection`) | `gcp-data-pipelines`<br>`discover-assets`<br>`accidental-data-loss-prevention`<br>`enforcing-resource-attribution` | Vérifie le bucket `RAW` existant, détecte le double fichier d'octobre (`RUN01` en `ABEND_S0C7` vs `RUN02_RERUN`) + les `.ebcdic` / `.cpy` et transfère en binaire strict avec label `datacloud.antigravity`. |
| **Démo #1 — Étape 2**<br>*Parsing Spark → BigLake Iceberg* | `bigquery` (`get_dataset_info`, `list_table_ids`)<br>`notebooks` *(si `.ipynb`)* | `gcp-spark` *(+ `biglake_iceberg.md`)*<br>`discover-assets`<br>`enforcing-resource-attribution` | Lit les Copybooks `.cpy`, filtre `RC=0000` (écarte `RUN01`), décode `EBCDIC CP500 + COMP-3`, recolle `CFONB 04+05` et écrit en **BigLake Managed Iceberg** (`raw_bank`). |
| **Démo #1 — Étape 3**<br>*AWS Borderless & PDF Object Table* | `bigquery` (`execute_sql`) | `federate-lakehouse-catalog` | Fédère `AWS Glue / S3` sans copie et crée l'**Object Table** sur les 250 PDF. |
| **Démo #1 — Étape 4**<br>*Init `dbt` & Doc `Knowledge Catalog`* | `bigquery` | `dbt-bigquery`<br>`curate-context` | Initialise `dbt_project.yml` et `_raw_sources.yml` + synchronisation technique initiale dans `Knowledge Catalog`. |
| **Démo #2 (3 étapes)**<br>*Industrialisation `SILVER` & DQ* | `bigquery` (`execute_sql`, `get_table_info`) | `data-autocleaning`<br>`dbt-bigquery`<br>`discover-assets` | Profile les anomalies `RAW`, fait arbitrer les règles de nettoyage/réconciliation et génère les 5 Data Products `dbt` testés. |
| **Démo #3 (2 étapes)**<br>*Sémantique `KC` & Pilotage CFO* | `bigquery`<br>`data-agent-kit` (`render_chart`) | `curate-context` (`kcmd` / OKF)<br>`discover-assets`<br>`bigquery-ai-ml` | Réconcilie les catalogues legacy + interviews `.mp4`, publie le contexte certifié dans `KC` et corrige l'écart PNB de `+42,80 M€` à `-38,42 M€`. |
| **Démo #4 (2 étapes)**<br>*Scale Digital : `BQML` & `AlloyDB`* | `bigquery`<br>`data-agent-kit` | `bigquery-ai-ml`<br>`ml-best-practices`<br>`cloud-databases-onboarding` | Génère les prévisions `AI.FORECAST` / propension dans BigQuery et expose les insights en `< 15 ms` via `alloydb_sync` aux 3 agents `ADK`. |

---

## Workspace Démo #1 — `01_demo1_raw_aggregation` (4 Conversations d'étapes)

### Conversation Étape 1 — Transfert Mainframe du mois passé vers GCS `RAW`

* **Chip 1 (Prompt pré-rempli) :**
  > `Transfere les données mainframe du serveur de fichier pour le mois passé, sur GCS dans la zone RAW.`
* **Actions internes d'`AGY` + `DAK` avant de répondre :**
  1. **MCP `data-agent-kit` -> `get_active_gcp_connection`** : récupère `project_id` (`data-days-demo`) et `region` (`europe-west1`).
  2. **Skill `discover-assets` & vérification du bucket existant** : confirme que le bucket `gs://data-days-demo-landing/raw/` existe déjà (aucune demande de création de bucket).
  3. **Inspection du serveur de fichiers local sur le mois passé (`202610`)** (`00_data_generator/output/corebanking/`) : lit `MANIFEST_Z_OS_DROP.ctl`, repère les binaires `.ebcdic` (`RECFM=FB`, `CP500 + COMP-3`), les Copybooks `.cpy`, et **l'incident sur octobre 2026** (`RUN01` en `ABEND_S0C7 RC=0012` vs `RUN02_RERUN` en `RC=0000`).
* **Questions posées par `AGY` sur scène :**
  1. **Incident sur le mois passé (`202610` : `ABEND` vs `RERUN`)** : *« Sur le serveur local, octobre 2026 comporte deux fichiers : `CFONB120_MVTS_202610_RUN01.cfonb` interrompu en crash (`STATUS=ABEND_S0C7`, `RC=0012`, `32 Mo`) et `CFONB120_MVTS_202610_RUN02_RERUN.cfonb` complet (`STATUS=OK`, `RC=0000`, `109 Mo`). On transfère les deux dans la zone `RAW` pour conserver une trace d'audit fidèle au CFT Mainframe (et laisser Spark filtrer sur `RC=0000`), ou j'exclus `RUN01` dès la copie ? »*
  2. **Référentiels maîtres `.ebcdic` & Copybooks COBOL `.cpy` associés** : *« Pour permettre le décodage aval vers BigLake Iceberg, j'inclus également les 2 référentiels maîtres binaires (`CBK_CUSTOMERS_REF_20261112.ebcdic`, `CBK_ACCOUNTS_MSTR_20261112.ebcdic`), le bordereau `MANIFEST_Z_OS_DROP.ctl` et les 3 schémas `copybooks/*.cpy` ? »*
  3. **Chemin cible dans le bucket existant & intégrité binaire stricte** : *« Je dépose le lot sous `gs://data-days-demo-landing/raw/corebanking/202610/` via `gcloud storage cp` parallélisé sans transcodage texte (indispensable pour préserver les octets `COMP-3`), avec attribution `datacloud.antigravity` ? »*
* **Chip 2 (Confirmation intervenant) :**
  > `Oui : transfère les deux fichiers d'octobre dans la zone RAW pour l'auditabilité CFT, inclus aussi les maîtres .ebcdic, le manifeste .ctl et les copybooks .cpy, en copie binaire stricte vers gs://data-days-demo-landing/raw/corebanking/202610/.`

---

### Conversation Étape 2 — Décodage Mainframe via Dataproc Serverless Spark & Documentation BigLake Iceberg (`raw_bank`)

* **Skills `DAK` & outils mobilisés :** `discover-assets`, `gcp-data-pipelines`, `gcp-spark` (`biglake_iceberg.md`, `read_write_data.md`, `gcloud_dataproc.md`), `enforcing-resource-attribution` (`CLOUDSDK_METRICS_ENVIRONMENT="... datacloud.antigravity"`, `--label datacloud:antigravity`).
* **Chip 1 — Diagnostic des Copybooks & choix du moteur :**
  > `Explore les fichiers Mainframe déposés dans gs://data-days-demo-landing/RAW/corebanking/ et leurs copybooks .cpy. Peut-on les charger directement dans BigQuery et les documenter, ou faut-il passer par un job Spark Serverless ?`
  * **Raisonnement d'`AGY` :** explique pourquoi `bq load` natif échoue (flux binaire fixe `RECFM=FB` sans `\n`, `EBCDIC CP500 + COMP-3` signé sur 2/3/8 octets, mix `.cfonb.gz` / `.cfonb`, trailer `99CFT_TRL` avec `202610_RUN01.cfonb` en `ABEND_S0C7` `RC=0012`, et rattachement positionnel `04 + 05` sans clé répétée) et pose les **3 questions d'arbitrage** :
    1. **Filtrage CFT (`99CFT_TRL`)** : rejet automatique de tout fichier où `RC != 0000` (écartant `202610_RUN01.cfonb`) + contrôle de `DATA_RECORDS` et `CHECKSUM_MVTS_04` ?
    2. **Architecture BigLake Managed Iceberg pré-documentée** : création de la connexion Cloud Resource `biglake-gcs-conn` (`europe-west1`) et pré-création documentée des 4 tables `ICEBERG` (`cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances`, `cbk_cfonb_movements` avec rattachement `04+05`) ?
    3. **Gouvernance `RAW` sans nettoyage silencieux** : conservation intacte des anomalies métier (`66 000` dates `00000000`/`99999999`, `12,08 %` de guichets décalés `'42   '`, `650` orphelins AWS) pour `dbt` en `Démo #2`, et exécution sur **Dataproc Serverless runtime `2.2`** ?
* **Chip 2 — Connexion BigLake & DDL documenté des 4 tables Iceberg (`72` colonnes) :**
  > `Oui sur les 3 points ! Avant de lancer le batch Spark, crée la connexion BigLake et initialise dans raw_bank les 4 tables BigLake Managed Iceberg en documentant complètement le dataset, les tables et les 72 colonnes.`
  * Création de `biglake-gcs-conn` avec `roles/storage.admin` (`storage.buckets.get` requis par Storage Write API sur tables Iceberg) + `roles/biglake.admin`, exécution de [`01_demo1_raw_aggregation/sql/00_create_documented_mainframe_iceberg_tables.sql`](../01_demo1_raw_aggregation/sql/00_create_documented_mainframe_iceberg_tables.sql) et génération de [`docs/MAINFRAME_BIGQUERY_SCHEMA.md`](./MAINFRAME_BIGQUERY_SCHEMA.md).
* **Chip 3 — Batch PySpark Dataproc Serverless & script de replay :**
  > `Parfait ! Génère maintenant le job PySpark Dataproc Serverless pour décoder l'EBCDIC/COMP-3 et les CFONB multi-lignes vers ces 4 tables Iceberg, lance le batch sur europe-west1 et crée un script pour rejouer tout cela.`
  * Génération de [`01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py`](../01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py) (`sc.binaryRecords`, `unpack_comp3`, `sc.binaryFiles` parallélisé, écriture Storage Write API `writeMethod="direct"` `mode("append")`) et du script de replay idempotent [`scripts/run_demo1_mainframe_spark_iceberg.sh`](../scripts/run_demo1_mainframe_spark_iceberg.sh).
* **Chip 4 — Certification SQL post-chargement (`INFORMATION_SCHEMA` & fuite `-2,42 Md€`) :**
  > `Vérifie dans BigQuery que les 4 tables Iceberg ont les bons volumes, que les 72 colonnes sont bien documentées dans INFORMATION_SCHEMA et que la fuite vers les néobanques ressort grâce aux lignes 05.`
  * Vérification des **7 invariants** : `79 350` clients, `94 350` comptes, `2 875 062` soldes `01`/`07`, `5 500 000` mouvements `04+05`, **`72 / 72` colonnes documentées (`100 %`)**, `66 000` dates `00000000`/`99999999` préservées en `RAW` et **`-2 420 000 000,00 €`** de virements sortants `0810` vers les BIC néobanques extraits des lignes `05`.

---

### Conversation Étape 3 — Fédération AWS S3 (`Borderless Lakehouse` / Catalogue `AWS Glue`)
* Exposition sans copie des tables Iceberg `AWS Glue / S3` (`federate-lakehouse-catalog`).

### Conversation Étape 4 — Streaming Temps Réel `Pub/Sub` → `BigQuery` & Sécurité `CLS` (`IBAN` / `PII`)
* Historisation sans serveur via BigQuery Subscriptions (`raw_sepa_payments_pubsub_stream`, `raw_iban_events_pubsub_stream`), audit `PII` et masquage `CLS`.

### Conversation Étape 5 — Découverte automatique GCS PDF via `Dataplex Cloud Storage Discovery` (`Object Tables`)
* **Skills `DAK` mobilisés :** `discover-assets`, `gcp-data-pipelines`, `accidental-data-loss-prevention`, `enforcing-resource-attribution`.
* **Chip 1 — Diagnostic du bucket `RAW/` & 3 questions d'arbitrage avant lancement du scan :**
  > `On a déposé dans gs://data-days-demo-landing/RAW/ nos 250 PDF d'avenants promotionnels d'agences et nos 6 PDF réglementaires pour le CFO. Peux-tu utiliser Cloud Storage Discovery de Knowledge Catalog pour les exposer automatiquement en Object Tables dans BigQuery sans écrire de DDL ?`
  1. **Filtrage `includePatterns` strict** : verrouiller `RAW/PROMO_CONTRACTS_PDF/**` (`250` PDF) et `RAW/REGULATORY_CFO_PDF/**` (`6` PDF) pour éviter de scanner `RAW/corebanking/` (`.ebcdic` + `RUN01` `ABEND_S0C7`), `RAW/AWS/` et `iceberg/` ?
  2. **Object Table managée `data_days_demo_landing.raw` + 2 vues gouvernées dans `raw_bank`** : conserver l'Object Table BigLake auto-publiée par Discovery (`metadataCacheMode=AUTOMATIC`, colonne `ref` `ObjectRef` via `biglake-gcs-conn`) et exposer dans `raw_bank` deux vues filtrées sur `content_type = 'application/pdf'` (`raw_promo_contracts_pdf` et `raw_cfo_regulatory_pdf`) ?
  3. **Octroi CLI des 3 rôles Service Agent Dataplex & cadence** : accorder en CLI `discoveryServiceAgent`, `discoveryPublishingServiceAgent` et `discoveryBigLakePublishingServiceAgent` à `service-1051798075322@gcp-sa-dataplex.iam.gserviceaccount.com` (zéro clic manuel en console) + scan immédiat et planification quotidienne `06:00 Europe/Paris` ?
* **Chip 2 — Exécution du scan `hexagone-raw-pdf-discovery` & script de replay :**
  * Création et exécution du DataScan `data-discovery`, publication de [`01_expose_discovered_pdf_views.sql`](../01_demo1_raw_aggregation/sql/01_expose_discovered_pdf_views.sql) et script de replay [`run_demo1_gcs_pdf_discovery.sh`](../scripts/run_demo1_gcs_pdf_discovery.sh).
* **Chip 3 — Certification des 256 PDF exposés (`250` avenants `-14,30 M€` + `6` normes CFO) :**
  * Contrôle SQL de `data_days_demo_landing.raw` (`discovery_managed`), `raw_bank.raw_promo_contracts_pdf` (`250` PDF) et `raw_bank.raw_cfo_regulatory_pdf` (`6` PDF ANC/ALM/ILAAP/ACPR).

### Conversation Étape 6 — Init `dbt` & Documentation technique `Knowledge Catalog`
* Initialisation `dbt_project.yml` + `_raw_sources.yml` (`dbt-bigquery`, 10 sources dont les 2 vues PDF découvertes) et synchronisation technique initiale vers `Knowledge Catalog`.

---

## Workspaces Démos #2, #3 & #4

* **Workspace `02_demo2_silver_dbt_dq` (3 conversations)** :
  1. `1. Scan Auto Data Quality RAW` (`3,4 %` doublons, `8,1 %` `RJCT`/`PDNG`, `1,2 %` dates `00000000`, `650` orphelins AWS)
  2. `2. Modèles dbt SILVER & Tests DQ` (5 modèles + extraction PDF `AI.GENERATE_TABLE` + `24` tests `schema.yml`)
  3. `3. Build & 5 Data Products KC` (publication à `100 %` DQ PASS)
* **Workspace `03_demo3_kc_semantics_cfo` (2 conversations)** :
  1. `1. Audit Faux PNB (+42,8 M€) & Vidéos` (réconciliation catalogues legacy + interviews `.mp4`)
  2. `2. Publication KC & Vérité (-38,42 M€)` (`curate-context` OKF v0.2, 3 glossaires, `-24,12 M€` ALM + `-14,30 M€` PDF)
* **Workspace `04_demo4_scale_mobile_adk` (2 conversations)** :
  1. `1. Modèles BQML & Budget Insight` (`AI.FORECAST` reste à vivre `+300,00 €` & détection hausse `+4,00 €` Lucas Martin)
  2. `2. Synchro AlloyDB (<15ms) & ADK` (`alloydb_sync` `< 15 ms` + 3 agents mobiles `ADK`)
