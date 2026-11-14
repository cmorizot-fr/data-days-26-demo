# Paris Data Summit 2026 — Agentic Data Cloud Demo (*Banque Hexagone*)

Dépôt de démonstration de bout en bout illustrant la transformation d'un SI bancaire siloté (**Banque Hexagone**) vers une plateforme gouvernée sur **Google's Agentic Data Cloud**, pilotée de manière interactive par **Antigravity (`AGY`)** et le plugin **Data Agent Kit (`DAK`)**.

---

## 🎯 Vision & Fil rouge métier

La **Banque Hexagone** (`80 000` clients, `95 000` comptes, `450` agences sur `8` régions) fait face à un paradoxe apparent : **aucune clôture de compte sur le trimestre** (`+15 000` ouvertures récentes), mais une **fuite silencieuse de `2,42 Md€` de dépôts à vue** vers des néobanques et courtiers (dont `68 %` chez les `18-32 ans` entre le 1er et le 5 du mois) qui dégrade lourdement sa marge nette (**PNB**).

La démonstration se déroule en **4 actes** :

| Acte | Objectif technique & métier | Briques Google Cloud & `DAK` |
| :--- | :--- | :--- |
| **Démo #1**<br>*Agrégation `RAW`* | Diagnostiquer un drop Mainframe z/OS (`EBCDIC CP500 + COMP-3`, détection d'un batch en `ABEND_S0C7`), parser vers **BigLake Managed Iceberg**, fédérer **AWS S3** sans copie et exposer `250` contrats PDF. | `BigLake Iceberg`, `Managed Spark`, `BigQuery Omni`, `Object Tables`, `dbt` |
| **Démo #2**<br>*Couche `SILVER` & DQ* | Industrialiser le nettoyage dans `dbt` (doublons `end_to_end_id`, rejets `RJCT`/`PDNG`, dates `00000000`, `650` comptes orphelins inter-cloud) et publier des Data Products. | `dbt-bigquery`, `Data Quality`, `Knowledge Catalog` |
| **Démo #3**<br>*Sémantique & CFO* | Réconcilier les formules métier contradictoires et démontrer l'écart critique sur le PNB trimestriel : **`+42,80 M€`** en requête SQL naïve contre **`-38,42 M€`** avec la vue certifiée `Knowledge Catalog` (coût ALM `-24,12 M€` + primes PDF `-14,30 M€`). | `Knowledge Catalog` (`OKF` / `kcmd`), `BigQuery Data Agents` |
| **Démo #4**<br>*Scale Mobile Temps Réel* | Calculer la propension d'épargne avec `BQML` / `AI SQL` et synchroniser les agrégats vers **AlloyDB** (`< 15 ms`) pour alimenter un conseiller mobile temps réel. | `BQML`, `AlloyDB` (`alloydb_sync`), `ADK` |

---

## 🖥️ Déployer en local l'interface de démo (`stage_ui`)

Le dossier [`stage_ui/`](./stage_ui) contient une application **React 18 + TypeScript + Vite + Tailwind CSS v4** reproduisant fidèlement l'expérience scénique d'**Antigravity** équipée du plugin **Data Agent Kit (`DAK`)** (support visuel autonome pour les répétitions et le backup sur scène).

### Prérequis
- **Node.js** `>= 18` (recommandé : `20 LTS` ou `22 LTS`) et **npm**.

### 1. Installation & lancement en mode développement

```bash
cd stage_ui
npm install
npm run dev
```

L'interface est immédiatement accessible dans le navigateur sur :
👉 **[http://localhost:5173](http://localhost:5173)**

### 2. Build de production & prévisualisation locale

Pour tester le bundle statique optimisé tel qu'il serait servi hors-ligne le jour J :

```bash
cd stage_ui
npm run build
npm run preview
```

### 3. Prise en main de l'interface scénique
- **Barre latérale `Workspaces` (`Démo #1` à `Démo #4`)** : **1 Workspace par Démo** et, à l'intérieur de chaque Workspace, **1 Conversation distincte par étape de la démo**.
- **Exécution interactive guidée** : cliquez sur la suggestion de prompt pré-remplie (ou appuyez sur `Tab`) puis envoyez le message pour dérouler en temps réel les appels MCP, les skills `DAK` mobilisés, les questions d'arbitrage d'`AGY` et les résultats chiffrés.
- **Vue `Customizations` (`Settings` / `Plugins`)** : permet d'inspecter sur scène le contenu du plugin **Data Agent Kit (`DAK`)** (skills spécialisés BigQuery/Spark/dbt/KC et serveurs MCP connectés).
- **Panneau latéral `Overview` (droite)** : affiche dynamiquement les sous-agents actifs, l'inspecteur des fichiers générés (modèles SQL `dbt`, scripts PySpark, bundles `OKF`) et les journaux de commandes terminales.
- **Contrôles Speaker** :
  - **Mode `Fast` (`⚡`)** : accélère (`×3`) l'animation des traces d'outils pendant les répétitions.
  - **`Reset`** : remet à zéro la conversation du scénario courant en un clic.
- **Configuration éditable sans toucher au code (`stage_ui/public/demo_config.yaml`)** : l'intégralité des Workspaces, étapes, prompts pré-remplis, questions d'`AGY`, traces et extraits de code se modifie dans [`stage_ui/public/demo_config.yaml`](./stage_ui/public/demo_config.yaml) (rechargement instantané sous `npm run dev`, ou simple `F5` sur `dist/demo_config.yaml` après build).

---

## 🐍 Environnement Python & Générateur de données (`seed=2026`)

Le générateur local produit des fichiers déterministes au centime près (incluant les fichiers binaires Mainframe z/OS `EBCDIC CP500` + décimaux condensés `COMP-3` et relevés `CFONB 120`).

### Prérequis
- **Python** `>= 3.11, < 3.14`
- **[uv](https://docs.astral.sh/uv/)** pour la gestion rapide de l'environnement et des dépendances

### Installation & génération Core Banking

```bash
# 1. Créer le fichier d'environnement local à partir du modèle
cp .env.example .env

# 2. Synchroniser l'environnement virtuel Python via uv
uv sync

# 3. Générer le drop Mainframe z/OS (clients, comptes EBCDIC, relevés CFONB 120 & copybooks)
uv run python 00_data_generator/generate_mainframe_cfonb.py

# 4. Vérifier les invariants métier et techniques au centime près
uv run python 00_data_generator/validate_corebanking.py
```

> Les fichiers générés sont écrits dans `00_data_generator/output/` (ignoré par Git afin de ne pas alourdir le dépôt).

### Rejouer le chargement Mainframe via Dataproc Serverless Spark → BigLake Iceberg (`Démo #1`)

```bash
# Transfère le drop binaire sur GCS (RAW/corebanking/), crée et documente les 4 tables
# BigLake Managed Iceberg dans BigQuery (raw_bank), lance le batch PySpark Serverless
# et contrôle les volumétries + invariants au centime près :
./scripts/run_demo1_mainframe_spark_iceberg.sh

# Optionnel : rejouer uniquement le DDL + batch Spark sans ré-uploader les ~980 Mo sur GCS
./scripts/run_demo1_mainframe_spark_iceberg.sh --skip-upload
```

---

## 📂 Structure du repository

```text
.
├── DESIGN_AND_CONTEXT.md              # Blueprint d'architecture complet & invariants chiffrés
├── AGENTS.md                          # Règles strictes pour Antigravity (AGY) & Data Agent Kit (DAK)
├── docs/
│   ├── DEMO_QUESTIONS_AND_FLOW.md     # Script conversationnel détaillé & skills DAK par tour
│   ├── MAINFRAME_BIGQUERY_SCHEMA.md   # Documentation complète des tables & colonnes Mainframe BigQuery
│   └── assets/                        # Schémas d'architecture & supports visuels
├── stage_ui/                          # Interface web locale de démonstration (React + Vite + Tailwind v4)
├── 00_data_generator/                 # Générateur déterministe (seed=2026) & copybooks COBOL (.cpy)
├── 01_demo1_raw_aggregation/          # Job PySpark Serverless, DDL BigLake Iceberg, Omni, PDF, init dbt
├── 02_demo2_silver_dbt_dq/            # Modèles dbt SILVER, tests Data Quality & Data Products KC
├── 03_demo3_kc_semantics_cfo/         # Glossaires Knowledge Catalog (OKF) & réconciliation PNB CFO
├── 04_demo4_scale_mobile_adk/         # BQML, synchronisation AlloyDB & agent mobile ADK
├── scripts/
│   ├── generate_all_data.sh           # Génération déterministe complète + synchronisation GCS RAW/
│   ├── run_demo1_mainframe_spark_iceberg.sh # Replay complet Spark Serverless -> BigLake Iceberg (raw_bank)
│   ├── run_demo1_gcs_pdf_discovery.sh # Découverte auto Dataplex GCS PDF -> BigLake Object Tables + vues
│   ├── setup_pubsub_queues.sh         # Provisionnement Pub/Sub & BigQuery Subscriptions temps réel
│   ├── clean_all_data.sh              # Nettoyage des données locales et/ou GCS
│   └── reset_demo_state.sh            # Script de remise à zéro de l'environnement entre répétitions
├── pyproject.toml                     # Configuration Python & dépendances (uv)
└── .env.example                       # Modèle des variables d'environnement GCP / AWS / AlloyDB
```

## 📚 Documentation de référence

- **[`DESIGN_AND_CONTEXT.md`](./DESIGN_AND_CONTEXT.md)** : contexte métier détaillé, architecture cible, anomalies `RAW` injectées et formules exactes des invariants financiers.
- **[`docs/DEMO_QUESTIONS_AND_FLOW.md`](./docs/DEMO_QUESTIONS_AND_FLOW.md)** : déroulé pas-à-pas sur scène, questions d'arbitrage posées par `AGY` et cartographie des skills `DAK` mobilisés.
- **[`docs/MAINFRAME_BIGQUERY_SCHEMA.md`](./docs/MAINFRAME_BIGQUERY_SCHEMA.md)** : dictionnaire complet des datasets, des 4 tables **BigLake Managed Iceberg** (`cbk_*`) et de leurs 72 colonnes documentées dans BigQuery.
- **[`AGENTS.md`](./AGENTS.md)** : garde-fous techniques et conventions que tout agent IA intervenant sur ce dépôt doit respecter.
