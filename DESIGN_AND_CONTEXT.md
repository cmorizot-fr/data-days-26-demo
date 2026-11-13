# Paris Data Summit 2026 — Design & contexte projet (Antigravity)

> [!IMPORTANT]
> Ce document sert à la fois de **blueprint d'architecture** pour la Squad démo et de **fichier de contexte de référence (`DESIGN.md` / `AGENTS.md`) pour Antigravity (`AGY`)** et le **Data Agent Kit (`DAK`)**. Il décrit le contexte métier, les silos sources simulés, l'architecture cible sur Google Data Cloud, le déroulé des 4 démos live et les invariants chiffrés que les jeux de données et pipelines doivent respecter.

---

## 1. Contexte métier & fil rouge de la plénière

### L'entreprise fictive & le double électrochoc du CEO
Nous simulons le système d'information d'une **grande banque de détail française** (80 000 clients représentatifs à l'échelle démo, 450 agences réparties sur 8 régions). En moins de 12 heures, le Directeur Général (CEO) vit deux chocs :

1. **En interne — Le « gap de chiffres » du CFO :**
   * Le **rapport commercial (CRM réseau & call center)** annonce : **`0 %` d'attrition**, tous les comptes courants jeunes/actifs toujours ouverts, et **`+15 000` nouveaux comptes** sur le trimestre.
   * Le **rapport finance & trésorerie (CFO / ALM)** constate une hémorragie : **`2,42 Md€` de dépôts à vue évaporés en 90 jours**, obligeant la banque à se refinancer au taux interbancaire (€STR), et une **marge nette d'intérêt (PNB) qui décroche de `-38,42 M€`** par rapport au budget.
   * **Explication métier (*churn silencieux*) :** les clients ne ferment plus leur compte historique, mais dès que leur salaire tombe entre le 1er et le 5 du mois, ils **transfèrent leurs liquidités en 10 secondes par virement SEPA Instant** vers des néobanques et courtiers en ligne. Les données étant éclatées entre Mainframe batch, flux paiements, SaaS CRM sur AWS, base Finance SAP/PCEC et contrats PDF, il faut 3 semaines d'Excel aux équipes du CFO pour comprendre la fuite.
2. **En externe — L'expérience mobile temps réel :**
   * Le soir même, le fils du CEO lui montre sur son smartphone comment une néobanque affiche instantanément *« Ce qui s'est passé depuis votre dernière connexion »*, anticipe son budget de fin de mois et lui propose d'épargner en un clic.

### Le mandat confié à la Squad
Bâtir sur **Google's Agentic Data Cloud** un socle unique, sans copie inutile, gouverné de bout en bout, capable à la fois :
* de **fiabiliser et réconcilier les KPI du CFO au centime près** dans `Gemini Enterprise` (avec économie massive de tokens),
* et de **passer à l'échelle côté digital** avec des agents clients temps réel (`Budget Insight`, `Conseil offres`, `Action`) connectés à l'application mobile.

---

## 2. Architecture globale des données (de `RAW` aux agents à l'échelle)

```mermaid
flowchart BT
    subgraph SILOS["Couche 0 — Silos sources existants (hétérogènes & bruités)"]
        S_MF["Mainframe core banking (fichiers batch CFONB / .cpy)"]
        S_AWS["SaaS CRM & call center sur AWS (S3 Iceberg + Glue)"]
        S_FIN["DB Finance SAP / PCEC & drops trésorerie ALM (Postgres / CSV)"]
        S_PAY["SI paiements temps réel (flux Kafka / PubSub ISO 20022)"]
        S_PDF["Contrats & offres promos agences (250 PDF sur GCS)"]
    end

    subgraph RAW_SILVER["Demos #1 & #2 — Socle BigLake, Iceberg & pipelines dbt (RAW -> SILVER)"]
        RAW["Couche RAW : tables Iceberg managées, Object Tables PDF & Borderless AWS (BigQuery Omni)"]
        DBT["Pipelines industriels dbt + scans Data Quality automatisés"]
        DP["Couche SILVER : 5 data products élémentaires documentés dans Knowledge Catalog"]
    end

    subgraph GOLD_KC["Demo #3 — Connaissance d'entreprise, KC & agents CFO"]
        LEG["Catalogues legacy + vidéos d'interviews métier (.mp4)"]
        KC["Knowledge Catalog : auto-enrichissement, 3 glossaires métier, graphe & MCP"]
        BQA["BQ Agents + Gemini Enterprise (questions finance, PDF & fonctions AI)"]
    end

    subgraph SCALE_APP["Demo #4 — Passage à l'échelle digital & mobile"]
        BQML["BigQuery AI / BQML (calcul Budget Insight & propension offres)"]
        ALLOY["AlloyDB (alloydb_sync : insights + état temps réel comptes & transactions)"]
        ADK["Agent Runtime (ADK) + App mobile Android : 3 agents (Budget Insight, Conseil offres, Action)"]
    end

    S_MF --> RAW
    S_AWS --> RAW
    S_FIN --> RAW
    S_PAY --> RAW
    S_PDF --> RAW
    RAW --> DBT --> DP
    LEG --> KC
    DP --> KC
    KC --> BQA
    DP --> BQML
    KC --> BQML
    S_PAY --> ALLOY
    BQML --> ALLOY
    ALLOY --> ADK
```

---

## 3. Découpage détaillé des 4 démos live

### Démo #1 — Agrégation de la couche `RAW` sans copie (Clément + Matt)
* **Persona :** Data Engineer qui découvre la vitesse d'`Antigravity (AGY)` + `Data Agent Kit (DAK)` face à un SI bancaire éclaté.
* **État initial :**
  * Fichiers batch Mainframe au format fixe illisible (`CFONB 120` / Copybook `.cpy`, encodage legacy).
  * Données CRM & interactions call center hébergées dans un SaaS sur **AWS** (`S3` + `Glue`).
  * Données Finance / comptabilité dans une base type **SAP / Postgres** (+ exports ALM).
  * Flux d'événements de paiements temps réel (`Kafka` / `Pub/Sub` en `ISO 20022 pacs.008` & JSON).
  * Contrats et avenants promotionnels en **PDF** non structurés sur GCS.
* **Actions réalisées dans `AGY` :**
  1. Exploration de l'architecture existante et création par agent du lien **Borderless Lakehouse** vers AWS (`BigQuery Omni` / `BigLake` sur S3, zéro copie).
  2. Ingestion des fichiers bruts Mainframe et flux en tables **Iceberg hébergées** + exposition des PDF via **Object Tables**.
  3. Initialisation de la structure industrielle **`dbt`** (couche `staging/raw`), regroupement logique des tables et génération de la **documentation technique initiale** dans `Knowledge Catalog`, qui met immédiatement en évidence les premières incohérences de qualité.
* **Briques Google Cloud démontrées :** `Antigravity` + `DAK`, `Borderless Lakehouse`, `BigLake Iceberg hosting`, accès non structuré (`Object Tables`), `Knowledge Catalog` (documentation technique des assets).
* **Transition vers Démo #2 :** *Jojo (Data Steward) intervient : « Vous avez branché les tuyaux, mais regardez l'état de la qualité en RAW — si on expose ça, tout va planter ! »*

---

### Démo #2 — Industrialisation `SILVER` & Data Quality dans `dbt` (L'équipe Data)
* **Persona :** L'équipe Data qui industrialise la passage de `RAW` à `SILVER` avec des garanties de qualité.
* **État initial :** Données `RAW` accessibles mais truffées d'anomalies réelles (doublons de retry sur le flux paiements, dates mainframe `00000000`, codes agences `NULL`, statuts techniques `RJCT`/`PDNG` mélangés aux virements exécutés `ACSC`).
* **Actions réalisées dans `AGY` :**
  1. Exécution d'un **agent Data Quality Scan** qui profile les tables `RAW` et remonte les anomalies concrètes.
  2. Itération assistée dans `AGY` pour générer les modèles **`dbt` (`SILVER`)** intégrant nativement les tests `dbt` et les règles de **Data Quality** BigQuery/KC.
  3. Publication des **5 data products élémentaires** propres dans `Knowledge Catalog` :
     * `dp_accounts_balances` *(Comptes & soldes valorisés J+1)*
     * `dp_payment_flows` *(Flux paiements SEPA Instant, cartes & ajouts d'IBAN dédoublonnés)*
     * `dp_customers_interactions` *(Clients, RDV agences & verbatims call center via Borderless AWS)*
     * `dp_finance_gl_alm` *(Écritures comptables, budget & refinancement trésorerie)*
     * `dp_contracts_promos` *(Contrats & offres promotionnelles PDF)*
* **Briques Google Cloud démontrées :** `Knowledge Catalog Data Products`, `Auto Data Quality`, intégration `dbt` + `DAK`.
* **Transition vers Démo #3 :** *« Jojo Fiero » : fier de ses Data Products 100 % propres au scan DQ, Jojo crée un premier `BQ Agent` et file répondre aux questions du CFO...*

---

### Démo #3 — Connaissance métier dans `Knowledge Catalog` & pilotage CFO (Jojo)
* **Persona :** Data Steward qui capture toute la finesse métier de l'entreprise pour ancrer les agents dans le réel et diviser la consommation de tokens.
* **État initial :** La Data Quality technique est désormais au vert (`SILVER`), **mais le contexte métier de la banque est absent des schémas**. Résultat : sur des KPI financiers composites, les agents hallucinent des formules fausses avec aplomb.
* **Actions réalisées en 2 temps :**
  1. **Le crash sémantique (« Fake résultat ») :**
     * Création d'un **`BQ Agent`** dans BigQuery Studio branché sur les tables `SILVER`, interrogé depuis **`Gemini Enterprise`** sur 4–5 questions Finance du CFO.
     * La requête SQL s'exécute sans erreur technique, mais renvoie un **résultat métier aberrant (`+42,8 M€` de hausse de marge au lieu de `-38,42 M€`)** car l'agent ignore les règles de signe comptable (`SENS_DC` / `SHKZG`), compte les virements internes compte-à-livret et oublie de déduire le refinancement ALM ainsi que les remises commerciales stockées dans les PDF.
  2. **Capture de la connaissance & ancrage `Knowledge Catalog` dans `AGY` :**
     * Import et réconciliation des **catalogues legacy** de la banque (exports CSV/JSON historiques incomplets ou contradictoires entre Réseau Commercial et Finance).
     * Ingestion multimodale des **vidéos d'interviews métier pré-enregistrées (`.mp4`)** où les sachants (responsable ALM, contrôle de gestion, réseau) expliquent à l'oral les vraies règles de calcul du PNB net et le rôle des avenants PDF.
     * Construction du **graphe de connaissance** et auto-enrichissement de `Knowledge Catalog` (**3 glossaires métier** : *Finance & ALM*, *Paiements & Comptes*, *Client & Commercial* + définitions certifiées des KPI).
  3. **Le replay gagnant dans `Gemini Enterprise` :**
     * On ré-utilise **le même `BQ Agent`** désormais ancré sur `Knowledge Catalog` : les réponses tombent **justes au centime près (`-38,42 M€`)**, exploitent les **PDF** et les **fonctions AI** (`AI.FORECAST` / `AI.GENERATE`), avec une **réduction massive du nombre de tokens** consommés.
* **Briques Google Cloud démontrées :** `BQ Agents`, `Knowledge Catalog` (agrégation, `Self-Enrichment`, graphe & glossaires), `Gemini Enterprise`, fonctions AI & multimodal PDF.

---

### Démo #4 — Passage à l'échelle côté Digital : `BQML`, `AlloyDB` & 3 agents `ADK` (Matt + Clément)
* **Persona :** Équipe Digital / Produit + Data qui transforme ce socle gouverné en expérience mobile agentique à grande échelle.
* **État initial :** Application mobile bancaire classique et statique (simple affichage des soldes passés).
* **Objectif produit :** Intégrer **3 agents spécialisés** dans l'expérience mobile :
  1. **`Agent Budget Insight`** : analyse des mouvements récents (*« Depuis votre dernière connexion »*, détection de hausse d'abonnement `+4 €`) et projection prédictive du reste à vivre de fin de mois (`+300 €`).
  2. **`Agent Conseil Offres`** : recommandation personnalisée et éligible (ex. placement de l'excédent sur un livret rémunéré maison boosté, évitant la fuite vers une néobanque).
  3. **`Agent Action`** : exécution transactionnelle sécurisée en 1-clic (virement interne d'épargne ou souscription d'offre).
* **Actions réalisées :**
  1. **Dans `Antigravity (AGY)` avec `DAK` :** génération accélérée des *User Journeys* et des features/modèles **`BQML`** (`TimesFM` / propension offres) — l'agent code juste du premier coup car il s'appuie directement sur les schémas `SILVER` et la sémantique de `Knowledge Catalog`.
  2. **Synchronisation opérationnelle (`alloydb_sync`) :** exposition haute performance vers **`AlloyDB`** des insights calculés dans BigQuery, combinés aux soldes valorisés `J-1` et au flux temps réel des paiements du jour `J` (`< 15 ms` de latence).
  3. **Dans `Android Studio` :** intégration dans l'application mobile des fonctions intelligentes et orchestration des **3 agents développés avec `ADK`** déployés sur **`Agent Runtime`**.
* **Briques Google Cloud démontrées :** `BQML` / `BigQuery AI`, `AlloyDB` (`alloydb_sync`), `ADK` & `Agent Runtime`.

---

## 4. Spécifications & invariants du jeu de données à simuler (`seed=2026`)

Pour que les 4 démos racontent une seule et même histoire cohérente sans jamais tricher avec des mocks codés en dur, le générateur de données doit garantir les invariants suivants :

### A. Volumétrie cible (optimisée pour `< 2 s` de requête en live)
* **Clients (`CRM AWS S3`) :** `80 000` clients particuliers répartis sur `8 régions` et `450 agences`, `0` clôture de compte sur le trimestre, `+15 000` ouvertures récentes, `320 000` notes de RDV agence & verbatims d'appels call center.
* **Comptes & opérations (`Core banking` + `SI paiements`) :** `95 000` comptes courants/livrets, `~5,5 M` d'écritures valorisées batch et `~6,2 M` d'événements dans le flux paiements sur 18 mois.
* **Finance & PDF :** `1,2 M` de lignes comptables agrégées, `250` vrais fichiers PDF d'offres promotionnelles sur GCS, et un référentiel d'`offres_epargne` pour la Démo #4.

### B. Anomalies `RAW` obligatoires (pour le tacle de Jojo & la Démo #2)
1. **Doublons techniques de flux (`SI paiements`) :** ~`3,4 %` d'événements en doublon sur `end_to_end_id` (retries réseau) + présence de statuts rejetés/en attente (`RJCT`, `PDNG` = `8,1 %` des messages).
2. **Corruptions de format Mainframe (`Core banking`) :** dates de valeur non renseignées encodées en `00000000` ou `99999999` (~`1,2 %` des lignes) et codes agences non normalisés (`'0042'` vs `'42  '`).
3. **Clés orphelines inter-silos :** ~`650` comptes récents créés en agence sur AWS S3 pas encore réconciliés dans le référentiel client Mainframe du soir.

### C. Invariants métier & financiers (pour la Démo #3 — `Fake` vs `Certifié`)
* **Fuite réelle des dépôts à vue (90 jours) :** exactement **`2 420 000 000 €`** de virements sortants compensés (`ACSC`) vers des BIC de néobanques/courtiers (`REVOLT21`, `TRBKDEBB`, etc.), dont **`68,0 %`** chez les **18–32 ans** concentrés entre le **1er et le 5 du mois**.
* **Résultat « FAKE » du `BQ Agent` avant `Knowledge Catalog` :** **`+42,80 M€`** (obtenu systématiquement lorsqu'un SQL naïf somme les montants comptables bruts non signés sans appliquer le sens Débit/Crédit, inclut les virements internes compte-à-livret `58*` et ignore le coût ALM ainsi que les PDF).
* **Résultat « CERTIFIÉ » après `Knowledge Catalog` :** **`-38,42 M€`** d'écart net de PNB par rapport au budget, décomposé exactement en :
  * **`-24,12 M€`** de coût de refinancement trésorerie ALM (`2,42 Md€` remplacés sur 90 jours au taux €STR ~`398 bps`),
  * **`-14,30 M€`** de primes de bienvenue, gratuités et taux boostés engagés dans les **250 avenants PDF** d'agence.

### D. Assets « Connaissance Legacy » & Personas Digital (pour les Démos #3 et #4)
* **Kit legacy pour Démo #3 :**
  * `legacy_catalogs/collibra_export_2021.csv` (obsolète, 30 % de colonnes couvertes, définitions Commerciales contredisant la Finance).
  * `legacy_catalogs/kpi_finance_excel_glossary.json` (incomplet).
  * `interviews_metier/` : transcriptions/vidéos courtes de 2 experts (Directeur ALM Trésorerie & Responsable Pilotage Réseau) énonçant les vraies règles de gestion.
* **Client témoin pour l'app mobile Android en Démo #4 :**
  * Historique de virements sortants vers néobanque les mois `M-2` et `M-1`, salaire reçu le 1er du mois `M` (`+1 850 €`), hausse détectée de `+4 €` sur un abonnement streaming (`15,99 € -> 19,99 €`), remboursement santé (`+42 €`), et **excédent prévisionnel fin de mois = `+300 €`** déclenchant la recommandation `Agent Conseil Offres` (*Livret Boost Maison 4 %*) exécutable en 1-clic par l'`Agent Action` dans `AlloyDB`.

---

## 5. Arborescence cible du repository & conventions pour Antigravity (`AGY`)

```yaml
agentic-data-cloud-day-paris-2026/
├── README.md                          # Vue d'ensemble & quickstart du repo
├── DESIGN_AND_CONTEXT.md              # Ce document (contexte de référence AGY)
├── AGENTS.md                          # Instructions directes pour les agents Antigravity
├── docs/
│   └── assets/
│       └── architecture_cible_data_cloud.png
├── 00_data_generator/                 # Générateur déterministe (seed=2026) des silos Couche 0
│   ├── generate_mainframe_cfonb.py
│   ├── generate_aws_crm_s3.py
│   ├── generate_finance_sap_alm.py
│   ├── generate_payments_stream.py
│   └── generate_promo_pdfs.py
├── 01_demo1_raw_aggregation/          # Connexions BigLake AWS, Iceberg RAW & init dbt
├── 02_demo2_silver_dbt_dq/            # Projet dbt (RAW -> SILVER), scans DQ & Data Products KC
├── 03_demo3_kc_semantics_cfo/         # Exports legacy, vidéos interviews, enrichissement KC & BQ Agents
├── 04_demo4_scale_mobile_adk/         # Modèles BQML, alloydb_sync, agents ADK & app mobile Android
└── scripts/
    └── reset_demo_state.sh            # Remise à zéro instantanée entre deux répétitions
```

### Règles de génération de code pour les agents `Antigravity`
1. **Zéro copie inutile :** Privilégier systématiquement `BigLake` (`Iceberg` sur GCS, `BigQuery Omni` sur AWS S3 et `Object Tables` pour les PDF) plutôt que des copies physiques de fichiers.
2. **Industrialisation `dbt` :** Toutes les transformations `RAW -> SILVER` doivent être écrites sous forme de modèles `dbt` versionnés accompagnés de leur fichier `schema.yml` (descriptions + tests de qualité).
3. **Sémantique centralisée dans `Knowledge Catalog` :** Ne jamais coder en dur de formules métier complexes (comme le calcul de la marge nette PNB CFO) dans le prompt d'un agent ; toujours passer par les glossaires et vues gouvernées de `Knowledge Catalog`.
4. **Séparation Analytique / Opérationnel :** Les calculs prédictifs (`Budget Insight`, propension offres) tournent dans `BigQuery` (`BQML` / `AI SQL`), tandis que la lecture faible latence (`< 15 ms`) et les écritures transactionnelles des agents `ADK` mobiles passent par `AlloyDB` (`alloydb_sync`).
