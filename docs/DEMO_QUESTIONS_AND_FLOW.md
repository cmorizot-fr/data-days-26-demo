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
| **Démo #1 — Étape 3**<br>*AWS Borderless (`AWS Glue / S3`)* | `bigquery` (`execute_sql`) | `federate-lakehouse-catalog` | Fédère le catalogue Iceberg `AWS Glue / S3` dans BigQuery sans aucune copie. |
| **Démo #1 — Étape 4**<br>*Streaming `Pub/Sub` → `BQ` (`STRUCT`) & `CLS`* | `bigquery`<br>`data-agent-kit` (`render_chart`) | `discover-assets`<br>`gcp-data-pipelines`<br>`enforcing-resource-attribution`<br>`bq-visual-audit` | Branche les 2 BigQuery Subscriptions sans serveur en **`100 % Nested STRUCT`** (`--use-table-schema`), audite les PII in-database (`10` feuilles dont santé RGPD Art. 9) et applique **3 Data Policies `CLS`**. |
| **Démo #1 — Étape 5**<br>*Discovery GCS PDF (`Object Tables`)* | `bigquery`<br>`data-agent-kit` (`render_chart`) | `discover-assets`<br>`gcp-data-pipelines`<br>`accidental-data-loss-prevention`<br>`bq-visual-audit` | Exécute `Dataplex Cloud Storage Discovery` sur les `250 + 6` PDF et publie les 2 vues gouvernées (`raw_bank`). |
| **Démo #1 — Étape 6**<br>*Init `dbt` & Doc `Knowledge Catalog`* | `bigquery` | `dbt-bigquery`<br>`curate-context` | Initialise `dbt_project.yml` et `_raw_sources.yml` + synchronisation technique initiale dans `Knowledge Catalog`. |
| **Démo #2 (3 étapes)**<br>*Industrialisation `SILVER` & DQ* | `bigquery` (`execute_sql`, `get_table_info`) | `data-autocleaning`<br>`dbt-bigquery`<br>`discover-assets` | Profile les anomalies `RAW`, fait arbitrer les règles de nettoyage/réconciliation et génère les 5 Data Products `dbt` testés. |
| **Démo #3 (2 étapes)**<br>*Sémantique `KC` & Pilotage CFO* | `bigquery`<br>`data-agent-kit` (`render_chart`) | `curate-context` (`kcmd` / OKF)<br>`discover-assets`<br>`bigquery-ai-ml` | Réconcilie les catalogues legacy + interviews `.mp4`, publie le contexte certifié dans `KC` et corrige l'écart PNB de `+42,80 M€` à `-38,42 M€`. |
| **Démo #4 (2 étapes)**<br>*Scale Digital : `BQML` & `AlloyDB`* | `bigquery`<br>`data-agent-kit` | `bigquery-ai-ml`<br>`ml-best-practices`<br>`cloud-databases-onboarding` | Génère les prévisions `AI.FORECAST` / propension dans BigQuery et expose les insights en `< 15 ms` via `alloydb_sync` aux 3 agents `ADK`. |

---

## Workspace Démo #1 — `01_demo1_raw_aggregation` (6 Conversations d'étapes)

### Conversation Étape 1 — Transfert Mainframe du mois passé vers GCS `RAW`

* **Chip 1 (Prompt pré-rempli) :**
  > `Transfere les données mainframe du serveur de fichier pour le mois passé, sur GCS dans la zone RAW.`
* **Actions internes d'`AGY` + `DAK` avant de répondre :**
  1. **MCP `data-agent-kit` -> `get_active_gcp_connection`** : récupère `project_id` (`data-days-demo`) et `region` (`europe-west1`).
  2. **Skill `discover-assets` & vérification du bucket existant** : confirme que le bucket `gs://data-days-demo-landing/raw/` existe déjà (aucune demande de création de bucket).
  3. **Inspection du serveur de fichiers local sur le mois passé (`202610`)** (`00_data_generator/output/corebanking/`) : lit `MANIFEST_Z_OS_DROP.ctl`, repère les binaires `.ebcdic` (`RECFM=FB`, `CP500 + COMP-3`), les Copybooks `.cpy`, et **l'incident sur octobre 2026** (`RUN01` en `ABEND_S0C7 RC=0012` vs `RUN02_RERUN` en `RC=0000`).
* **Question d'arbitrage posée par `AGY` sur scène (1 question unique) :**
  1. **Incident sur le mois passé (`202610` : `ABEND` vs `RERUN`)** : *« Sur le serveur local, octobre 2026 comporte deux fichiers : `CFONB120_MVTS_202610_RUN01.cfonb` interrompu en crash (`STATUS=ABEND_S0C7`, `RC=0012`, `32 Mo`) et `CFONB120_MVTS_202610_RUN02_RERUN.cfonb` complet (`STATUS=OK`, `RC=0000`, `109 Mo`). On conserve les deux en zone `RAW` pour l'auditabilité CFT (et filtrer sur `RC=0000` au chargement) ou j'exclus `RUN01` dès la copie ? »*
  *(Les 2 référentiels maîtres `.ebcdic`, le bordereau `MANIFEST_Z_OS_DROP.ctl`, les 3 Copybooks `copybooks/*.cpy` et la copie binaire stricte sans transcodage vers `gs://data-days-demo-landing/raw/corebanking/202610/` avec attribution `datacloud.antigravity` sont retenus et annoncés d'office.)*
* **Chip 2 (Confirmation intervenant) :**
  > `Oui : transfère les deux fichiers d'octobre dans la zone RAW pour conserver l'auditabilité CFT, et lance la copie binaire complète vers gs://data-days-demo-landing/raw/corebanking/202610/.`
  * **Résultat & transition proactive vers l'Étape 2 :** après copie et contrôle `CRC32C` des 8 objets, `AGY` préconise **Managed Service for Apache Spark (Serverless)** pour le parsing aval (car `bq load` ne sait pas lire un flux binaire fixe `RECFM=FB` `EBCDIC CP500 + COMP-3` sans `\n`, ni filtrer sur le trailer `99CFT_TRL` `RC=0000` et recoller par position les lignes `05` sur leur `04` parent).

---

### Conversation Étape 2 — Décodage Mainframe via Dataproc Serverless Spark & BigLake Iceberg (`raw_bank`)

* **Skills `DAK` & outils mobilisés :** `discover-assets`, `gcp-data-pipelines`, `gcp-spark` (`biglake_iceberg.md`, `read_write_data.md`, `gcloud_dataproc.md`), `enforcing-resource-attribution`, `bq-visual-audit`.
* **Chip 1 — Analyse des Copybooks `.cpy` & 2 questions d'arbitrage :**
  > `Parfait, suis ta recommandation : analyse les Copybooks .cpy dans gs://data-days-demo-landing/RAW/corebanking/ et prépare le chargement via Spark Serverless vers BigQuery (raw_bank) en documentant le schéma.`
  * **Acté d'office :** rejet automatique de `202610_RUN01.cfonb` (`RC=0012`) via `99CFT_TRL` + contrôle `CHECKSUM_MVTS_04` (décision de l'Étape 1) et rattachement positionnel `CFONB 04 + 05`.
  * **2 questions d'arbitrage :**
    1. **Cible de stockage BigLake Managed Iceberg** : pré-création et documentation de 4 tables `ICEBERG` (`72` colonnes) via `biglake-gcs-conn` vs tables BigQuery natives non-Iceberg ?
    2. **Gouvernance `RAW` sans nettoyage silencieux** : conservation intacte des anomalies métier (`66 000` dates `00000000`/`99999999`, `12,08 %` guichets `'42   '`, `650` orphelins AWS) pour `dbt` en `Démo #2` + exécution sur **Dataproc Serverless runtime `2.2`** ?
* **Chip 2 — Exécution bout en bout (DDL + Batch PySpark Serverless + Certification & `bq-visual-audit`) :**
  > `Oui sur les 2 points : crée les 4 tables BigLake Managed Iceberg documentées (72 colonnes), lance le batch PySpark Serverless en préservant les anomalies RAW, puis vérifie le chargement dans BigQuery.`
  * Déroule visiblement le DDL documenté (`00_create_documented_mainframe_iceberg_tables.sql`), le **démarrage du runtime Dataproc Serverless `2.2` (`cold start` + allocation executors)**, le batch PySpark (`parse_corebanking_iceberg.py`) et la certification SQL + contrôle visuel (`79 350` clients, `94 350` comptes, `2 875 062` soldes, `5 500 000` mouvements `04+05`, `72/72` colonnes, `66 000` dates `00000000` préservées, **`-2 420 000 000,00 €`** de fuite 90j).
  * **Déclenchement réel sans impact (`--dry-run`) :** à l'envoi du Chip 2, le middleware Vite (`POST /api/trigger-spark-dryrun`) soumet réellement un batch **Dataproc Serverless PySpark (`--async --dry-run`)** sur `data-days-demo` (`europe-west1`) qui décode les vrais fichiers GCS sans aucune écriture BigQuery/Iceberg, et met à jour le lien Console GCP vers ce batch en direct.

---

### Conversation Étape 3 — Fédération AWS S3 (`Borderless Lakehouse` / Catalogue `AWS Glue`)
* Exposition sans copie des tables Iceberg `AWS Glue / S3` (`federate-lakehouse-catalog`).

### Conversation Étape 4 (`4. Flux Paiements`) — Streaming Temps Réel `Pub/Sub` → `BigQuery` (`100 % Nested STRUCT`) & Sécurité `CLS` (`IBAN` / `PII`)
* **Skills `DAK` mobilisés :** `discover-assets`, `gcp-data-pipelines`, `enforcing-resource-attribution`, `bq-visual-audit`.
* **Chip 1 — Découverte Pub/Sub & 1 question d'architecture (`askQuestions` unique) :**
  * **Acté d'office :** conservation du bruit `RAW` (`~3,4 %` retries `end_to_end_id`, `~8,1 %` `RJCT`/`PDNG`) + `sepa-payments-dlq-topic`, et maintien intact de `sepa-payments-alloydb-ops-sub` (`< 15 ms` Démo #4).
  * **Question unique :** schéma **`100 % Nested STRUCT` (`--use-table-schema`)** vs `data JSON` opaque (interdisant le CLS par sous-champ) vs pipeline Dataflow.
* **Chip 2 — Déploiement sans serveur :** création de [`02_create_documented_pubsub_nested_tables.sql`](../01_demo1_raw_aggregation/sql/02_create_documented_pubsub_nested_tables.sql) (`55/55` chemins `STRUCT` documentés) via [`setup_pubsub_queues.sh`](../scripts/setup_pubsub_queues.sh), ingestion temps réel (`503` paiements + `79` ajouts IBAN, `0` DLQ).
* **Chip 3 — Audit hybride `PII` in-database (`0` donnée brute extraite) & 1 question `CLS` (`askQuestions` unique) :** exécution de [`03_audit_pii_nested_pubsub.sql`](../01_demo1_raw_aggregation/sql/03_audit_pii_nested_pubsub.sql) détectant **10 sous-champs `STRUCT` sensibles** (`4` IBAN, `4` noms/IP, et **`12,9 %` de motifs santé/logement RGPD Art. 9** dans `remittance.unstructured_info` comme `CPAM SANTE`) → arbitrage unique sur le masquage gradué (`LAST_FOUR_CHARACTERS`, `SHA256`, `ALWAYS_NULL`) en laissant `agent_bic` en clair.
* **Chip 4 — Application chirurgicale des Policy Tags `CLS` & `bq-visual-audit` :** déploiement de la taxonomie `hexagone-cls-payments-pii` et des 3 Data Policies via [`apply_pubsub_cls_policy_tags.py`](../scripts/apply_pubsub_cls_policy_tags.py) + contrôle visuel final de couverture `CLS`.

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
* **Prérequis hors scène :** le silo Finance `raw_bank.raw_sap_gl_alm` (grand livre SAP / PCEC + budget BPC + dépôts TCI ALM, `1 200 000` lignes) est préchargé par [`load_finance_sap_bq.sh`](../scripts/load_finance_sap_bq.sh) ; il est simplement déclaré parmi les 10 sources `dbt` (aucune conversation d'ingestion dédiée).

---

## Workspaces Démos #2, #3 & #4

* **Workspace `02_demo2_silver_dbt_dq` (5 conversations)** :
  1. `1. Concevoir les data products` (2 turns) : recommandation à partir du **POS `DSI-EA-POS-2026-v3.2`** ([`banque_hexagone_pos_2026.png`](./assets/banque_hexagone_pos_2026.png)) et des `17` sources de `raw_bank` — 3 arbitrages d'urbanisation (découpage domaine vs 8 îlots POS + exclusion des 7 îlots pointillés & Zone 5 ; frontières par grain métier, MOA & isolation `CLS` des verbatims `CRC-VOX` ; nommage `snake_case` anglais + fraîcheur `dbt` + `AlloyDB` `< 15 ms`) → [`data_products_catalog.yaml`](../02_demo2_silver_dbt_dq/kc_products/data_products_catalog.yaml) (`5 SILVER + 2 GOLD`)
  2. `2. Diagnostiquer la qualité des données` (2 turns) : (a) **trouver les règles de qualité** avec l'Agentic Data Cloud — profil Dataplex, recommandations `generateDataQualityRules`, contrats Knowledge Catalog et raisonnement inter-silos de l'agent → `31` règles dans `dq_scans/dq_rules_catalog.yaml` + 3 arbitrages (où appliquer, traitement des anomalies, seuils) ; (b) les appliquer par un scan Auto Data Quality RAW (`3,4 %` doublons, `8,1 %` `RJCT`/`PDNG`, `1,2 %` dates `00000000`, `650` orphelins AWS)
  3. `3. Nettoyer & fiabiliser les données` (2 turns) : (a) diagnostic SQL des recouvrements inter-silos (`100 %` overlap `end_to_end_id`) + **3 arbitrages dans `AskQuestionTray` avant écriture** (Mainframe fait foi + enrichissement SEPA sans double comptage, `650` comptes J0 conservés et signalés, catégorisation par seed `movement_category_rules`) ; (b) génération des vrais modèles `dbt` structurés et de leurs **`82` tests `schema.yml`**
  4. `4. Extraire les engagements des PDF` (2 turns) : (a) prototypage sur `raw_promo_contracts_pdf` révélant `63 / 250` échecs naïfs (`10,46 M€` vs `14,30 M€`) + **3 arbitrages dans `AskQuestionTray`** (extraction hybride avec lien `ObjectRef`, durcissement température `0` + reprise incrémentale, type déduit du compte PCEC via `promo_types`) ; (b) extraction certifiée `250 / 250` PDF = `14 300 000,00 €` (`OBJ.MAKE_REF` sous VPC-SC), vue `promo_contracts_pdf_tracking` et **`22 / 22` tests PASS**
  5. `5. Publier les 5 produits de données` : `dbt build --select +path:models/silver` (**`104 / 104` tests PASS** = `82` structurés + `22` PDF), `bq-visual-audit` et publication complète (Overview, Contracts, Insights) vers la **Data Marketplace Knowledge Catalog (`http://localhost:5174/data-products`)**
* **Workspace `03_demo3_kc_semantics_cfo` (2 conversations)** :
  1. `1. Comprendre le faux PNB (+42,8 M€)` (réconciliation catalogues legacy + interviews `.mp4`)
  2. `2. Certifier la vraie marge (-38,42 M€)` (`curate-context` OKF v0.2, 3 glossaires, `-24,12 M€` ALM + `-14,30 M€` PDF)
* **Workspace `04_demo4_scale_mobile_adk` (2 conversations)** :
  1. `1. Anticiper le budget & proposer l'offre` (`AI.FORECAST` reste à vivre `+300,00 €` & détection hausse `+4,00 €` Lucas Martin)
  2. `2. Servir l'app mobile en temps réel` (`alloydb_sync` `< 15 ms` + 3 agents mobiles `ADK`)
