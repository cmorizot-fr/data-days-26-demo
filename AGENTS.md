# AGENTS.md — Instructions pour Antigravity (`AGY`) & Data Agent Kit (`DAK`)

Ce fichier définit les règles strictes que tout agent travaillant sur ce repository doit respecter.
Le contexte complet du projet est décrit dans `DESIGN_AND_CONTEXT.md`.

## 1. Principes d'architecture non négociables
1. **Zéro copie inutile :** Utiliser systématiquement `BigLake` (`Iceberg` sur GCS, `BigQuery Omni` sur AWS S3 et `Object Tables` pour les PDF) plutôt que de dupliquer des fichiers.
2. **Industrialisation `dbt` :** Toutes les transformations `RAW -> SILVER` doivent être écrites sous forme de modèles `dbt` versionnés avec leur `schema.yml` (descriptions + tests de qualité).
3. **Sémantique centralisée dans `Knowledge Catalog` :** Ne jamais coder en dur des formules métier complexes (notamment le calcul de la marge nette PNB CFO) dans les prompts d'agents ; toujours s'appuyer sur les glossaires et vues gouvernées de `Knowledge Catalog`.
4. **Séparation Analytique / Opérationnel :**
   * Analytique & ML (`Budget Insight`, propension offres) -> `BigQuery` (`BQML` / `AI SQL`).
   * Temps réel faible latence (`< 15 ms`) & écritures transactionnelles mobile -> `AlloyDB` (`alloydb_sync`).

## 2. Invariants chiffrés à préserver (`seed=2026`)
Toute modification du générateur de données (`00_data_generator/`) doit préserver ces invariants vérifiables au centime près :
* **Périmètre clients :** `80 000` clients, `8` régions, `450` agences, `0` clôture sur le trimestre, `+15 000` ouvertures récentes, `95 000` comptes.
* **Anomalies `RAW` obligatoires :**
  * `~3,4 %` de doublons `end_to_end_id` + `8,1 %` de statuts `RJCT` / `PDNG` dans le flux paiements.
  * `~1,2 %` de dates `00000000` / `99999999` et codes agences non normalisés dans le Mainframe CFONB.
  * `~650` comptes orphelins entre AWS S3 et Mainframe.
* **Fuite dépôts à vue (90 j) :** exactement `2 420 000 000,00 €` de virements sortants `ACSC` vers des BIC néobanques/courtiers, dont `68,0 %` chez les `18-32 ans` entre le 1er et le 5 du mois.
* **Écart PNB CFO :**
  * Requête naïve (`SILVER` sans sémantique `KC`) : **`+42 800 000,00 €`**.
  * Requête certifiée (avec `KC`) : **`-38 420 000,00 €`** (`-24,12 M€` coût refinancement ALM + `-14,30 M€` primes/remises des 250 PDF).

## 3. Conventions de développement
* **Python :** Utiliser `uv` pour la gestion des dépendances (`pyproject.toml`). Privilégier `polars`, `pyarrow` et `duckdb` pour la génération et la validation locale rapide.
* **Scripts & Secrets :** Ne jamais committer de `.env` ni de clés GCP/AWS. Utiliser `.env.example` comme référence.
* **Orchestration de la génération & du nettoyage (`scripts/`) :** Tout nouveau générateur ajouté dans `00_data_generator/` doit obligatoirement être branché dans [`scripts/generate_all_data.sh`](./scripts/generate_all_data.sh) (qui lance toutes les générations et synchronise vers GCS) et pris en compte par [`scripts/clean_all_data.sh`](./scripts/clean_all_data.sh) (qui nettoie proprement toutes les données générées en local et/ou sur GCS).

## 4. Spécificités du `Flow 1` (`Démo #1`) & Posture Interactive `AGY` + `DAK`
Le script conversationnel complet et les skills `Data Agent Kit (DAK)` associés à chaque étape sont consignés dans `docs/DEMO_QUESTIONS_AND_FLOW.md`.
Organisation de l'interface (`stage_ui` & démo) : **1 Workspace par Démo** (`01_demo1_raw_aggregation` .. `04_demo4_scale_mobile_adk`), et à l'intérieur de chaque Workspace, **1 Conversation distincte par Étape de la démo**. Les buckets GCS existent déjà.

1. **Enchaînement mémorisé du `Flow 1` (`Démo #1`) par conversation d'étape :**
   * **Conversation Étape 1 — *"Transfere les données mainframe du serveur de fichier pour le mois passé, sur GCS dans la zone RAW."* :**
     * **Outils & Skills `DAK` à mobiliser :** MCP `data-agent-kit/get_active_gcp_connection` (résolution auto projet/région IDE), `discover-assets`, `gcp-data-pipelines`, `accidental-data-loss-prevention` et `enforcing-resource-attribution` (`CLOUDSDK_METRICS_ENVIRONMENT="... datacloud.antigravity"`).
     * **Diagnostic & 3 questions obligatoires avant transfert (le bucket existant déjà, ne jamais proposer de le créer) :** inspecter `00_data_generator/output/corebanking/` (`MANIFEST_Z_OS_DROP.ctl`), vérifier l'accès au bucket `RAW` existant, expliquer que les maîtres `.ebcdic` sont en binaire `RECFM=FB` `CP500 + COMP-3` sans `\n`, et faire confirmer : **(1)** la gestion du double fichier détecté sur le mois passé (`202610_RUN01.cfonb` en `ABEND_S0C7` `RC=0012` vs `RUN02_RERUN.cfonb` `RC=0000` — conserver les deux en zone `RAW` pour l'auditabilité CFT et filtrer dans Spark), **(2)** l'inclusion des référentiels maîtres `.ebcdic`, du `.ctl` et des Copybooks `copybooks/*.cpy`, **(3)** le chemin cible dans le bucket existant (`raw/corebanking/202610/`) en copie binaire stricte parallélisée sans transcodage.
   * **Conversation Étape 2 — *Parsing Spark → BigLake Iceberg (`raw_bank`)* :**
     * **Outils & Skills `DAK` à mobiliser :** `gcp-spark` (`biglake_iceberg.md`, `ManagedSparkSession` / Spark Connect), MCP `bigquery`, `enforcing-resource-attribution`.
     * **3 questions obligatoires après lecture des `.cpy` :** **(1)** rejet automatique des fichiers où `99CFT_TRL` a `RC != 0000` + contrôle `CHECKSUM_MVTS_04`, **(2)** rattachement par fenêtre d'ordre physique des lignes `05` (`BIC` + `EndToEndId`) sur leur `04` parent et création des 4 tables **BigLake Managed Iceberg** (`cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances`, `cbk_cfonb_movements`), **(3)** préservation stricte en `RAW` des anomalies de valeurs métier (`00000000`, codes agences `'42  '`, `650` orphelins) pour `dbt` en `Démo #2` + choix du profil Spark Connect.
   * **Conversation Étape 3 — *Fédération AWS S3 (`federate-lakehouse-catalog`) & Contrats PDF (`Object Tables`)* :** exposition zéro-copie des autres silos.
   * **Conversation Étape 4 — *Init `dbt` (`dbt-bigquery`) & Doc technique `Knowledge Catalog` (`curate-context`)* :** génération de `dbt_project.yml` et `_raw_sources.yml`.
2. **Règle d'or sur scène (ne jamais décider en silence) :**
   * Face à un piège physique, un fichier `ABEND` ou un conflit sémantique, `AGY` résume toujours ses constats et pose ses **2 à 3 questions d'arbitrage ciblées** avant d'exécuter.
3. **Configuration pré-scriptée de `stage_ui` (ne jamais coder les scénarios en dur en TypeScript) :**
   * Toute la partie pré-scriptée de l'interface web (`stage_ui` : paramètres globaux, Workspaces par démo, Conversations par étape, prompts pré-remplis, questions/réponses d'`AGY`, traces d'outils, diffs de fichiers, logs terminaux et artefacts) doit **toujours rester centralisée et éditable dans le fichier de configuration YAML [`stage_ui/public/demo_config.yaml`](./stage_ui/public/demo_config.yaml)** (chargé dynamiquement par `stage_ui/src/data/scenarios.ts`, modifiable à chaud sous `npm run dev` ou par simple `F5` sur `dist/demo_config.yaml`).



