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

## 4. Spécificités du `Flow 1` (`Démo #1`) & Posture Interactive `AGY` + `DAK`
Le script conversationnel complet et les skills `Data Agent Kit (DAK)` associés à chaque étape sont consignés dans `docs/DEMO_QUESTIONS_AND_FLOW.md`. Tout agent (`AGY`) intervenant sur ce repo doit mémoriser et appliquer ce déroulé :

1. **Enchaînement mémorisé du `Flow 1` (`Démo #1`) en 3 tours interactifs :**
   * **Tour 1 — *"Transfère les données sur GCP depuis le serveur de fichiers local"* :**
     * **Outils & Skills `DAK` à mobiliser :** MCP `data-agent-kit/get_active_gcp_connection` (résolution auto projet/région IDE), `discover-assets`, `gcp-data-pipelines`, `accidental-data-loss-prevention` et `enforcing-resource-attribution` (`CLOUDSDK_METRICS_ENVIRONMENT="... datacloud.antigravity"`).
     * **Diagnostic & 3 questions obligatoires avant transfert :** inspecter `00_data_generator/output/corebanking/` (`MANIFEST_Z_OS_DROP.ctl`), expliquer pourquoi un import direct `bq load` / `BigQuery DTS` est impossible (maîtres `.ebcdic` en binaire `RECFM=FB` `CP500 + COMP-3` sans `\n`), signaler le fichier `202610_RUN01.cfonb` en `ABEND_S0C7` (`RC=0012`) à côté de `RUN02_RERUN`, et faire confirmer : **(1)** le bucket/chemin cible GCS Landing (et autorisation de création si absent), **(2)** le transfert intégral fidèle au CFT (incluant `.cpy`, `.ctl` et `RUN01` pour l'auditabilité, filtré ensuite par Spark), **(3)** la copie binaire stricte parallélisée sans transcodage ni décompression.
   * **Tour 2 — *Parsing Core Banking vers BigLake Managed Iceberg (`raw_bank`)* :**
     * **Outils & Skills `DAK` à mobiliser :** `gcp-spark` (`biglake_iceberg.md`, `ManagedSparkSession` / Spark Connect), MCP `bigquery`, `enforcing-resource-attribution`.
     * **3 questions obligatoires après lecture des `.cpy` :** **(1)** rejet automatique des fichiers où `99CFT_TRL` a `RC != 0000` + contrôle `CHECKSUM_MVTS_04`, **(2)** rattachement par fenêtre d'ordre physique des lignes `05` (`BIC` + `EndToEndId`) sur leur `04` parent et création des 4 tables **BigLake Managed Iceberg** (`cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_balances`, `cbk_cfonb_movements`), **(3)** préservation stricte en `RAW` des anomalies de valeurs métier (`00000000`, codes agences `'42  '`, `650` orphelins) pour `dbt` en `Démo #2` + choix du profil d'exécution Spark.
   * **Tour 3 — *Fédération AWS S3 (`federate-lakehouse-catalog`), PDF (`Object Tables`) & Init `dbt` (`dbt-bigquery` + `curate-context`)* :** exposition zéro-copie des autres silos et génération de `sources.yml`.
2. **Règle d'or sur scène (ne jamais décider en silence) :**
   * Face à un piège physique, un fichier `ABEND`, une création de ressource ou un conflit sémantique, `AGY` résume toujours ses constats et pose ses **2 à 3 questions d'arbitrage ciblées** avant d'exécuter.


