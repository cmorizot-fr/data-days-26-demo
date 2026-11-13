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

### Conversation Étape 2 — Parsing Spark vers BigLake Iceberg (`raw_bank`)

* **Chip 1 :** `Explore les fichiers Mainframe déposés dans gs://data-days-demo-landing/raw/corebanking/ et leurs copybooks .cpy pour en faire des tables BigQuery Iceberg dans raw_bank.`
* **3 questions posées par `AGY` (`gcp-spark`) :**
  1. Filtrage automatique sur `99CFT_TRL` `RC=0000` + `CHECKSUM_MVTS_04` (écartant `202610_RUN01.cfonb`) ?
  2. Rattachement par fenêtre d'ordre physique (`LEAD`) des lignes complémentaires `05` (`BIC` + `EndToEndId`) sur leur mouvement `04` et écriture de 4 tables **BigLake Managed Iceberg** (`cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances`, `cbk_cfonb_movements`) ?
  3. Conservation intacte en `RAW` des anomalies de valeurs métier (`00000000`, codes guichets `'42   '`) pour `dbt` en Démo #2 + confirmation du profil `Spark Connect` ?
* **Chip 2 :** confirmation et exécution de `parse_corebanking_iceberg.py` sur `ManagedSparkSession`.

---

### Conversation Étape 3 — Fédération AWS S3 (`Borderless Lakehouse`) & Contrats PDF (`Object Tables`)
* Exposition sans copie des tables Iceberg `AWS Glue / S3` (`federate-lakehouse-catalog`) et indexation des `250` avenants PDF via **Object Table** BigLake.

### Conversation Étape 4 — Init `dbt` & Documentation technique `Knowledge Catalog`
* Initialisation `dbt_project.yml` + `_raw_sources.yml` (`dbt-bigquery`) et synchronisation technique initiale vers `Knowledge Catalog`.

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
