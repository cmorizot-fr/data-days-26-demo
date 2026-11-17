# Paris Data Summit 2026 — Agentic Data Cloud Demo (*Banque Hexagone*)

Dépôt de démonstration de bout en bout illustrant la transformation d'un SI bancaire siloté (**Banque Hexagone**) vers une plateforme gouvernée sur **Google's Agentic Data Cloud**, pilotée de manière interactive par **Antigravity (`AGY`)** et le plugin **Data Agent Kit (`DAK`)**.

---

## 🎯 Vision & Fil rouge métier

La **Banque Hexagone** (`80 000` clients, `95 000` comptes, `450` agences sur `8` régions) fait face à un paradoxe apparent : **aucune clôture de compte sur le trimestre** (`+15 000` ouvertures récentes), mais une **fuite silencieuse de `2,42 Md€` de dépôts à vue** vers des néobanques et courtiers (dont `68,0 %` chez les `18-32 ans` entre le 1er et le 5 du mois) qui dégrade lourdement sa marge nette (**PNB**).

La démonstration se déroule en **4 actes** (chacun représenté par un **Workspace** dédié dans `stage_ui`, découpé en **1 conversation par étape**) :

| Acte | Objectif technique & métier | Briques Google Cloud, `DAK` & Skills |
| :--- | :--- | :--- |
| **Démo #1**<br>*Agrégation `RAW`* | Transférer le drop Mainframe z/OS (`EBCDIC CP500 + COMP-3`, rejet du batch `ABEND_S0C7`), décoder via **Dataproc Serverless Spark** vers **4 tables BigLake Managed Iceberg** (`72` colonnes documentées), fédérer **AWS S3 / Glue** sans copie, ingérer les flux **Pub/Sub SEPA** avec **CLS**, découvrir sans DDL les `250 + 6` **PDF** via **Dataplex Cloud Storage Discovery**, et initialiser `dbt`. | `BigLake Iceberg`, `Dataproc Serverless Spark`, `Lakehouse Federation (AWS Glue)`, `Pub/Sub → BQ + CLS`, `Dataplex Cloud Storage Discovery` (`Object Tables`), `dbt-bigquery`, `bq-visual-audit` |
| **Démo #2**<br>*Couche `SILVER` & DQ* | Scanner les anomalies `RAW` avec **Dataplex Auto Data Quality**, industrialiser le nettoyage dans `dbt` (`3,4 %` doublons `end_to_end_id`, `8,1 %` rejets `RJCT`/`PDNG`, `1,2 %` dates `00000000`, `650` comptes AWS J0), structurer les `250` PDF (`-14,30 M€`) via `AI.GENERATE_TABLE` et publier **5 Data Products** certifiés (`100 %` DQ). | `data-autocleaning`, `dbt-bigquery`, `bigquery-ai-ml` (`AI.GENERATE_TABLE`), `Knowledge Catalog`, `bq-visual-audit` |
| **Démo #3**<br>*Sémantique & CFO* | Extraire la doctrine métier depuis les exports legacy et 2 vidéos d'interviews (`.mp4`), publier 3 glossaires OKF dans **Knowledge Catalog** et démontrer l'écart critique de PNB : **`+42,80 M€`** en SQL naïf contre **`-38,42 M€`** certifié (refinancement ALM `-24,12 M€` + avenants PDF `-14,30 M€` + 2 alertes de seuils ILAAP/Risques). | `curate-context` (`OKF v0.2` / `kcmd`), `Knowledge Catalog`, `BigQuery Data Agents`, `bq-visual-audit` |
| **Démo #4**<br>*Scale Mobile & ADK* | Prédire le reste à vivre fin de mois (`AI.FORECAST` TimesFM) et les dérives d'abonnements sur `80 000` clients (`CUST00002026` Lucas Martin : `+300,00 €` → *Livret Boost 4 %*), puis synchroniser vers **AlloyDB** (`< 15 ms`, `p99 = 8,4 ms`) pour servir 3 agents mobiles **ADK**. | `bigquery-ai-ml` (`AI.FORECAST`), `AlloyDB` (`alloydb_sync`), `ADK`, `bq-visual-audit` |

---

## 📊 Skill Workspace : Contrôle Visuel Systématique (`bq-visual-audit`)

Ce repository embarque un skill personnalisé Antigravity dans [`.agents/skills/bq-visual-audit/SKILL.md`](./.agents/skills/bq-visual-audit/SKILL.md) :
- **Principe :** aucune création ou exposition de table/vue/Data Product dans BigQuery ne s'arrête à un simple `COUNT(*)` textuel. `AGY` enchaîne automatiquement une requête de contrôle consolidée et un rendu graphique inline via **`MCP data-agent-kit/render_chart`**.
- **Visibilité sur scène :**
  1. Dans le menu **`Customizations`** (`Marketplace` & `Installed`), la fiche **`bq-visual-audit` (`Workspace Skill · Always Active`)** est consultable à côté du plugin **Data Agent Kit**.
  2. Dans le **Chat**, **7 étapes** affichent une carte interactive `VisualCheckCard` (tuiles KPI en luminance de surface, barres de répartition/waterfall et, sur l'étape **Discovery GCS PDF**, **4 vignettes réelles de PDF cliquables avec zoom plein écran**). Cliquer sur le badge `bq-visual-audit · render_chart` d'une carte ouvre directement la définition du skill.

## 🧩 Skill Workspace : Ajouter une étape à la démo (`stage-ui-step-authoring`)

Pour faire apparaître de nouvelles données, de nouveaux modèles `dbt` ou de nouveaux Data Products dans l'interface scénique, demandez simplement à `AGY` d'ajouter l'étape : il applique le skill [`.agents/skills/stage-ui-step-authoring/SKILL.md`](./.agents/skills/stage-ui-step-authoring/SKILL.md).
- **Principe :** l'UI raconte ce qui s'est réellement passé — chiffres, fichiers, traces et logs issus d'exécutions réelles.
- **Conventions :** noms d'étapes fonctionnels et numérotés, 2 à 3 questions d'arbitrage avec l'option `(Recommended)` en tête, code affiché généré depuis le repo.
- **Outils :**
  ```bash
  uv run --frozen python .agents/skills/stage-ui-step-authoring/scripts/render_file_block.py <fichier>   # bloc de code réel pour filesChanged
  node .agents/skills/stage-ui-step-authoring/scripts/check_demo_config.mjs                            # validation du scénario
  ```

---

## 🖥️ Déployer en local l'interface scénique (`stage_ui`)

Le dossier [`stage_ui/`](./stage_ui) contient une application **React 18 + TypeScript + Vite + Tailwind CSS v4** reproduisant l'expérience scénique d'**Antigravity** équipée de **Data Agent Kit (`DAK`)** et du skill **`bq-visual-audit`**.

### Prérequis
- **Node.js** `>= 18` (recommandé : `20 LTS` ou `22 LTS`) et **npm**.

### 1. Lancement en mode développement (avec Hot Reload YAML)

```bash
cd stage_ui
npm install
npm run dev
```

L'interface est accessible sur 👉 **[http://localhost:5173](http://localhost:5173)**

### 2. Build de production & prévisualisation hors-ligne

```bash
cd stage_ui
npm run build
npm run preview
```

### 3. Édition sans code des scénarios (`demo_config.yaml`)
- L'intégralité des Workspaces, étapes, prompts pré-remplis (`chips`), questions d'arbitrage d'`AGY`, traces d'outils MCP/CLI, diffs de fichiers et blocs graphiques `visualCheck` est centralisée dans **[`stage_ui/public/demo_config.yaml`](./stage_ui/public/demo_config.yaml)**.
- Sous `npm run dev`, toute modification du YAML est prise en compte instantanément ; sur un build statique (`dist/demo_config.yaml`), un simple rafraîchissement navigateur (`F5`) recharge la configuration.
- **Contrôles Speaker (`⋮` en haut à droite)** : réglage de la vitesse d'animation (`0.5×` scène, `1×` normale, `3×` répétition rapide) et remise à zéro par étape ou globale.

---

## 🐍 Génération déterministe des données multi-silos (`seed=2026`)

Tous les générateurs Python s'appuient sur un univers client partagé (`shared_universe.py`, `seed=2026`) garantissant des invariants financiers vérifiables au centime près d'un silo à l'autre.

### Prérequis
- **Python** `>= 3.11, < 3.14`
- **[uv](https://docs.astral.sh/uv/)** pour la gestion de l'environnement virtuel (`pyproject.toml`)

### Générer l'ensemble des silos (et synchroniser vers GCS `RAW/`)

```bash
# 1. Configurer les variables d'environnement locales (GCP_PROJECT_ID=data-days-demo, etc.)
cp .env.example .env

# 2. Installer l'environnement Python isolé
uv sync

# 3. Tout générer en local + uploader vers gs://data-days-demo-landing/RAW/
./scripts/generate_all_data.sh

# Optionnel : générer uniquement en local sans upload GCS
./scripts/generate_all_data.sh --local-only
```

Vous pouvez également exécuter chaque générateur individuellement :

| Silo simulé | Commande individuelle | Sortie locale (`00_data_generator/output/`) |
| :--- | :--- | :--- |
| **Univers maître partagé** (`80k` clients, `95k` comptes) | `uv run python 00_data_generator/shared_universe.py` | `data/universe/*.parquet` |
| **Mainframe z/OS** (`EBCDIC CP500 + COMP-3`, `CFONB 120` 18 mois + `ABEND_S0C7`) | `uv run python 00_data_generator/generate_mainframe_cfonb.py` | `output/corebanking/` + `copybooks/*.cpy` |
| **Validation Mainframe** (contrôle binaire & invariants) | `uv run python 00_data_generator/validate_corebanking.py` | Audit console (`7/7` invariants) |
| **AWS S3 CRM** (`80k` clients, `320k` notes, `650` orphelins J0) | `uv run python 00_data_generator/generate_aws_crm_s3.py` | `output/RAW/AWS/` |
| **Flux Paiements SEPA & IBAN** (`3,4 %` doublons, `8,1 %` `RJCT`/`PDNG`) | `uv run python 00_data_generator/generate_payments_stream.py` | `output/RAW/PAYMENTS/` |
| **Corpus PDF** (`250` avenants agences `-14,30 M€` + `6` normes CFO/ACPR) | `uv run python 00_data_generator/generate_promo_pdfs.py` | `output/RAW/PROMO_CONTRACTS_PDF/` & `REGULATORY_CFO_PDF/` |
| **Finance SAP / PCEC & ALM** (`1,2 M` lignes : naïf `+42,80 M€`, signé `-24,12 M€`) | `uv run python 00_data_generator/generate_finance_sap_alm.py` | `output/RAW/FINANCE_SAP_ALM/` + `output/bq_schemas/` |

Pour nettoyer proprement les fichiers générés en local et/ou sur GCS :
```bash
./scripts/clean_all_data.sh --local-only   # ou --all pour vider aussi GCS RAW/
```

---

## ☁️ Scripts d'exécution réelle sur Google Cloud (`Démo #1`)

Les pipelines de la **Démo #1** disposent de scripts idempotents prêts à être joués en live sur le projet `data-days-demo` (`europe-west1`) avec attribution `datacloud.antigravity` :

### 1. Décodage Mainframe via Dataproc Serverless Spark → BigLake Managed Iceberg
```bash
# Provisionne la connexion BigLake, pré-crée et documente les 4 tables Iceberg (72 colonnes),
# soumet le batch PySpark Serverless 2.2 et certifie les 7 invariants SQL dans raw_bank :
./scripts/run_demo1_mainframe_spark_iceberg.sh

# Variante rapide si les ~969 Mo binaires sont déjà présents sur GCS :
./scripts/run_demo1_mainframe_spark_iceberg.sh --skip-upload
```

### 2. Découverte automatique des PDF sur GCS → Object Tables BigLake (Zéro DDL)
```bash
# Accorde en CLI les rôles au Service Agent Dataplex, crée et lance le DataScan
# Cloud Storage Discovery (hexagone-raw-pdf-discovery), attend la publication automatique
# de l'Object Table BigLake (data_days_demo_landing.raw) et expose les 2 vues dans raw_bank :
./scripts/run_demo1_gcs_pdf_discovery.sh
```

### 3. Streaming Temps Réel Pub/Sub `100 % Nested STRUCT` → BigQuery & Sécurité `CLS`
```bash
# Replay complet : tables BigQuery 100 % Nested STRUCT (55/55 chemins documentés),
# BigQuery Subscriptions (--use-table-schema + DLQ), audit PII hybride in-database
# et application des 3 Data Policies CLS (LAST_FOUR_CHARACTERS, SHA256, ALWAYS_NULL) :
./scripts/run_demo1_pubsub_bq_cls.sh --recreate-schema --burst 500

# Émission unitaire des événements temps réel Jour J du client témoin (CUST00002026) :
uv run python 00_data_generator/stream_payments_pubsub.py --witness-live
```

### 4. Historique Paiements 18 mois ↔ Temps réel (vue unifiée certifiée)
```bash
# Expose sans copie l'archive Parquet (6,2 M lignes) en tables BigLake, crée les vues
# raw_sepa_payments_unified / raw_iban_events_unified, rejoue le temps réel + CLS sur les 4 tables,
# puis certifie 12 contrôles (continuité, fuite 2,42 Md€, rapprochement Mainframe CFONB, IBAN) :
./scripts/run_demo1_payments_history_unified.sh --recreate-schema --burst 500

# Contrôle local de cohérence historique <-> temps réel (sans GCP) :
uv run python 00_data_generator/validate_payments_coherence.py
```

### 5. SaaS CRM en Apache Iceberg sur GCS (simulation AWS Glue / S3)
```bash
# Publie les 4 tables CRM en vraies tables Iceberg (PyIceberg) sous gs://<bucket>/RAW/AWS_SAAS_ICEBERG/,
# les expose en lecture seule dans raw_bank.aws_crm_* et certifie 14 contrôles (dont 650 orphelins vs Mainframe) :
./scripts/run_demo1_aws_crm_iceberg.sh
```

### 6. Grand livre SAP / PCEC & dépôts ALM → `raw_bank.raw_sap_gl_alm` (chargement direct, hors scène)
```bash
# bq load --replace du Parquet synchronisé sur GCS, documentation des 17 colonnes
# et contrôle des invariants (1 200 000 lignes, naïf +42 800 000.00, signé hors 58* -24 120 000.00).
# Appelé automatiquement par generate_all_data.sh après la synchronisation GCS :
./scripts/load_finance_sap_bq.sh
```

---

## 📂 Structure du repository

```text
.
├── DESIGN_AND_CONTEXT.md                     # Blueprint d'architecture complet & invariants chiffrés
├── AGENTS.md                                 # Règles strictes pour Antigravity (AGY) & Data Agent Kit (DAK)
├── .agents/
│   └── skills/
│       ├── bq-visual-audit/SKILL.md          # Skill Workspace de contrôle visuel post-création BigQuery
│       └── stage-ui-step-authoring/          # Skill Workspace d'ajout d'étapes dans l'UI de démo (+ scripts/)
├── docs/
│   ├── DEMO_QUESTIONS_AND_FLOW.md            # Script conversationnel détaillé & skills DAK par étape
│   ├── MAINFRAME_BIGQUERY_SCHEMA.md          # Dictionnaire des 4 tables BigLake Iceberg & 72 colonnes
│   └── assets/                               # Schémas d'architecture & supports visuels
├── stage_ui/                                 # Interface web scénique (React 18 + Vite + Tailwind v4)
│   ├── public/
│   │   ├── demo_config.yaml                  # Configuration YAML éditable à chaud (incl. askQuestions)
│   │   └── assets/pdf_previews/              # Vignettes haute résolution des PDF découverts (zoom UI)
│   └── src/                                  # Composants ChatStage, AskQuestionTray, VisualCheckCard
├── 00_data_generator/                        # Générateurs déterministes multi-silos (seed=2026)
│   ├── shared_universe.py                    # Univers partagé (80k clients, 95k comptes, 450 agences)
│   ├── customer_ledger.py                    # Journal partagé de la vie client (source unique Mainframe + SEPA)
│   ├── generate_mainframe_cfonb.py           # Mainframe EBCDIC CP500 + COMP-3 & relevés CFONB 120
│   ├── generate_aws_crm_s3.py                # CRM AWS S3 Parquet & 650 comptes récents J0
│   ├── generate_payments_stream.py           # Archive 18 mois Parquet 100 % Nested STRUCT (6,2 M lignes)
│   ├── generate_promo_pdfs.py                # 250 PDF d'avenants agences (-14,30 M€) + 6 PDF CFO
│   ├── generate_finance_sap_alm.py           # Grand livre SAP / PCEC + budget + TCI ALM (1,2 M lignes)
│   ├── stream_payments_pubsub.py             # Producteur temps réel Nested STRUCT vers Cloud Pub/Sub
│   ├── validate_corebanking.py               # Vérification locale des invariants Core Banking
│   ├── verify_invariants.py                  # Contrôle croisé inter-silos (univers, AWS, paiements, Finance, PDF)
│   └── copybooks/                            # Copybooks COBOL (.cpy) des fichiers Mainframe
├── 01_demo1_raw_aggregation/                 # Acte 1 : Agrégation RAW sans copie inutile
│   ├── spark/parse_corebanking_iceberg.py    # Job PySpark Dataproc Serverless -> BigLake Iceberg
│   └── sql/
│       ├── 00_create_documented_mainframe_iceberg_tables.sql
│       ├── 01_expose_discovered_pdf_views.sql
│       ├── 02_create_documented_pubsub_nested_tables.sql
│       └── 03_audit_pii_nested_pubsub.sql
├── 02_demo2_silver_dbt_dq/                   # Acte 2 : Modèles dbt SILVER, Auto DQ & Data Products KC
├── 03_demo3_kc_semantics_cfo/                # Acte 3 : Glossaires Knowledge Catalog (OKF) & PNB CFO
├── 04_demo4_scale_mobile_adk/                # Acte 4 : BQML AI.FORECAST, AlloyDB (<15ms) & agents ADK
├── scripts/
│   ├── generate_all_data.sh                  # Orchestration complète des générateurs + sync GCS RAW/
│   ├── run_demo1_mainframe_spark_iceberg.sh  # Replay complet Spark Serverless -> BigLake Iceberg
│   ├── run_demo1_gcs_pdf_discovery.sh        # Replay complet Dataplex GCS PDF Discovery -> Object Tables
│   ├── run_demo1_pubsub_bq_cls.sh            # Replay complet Pub/Sub Nested STRUCT -> Audit PII -> CLS
│   ├── apply_pubsub_cls_policy_tags.py       # Déploiement Taxonomie & 3 Data Policies CLS sur STRUCT
│   ├── setup_pubsub_queues.sh                # Provisionnement Pub/Sub & BigQuery Subscriptions (--use-table-schema)
│   ├── clean_all_data.sh                     # Nettoyage propre des données locales et/ou GCS
│   └── reset_demo_state.sh                   # Remise à zéro entre répétitions
├── pyproject.toml                            # Configuration Python & dépendances (uv)
└── .env.example                              # Modèle des variables d'environnement GCP / AWS / AlloyDB
```

---

## 📚 Documentation de référence

- **[`DESIGN_AND_CONTEXT.md`](./DESIGN_AND_CONTEXT.md)** : contexte métier détaillé, architecture cible, anomalies `RAW` injectées et formules exactes des invariants financiers.
- **[`docs/DEMO_QUESTIONS_AND_FLOW.md`](./docs/DEMO_QUESTIONS_AND_FLOW.md)** : déroulé pas-à-pas sur scène, questions d'arbitrage posées par `AGY` et cartographie des skills `DAK` mobilisés.
- **[`docs/MAINFRAME_BIGQUERY_SCHEMA.md`](./docs/MAINFRAME_BIGQUERY_SCHEMA.md)** : dictionnaire complet du dataset `raw_bank`, des 4 tables **BigLake Managed Iceberg** (`cbk_*`) et de leurs `72` colonnes documentées.
- **[`.agents/skills/bq-visual-audit/SKILL.md`](./.agents/skills/bq-visual-audit/SKILL.md)** : protocole du skill de contrôle visuel post-création BigQuery (`render_chart` + aperçu documentaire `ObjectRef`).
- **[`.agents/skills/stage-ui-step-authoring/SKILL.md`](./.agents/skills/stage-ui-step-authoring/SKILL.md)** : méthode et outils pour ajouter une étape de démo dans `stage_ui` à partir du réel (validateur `check_demo_config.mjs`).
- **[`AGENTS.md`](./AGENTS.md)** : garde-fous techniques, UX et conventions que tout agent IA intervenant sur ce dépôt doit respecter.
