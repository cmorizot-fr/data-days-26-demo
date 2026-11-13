# Fil conducteur des échanges live & Skills Data Agent Kit (`DAK`) — Paris Data Summit 2026

> [!IMPORTANT]
> Ce document constitue le **script conversationnel de référence** mémorisé pour `Antigravity (AGY)` (lié depuis [`AGENTS.md`](../AGENTS.md)) et l'aide-mémoire de scène des intervenants.
> À chaque étape, les données et l'environnement déclenchent les **skills officiels du Data Agent Kit (`DAK`)** et provoquent un **dialogue d'arbitrage court et concret (2 à 3 questions)** entre le LLM et le présentateur avant exécution.

---

## Cartographie globale des Skills & MCP `Data Agent Kit` mobilisés

| Démo & Phase | MCP Servers sollicités | Skills `DAK` activés | Rôle clé dans la démo |
| :--- | :--- | :--- | :--- |
| **Démo #1 — Tour 1**<br>*Transfert Serveur Local -> GCS* | `data-agent-kit` (`get_active_gcp_connection`) | `gcp-data-pipelines`<br>`discover-assets`<br>`accidental-data-loss-prevention`<br>`enforcing-resource-attribution` | Détecte le projet/région IDE, inspecte le binaire z/OS local, écarte `BQ DTS` direct, valide le bucket/immuabilité CFT et transfère avec labels `datacloud.antigravity`. |
| **Démo #1 — Tour 2**<br>*Parsing Spark -> BigLake Iceberg* | `bigquery` (`get_dataset_info`, `list_table_ids`)<br>`notebooks` *(si `.ipynb`)* | `gcp-spark` *(+ `biglake_iceberg.md`)*<br>`discover-assets`<br>`enforcing-resource-attribution` | Lit les Copybooks `.cpy`, filtre le `RUN01` en `ABEND_S0C7`, décode `EBCDIC CP500 + COMP-3`, recolle `CFONB 04+05` et écrit en **BigLake Managed Iceberg** (`raw_bank`). |
| **Démo #1 — Tour 3**<br>*AWS Borderless, PDF & init `dbt`* | `bigquery` (`execute_sql`) | `federate-lakehouse-catalog`<br>`dbt-bigquery`<br>`curate-context` | Fédère `AWS Glue / S3` sans copie, crée l'**Object Table** sur les 250 PDF et initialise les `sources.yml` `dbt` + doc technique `Knowledge Catalog`. |
| **Démo #2**<br>*Industrialisation `SILVER` & DQ* | `bigquery` (`execute_sql`, `get_table_info`) | `data-autocleaning`<br>`dbt-bigquery`<br>`discover-assets` | Profile les anomalies `RAW`, fait arbitrer les règles de nettoyage/réconciliation et génère les 5 Data Products `dbt` testés. |
| **Démo #3**<br>*Sémantique `KC` & Pilotage CFO* | `bigquery`<br>`data-agent-kit` (`render_chart`) | `curate-context` (`kcmd` / OKF)<br>`discover-assets`<br>`bigquery-ai-ml` | Réconcilie les catalogues legacy + interviews `.mp4`, publie le contexte certifié dans `KC` et corrige l'écart PNB de `+42,80 M€` à `-38,42 M€`. |
| **Démo #4**<br>*Scale Digital : `BQML` & `AlloyDB`* | `bigquery`<br>`data-agent-kit` | `bigquery-ai-ml`<br>`ml-best-practices`<br>`cloud-databases-onboarding` | Génère les prévisions `AI.FORECAST` / propension dans BigQuery et expose les insights en `< 15 ms` via `alloydb_sync` aux 3 agents `ADK`. |

---

## Démo #1 — Script complet mémorisé du `Flow 1` (Clément & Matt)

### Tour 1 — Transfert des données vers GCP depuis le serveur de fichiers local

#### 1. Actions internes d'`AGY` + `DAK` dès réception du prompt
* **Prompt intervenant sur scène :**
  > *« Transfère les données Core Banking sur GCP depuis le serveur de fichiers local. »*
* **Skills & Outils déclenchés automatiquement par `AGY` avant de répondre :**
  1. **MCP `data-agent-kit` -> `get_active_gcp_connection`** : récupère automatiquement le `project_id`, la `region` (`europe-west1`) et la `bigquery_location` configurés dans l'IDE.
  2. **Inspection du serveur de fichiers local** (`00_data_generator/output/corebanking/`) : lit `MANIFEST_Z_OS_DROP.ctl`, repère les Copybooks `.cpy`, les binaires `.ebcdic` (`RECFM=FB`, `CP500 + COMP-3`), le mix `.cfonb.gz` (2025) / `.cfonb` (2026) et l'anomalie de double fichier sur octobre (`RUN01` en `ABEND_S0C7` vs `RUN02_RERUN`).
  3. **Skill `discover-assets` & vérification GCS** : vérifie si un bucket de Landing Zone existe déjà sur le projet actif.
  4. **Skill `gcp-data-pipelines` + `accidental-data-loss-prevention`** : agit en *GCP Data Solutions Architect* — explique pourquoi un chargement direct BigQuery (`bq load` / `BigQuery DTS`) casserait sur du binaire `EBCDIC + COMP-3`, recommande un atterrissage brut sur **Cloud Storage (Landing Zone)** et **s'arrête pour faire valider 3 points avant transfert**.

#### 2. Réponse & Questions exactes posées par `AGY` sur scène (Tour 1)
> *« J'ai inspecté le répertoire local du serveur de fichiers (`00_data_generator/output/corebanking/`, 22 fichiers, ~980 Mo) ainsi que la connexion GCP active (`<PROJECT_ID>`, région `europe-west1`).*
>
> *Diagnostic rapide avant transfert :*
> * *Les maîtres (`.ebcdic`) sont en **binaire continu z/OS (`RECFM=FB`, `EBCDIC CP500` + `COMP-3` Packed Decimal)** : un import direct via `bq load` ou `BigQuery DTS` est impossible. Il faut d'abord les déposer en **Landing Zone GCS** avant décodage par **Managed Spark**.*
> * *Le lot contient un mix d'archives `.cfonb.gz` (2025) et `.cfonb` (2026), ainsi qu'**un fichier interrompu en crash Mainframe** (`CFONB120_MVTS_202610_RUN01.cfonb`, `STATUS=ABEND_S0C7 RC=0012`) à côté de sa reprise `RUN02_RERUN.cfonb` (`RC=0000`).*
>
> *Avant de lancer le transfert, peux-tu me confirmer ces 3 choix :*
> 1. **Bucket & arborescence cible GCS** : Je dépose le lot sous `gs://<GCS_BUCKET_LANDING>/corebanking/drop_date=2026-11-12/` *(et si le bucket n'existe pas encore, confirmes-tu sa création en `europe-west1`)* ?
> 2. **Fidélité de la Landing Zone (gestion du fichier `ABEND` & des `.cpy`)** : On transfère **100 % du lot tel quel** (incluant les Copybooks `.cpy`, le manifeste `.ctl` et le fichier `202610_RUN01` en `ABEND` pour garder une trace d'audit exacte de la sortie CFT et filtrer dans Spark), ou j'exclus `RUN01` dès le transfert ?
> 3. **Intégrité binaire du transfert** : Je lance un `gcloud storage cp --recursive` parallélisé en **copie binaire stricte sans décompression ni transcodage texte** (indispensable pour ne pas corrompre les octets `COMP-3` des `.ebcdic` et conserver les `.cfonb.gz`) ? »

#### 3. Réponse de l'intervenant sur scène (Tour 1)
> *« 1) Oui, utilise ce bucket en `europe-west1` (crée-le s'il n'existe pas). 2) Transfère **tout tel quel**, y compris les `.cpy`, le `.ctl` et le `RUN01` en ABEND : la Landing Zone doit rester le miroir exact du Mainframe pour l'auditabilité, c'est Spark qui filtrera. 3) Oui, copie binaire stricte parallélisée ! »*

#### 4. Exécution par `AGY` (Tour 1)
* Activation du **Skill `enforcing-resource-attribution`** : exécution de `CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity" gcloud storage cp --recursive ...` puis vérification post-transfert (`gcloud storage ls -lh`).

---

### Tour 2 — Découverte des Copybooks sur GCS & Parsing Spark vers BigLake Iceberg (`raw_bank`)

#### 1. Prompt intervenant sur scène (Tour 2)
> *« Parfait, maintenant explore les Copybooks déposés sur GCS, parse ces fichiers Core Banking et crée nos tables Iceberg dans le dataset BigQuery `raw_bank`. »*

#### 2. Skills `DAK` activés & Questions posées par `AGY` (Tour 2)
* **Skills activés** : `gcp-data-pipelines` -> **`gcp-spark`** (`references/biglake_iceberg.md` + `references/gcloud_dataproc.md`) + `discover-assets` + MCP `bigquery` (`get_dataset_info`).
* **Questions posées par `AGY` après lecture des 3 fichiers `.cpy` :**
  > *« D'après l'analyse des 3 Copybooks COBOL (`CBK_CUSTOMERS_REF.cpy`, `CBK_ACCOUNTS_MSTR.cpy`, `CFONB120_BAL_OPS.cpy`), voici les 3 arbitrages à confirmer avant de générer et lancer le pipeline **Managed Spark -> BigLake Iceberg** :*
  > 1. **Contrôle d'intégrité CFT (`ABEND` Octobre)** : Spark vérifie l'enveloppe `00CFT_HDR` / `99CFT_TRL` de chaque fichier, **rejette automatiquement tout fichier dont `RC != 0000`** (ce qui écarte `202610_RUN01.cfonb` en `ABEND_S0C7`) et valide le compteur `CHECKSUM_MVTS_04` ?
  > 2. **Reconstruction multi-lignes `CFONB 04 + 05` & tables cibles** : Dans `CFONB120_BAL_OPS.cpy`, le `BIC` contrepartie et l'`EndToEndId` SEPA sont sur la ligne `05` placée physiquement sous la ligne `04` sans numéro d'écriture commun. Je rattache chaque `05` à son `04` parent par fenêtre d'offset physique et je matérialise **4 tables BigLake Managed Iceberg** dans `raw_bank` (`cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances`, `cbk_cfonb_movements`) ?
  > 3. **Frontière `RAW` vs Qualité métier & Runtime Spark** : J'ai vu dans les données des dates de valeur `00000000` / `99999999` et des codes agences décalés (`'42  '`). Confirme-moi qu'on **conserve ces valeurs métier brutes telles quelles en `RAW`** (avec ajout de `_source_file` et `_ingest_ts`), et indique-moi quel **Runtime Profile Spark Connect** (ou soumission batch Serverless) utiliser sur `<PROJECT_ID>` ? »

#### 3. Réponse de l'intervenant sur scène (Tour 2)
> *« 1) Oui, contrôle strict `RC=0000` + checksum. 2) Oui pour les 4 tables BigLake Managed Iceberg avec fusion physique `04+05`. 3) Surtout **ne touche à aucune valeur métier en `RAW`** : Spark gère uniquement le décodage physique Mainframe, on traitera la Data Quality dans `dbt` juste après. Lance-le sur notre session Spark Connect `<RUNTIME_PROFILE>` ! »*

---

### Tour 3 — Fédération AWS S3 (`Borderless Lakehouse`), Contrats PDF (`Object Tables`) & Init `dbt`

* **Prompt intervenant :**
  > *« Connecte maintenant sans copie les tables CRM & Call Center qui sont sur AWS S3/Glue, expose les 250 contrats promotionnels PDF sur GCS dans `raw_bank`, et initialise la couche `sources` de notre projet `dbt`. »*
* **Skills `DAK` activés :**
  * **`federate-lakehouse-catalog`** (fédération du catalogue `AWS Glue` / `S3` vers BigQuery sans copie de fichiers),
  * MCP `bigquery` + `enforcing-resource-attribution` (`--label datacloud:antigravity` pour l'**Object Table** `raw_bank.obj_promo_contracts_pdf`),
  * **`dbt-bigquery`** + **`curate-context`** (génération de `sources.yml` et documentation technique initiale dans `Knowledge Catalog`).
* **Questions rapides d'`AGY` :**
  1. Confirmation de l'ID de connexion AWS / ARN Glue (`federate-lakehouse-catalog`) en mode lecture directe zéro-copie.
  2. Exposition des 250 PDF en **Object Table BigLake** dans `raw_bank` et génération immédiate des `sources.yml` `dbt` pointant sur l'ensemble des tables `RAW` (Iceberg Mainframe + fédération AWS + Object Table PDF).

*(Transition idéale vers la **Démo #2** : Jojo ouvre la doc fraîchement générée et lance l'audit Data Quality !)*

---

## Démo #2 — Industrialisation `SILVER` & Data Quality dans `dbt` (Jojo & l'équipe Data)

* **Skills `DAK` activés :** **`data-autocleaning`**, **`dbt-bigquery`**, **`discover-assets`**, MCP `bigquery`.
* **Prompt intervenant :**
  > *« Lance un diagnostic Data Quality complet sur toutes nos sources `raw_bank` et propose le plan des modèles `dbt` `SILVER` pour nos 5 Data Products. »*
* **Questions d'arbitrage posées par `AGY` suite au scan :**
  1. **Flux Paiements (`3,4 %` doublons retries + `8,1 %` `RJCT`/`PDNG`)** : dédoublonnage par dernier statut sur `(end_to_end_id, event_ts)` + conservation du flag `is_settled = (status = 'ACSC')` ?
  2. **Anomalies Mainframe (`1,2 %` dates `00000000`/`99999999` & `12,1 %` agences `'42  '` / blancs)** : normalisation `LPAD` sur 4 chiffres via rattachement au compte maître + fallback documenté sur `date_compta` (`is_value_date_imputed`) ?
  3. **Clés orphelines inter-silos (`650` comptes récents AWS absents du Mainframe J-1)** : réconciliation gouvernée avec statut `PENDING_MAINFRAME_BATCH` (plutôt que suppression) pour préserver les `+15 000` ouvertures du trimestre ?

---

## Démo #3 — Sémantique métier dans `Knowledge Catalog` & Pilotage CFO (Jojo)

* **Skills `DAK` activés :** **`curate-context`** (`kcmd` / bundle OKF v0.2), **`discover-assets`**, **`bigquery-ai-ml`**.
* **Déroulé :**
  1. **Crash sémantique avant `KC`** : `BQ Agent` sur `SILVER` nu renvoie **`+42,80 M€`** (ignore `SHKZG`, inclut les virements internes `58*`, oublie le refinancement ALM €STR `-24,12 M€` et les primes des 250 PDF `-14,30 M€`).
  2. **Enrichissement dans `AGY`** (catalogues legacy + interviews `.mp4`) -> **`AGY` demande validation aux 2 portes obligatoires du skill `curate-context`** :
     * Séparation officielle entre *Attrition Juridique (Clôture = `0 %`)* et *Churn Silencieux de Liquidité (`2,42 Md€`, `68 %` chez les `18–32 ans` du 1er au 5 du mois)* ;
     * Validation et publication du Context Set certifiant la formule complète de l'**Écart Net de PNB CFO (`-38,42 M€`)**.

---

## Démo #4 — Passage à l'échelle Digital : `BQML`, `AlloyDB` & 3 Agents `ADK` (Matt & Clément)

* **Skills `DAK` activés :** **`bigquery-ai-ml`**, **`ml-best-practices`**, **`cloud-databases-onboarding`**.
* **Questions d'architecture posées par `AGY` :**
  1. Calcul analytique massif dans BigQuery (`AI.FORECAST` reste à vivre + détection hausse d'abonnement `+4 €` + propension offres) synchronisé vers **`AlloyDB` (`alloydb_sync`)** pour servir l'app mobile en `< 15 ms` avec fusion temps réel des paiements du jour `J` ?
  2. Garde-fou d'éligibilité sur l'`Agent Conseil Offres` (recommander *Livret Boost Maison 4 %* uniquement si excédent fin de mois prévu `> 0`, ex. `+300 €` pour Lucas Martin `CUST00002026`) et validation 1-clic transactionnelle dans `AlloyDB` pour l'`Agent Action` ?
