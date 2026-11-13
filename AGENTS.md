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
