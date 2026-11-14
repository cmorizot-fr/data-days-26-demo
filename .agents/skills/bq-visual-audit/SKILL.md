---
name: bq-visual-audit
description: >-
  Exécute systématiquement un contrôle visuel post-création (graphiques ECharts via
  data-agent-kit/render_chart, jauges d'anomalies, ponts de réconciliation financière et
  aperçus documentaires ObjectRef) après toute création, alimentation ou exposition de table,
  table BigLake Managed Iceberg, Object Table, modèle dbt SILVER ou vue gouvernée GOLD dans BigQuery.
---

# Contrôle Visuel Systématique Post-Création BigQuery (`bq-visual-audit`)

Ce skill impose une règle d'ingénierie stricte pour tous les workflows **Banque Hexagone** :
**aucune création ou exposition de données dans BigQuery n'est considérée comme validée sur un simple `COUNT(*)` textuel.**

Dès qu'une étape crée, charge ou expose un actif dans BigQuery (`CREATE TABLE`, écriture Spark BigLake Iceberg, scan `Dataplex Cloud Storage Discovery`, `dbt build`, `CREATE VIEW` ou table `BQML` / `AI.FORECAST`), tu DOIS enchaîner un **contrôle visuel intégré au fil de discussion**.

## Protocole obligatoire en 3 étapes

### 1. Requête SQL consolidée de contrôle (`bigquery/execute_sql` ou `bq query`)
Exécute une requête unique (avec `--label datacloud:antigravity` en CLI) qui agrège simultanément :
- **Volumétrie & Complétude documentaire** : nombre de lignes par table/vue et couverture des descriptions dans `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`.
- **Distribution métier ou réconciliation financière** : répartition par catégorie métier, BIC contrepartie, segment d'âge, ou pont comptable (`Naïf` vs `Certifié Knowledge Catalog`).
- **Taux d'anomalies / Data Quality** :
  - En zone **`RAW`** : vérifier visuellement que les anomalies sources sont **préservées sans perte** pour l'audit aval (`1,20 %` dates `00000000`/`99999999`, `3,40 %` doublons SEPA, `8,10 %` `RJCT`/`PDNG`, `650` comptes J0 AWS).
  - En zones **`SILVER` / `GOLD`** : prouver visuellement le passage à **`100,0 %` DQ PASS** et la réconciliation au centime près.

### 2. Rendu graphique inline via `MCP data-agent-kit/render_chart`
Appelle systématiquement l'outil MCP `data-agent-kit/render_chart` avec une spécification **Apache ECharts V5** claire et lisible :
- **Couche `RAW` (BigLake Iceberg / Fédération / Streams)** : barres horizontales de distribution des volumes & répartition métier initiale (ex. fuite `-2,42 Md€` par BIC néobanque) + indicateurs d'anomalies brutes détectées.
- **Couche `RAW` Documentaire (`Object Tables` PDF)** : répartition par gabarit documentaire (`application/pdf`) **accompagnée d'un échantillon visuel de vignettes des documents découverts** via leurs `ObjectRef` (`uri`, `size_bytes`, `promo_contract_id` / `doc_code`).
- **Couche `SILVER` (`dbt` + `AI.GENERATE_TABLE`)** : scorecard visuelle `100 % PASS` avant/après purge des anomalies et synthèse des montants extraits des PDF (`-14,30 M€`).
- **Couche `GOLD` / Sémantique `Knowledge Catalog`** : pont de réconciliation (waterfall / comparaison directe) opposant le SQL naïf (`+42,80 M€`) à la vue certifiée (`-24,12 M€` ALM + `-14,30 M€` PDF = `-38,42 M€`) et mettant en évidence les seuils réglementaires franchis (`ILAAP > 2,00 Md€`, `Comité des Risques > 9,00 M€`).
- **Couche `AI / Opérationnelle` (`AI.FORECAST` & `alloydb_sync`)** : courbe/barres de trajectoire budgétaire client témoin (`CUST00002026`) et comparatif visuel de latence analytique vs opérationnelle (`p99 < 15 ms`).

### 3. Charte visuelle obligatoire (Zéro bordure colorée)
Conformément aux règles UX globales de l'utilisateur :
- **Interdiction absolue** des liserés, contours ou anneaux de couleur autour des cartes, tuiles KPI, barres ou vignettes.
- Utiliser exclusivement la **luminance de surface** (fonds doux contrastés) et la **typographie** pour hiérarchiser les statuts (`OK`, `WARN`, `ALERTE SEUIL`).
