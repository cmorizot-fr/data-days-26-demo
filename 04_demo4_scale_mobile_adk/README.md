# Couche GOLD Démo #4 — `dp_budget_insight` (`gold_bank`) & Scale Mobile

Ce dossier regroupe les artefacts analytiques (`BigQuery AI` / `AI.FORECAST` TimesFM 2.5), la synchronisation opérationnelle `AlloyDB` (`alloydb_sync`, `< 15 ms`) et les 3 agents mobiles `ADK` (*Budget Insight*, *Conseil Offres*, *Action*).

## Architecture GOLD (`gold_bank` · Data Product `dp_budget_insight`)

Les modèles de production sont industrialisés dans le projet `dbt` unique ([`02_demo2_silver_dbt_dq/models/gold/budget_insight/`](../02_demo2_silver_dbt_dq/models/gold/budget_insight/)) pour préserver le lineage complet `RAW → SILVER → GOLD`, la documentation `persist_docs` (`INFORMATION_SCHEMA` / Knowledge Catalog) et les tests de conformité `ACPR 2024-R-01`.

| Table `gold_bank` | Grain | Rôle dans la Démo #4 & l'agent conversationnel |
| :--- | :--- | :--- |
| `customer_transactions_enriched` | 1 ligne par mouvement réglé (~5,5 M) | Transactions prêtes pour l'agent conversationnel : libellés FR, `merchant_name` 100 % renseigné (0 NULL sur les paiements carte, noms commerciaux néobanques), `is_neobank_outflow` booléen strict, zéro IBAN PII. |
| `customer_monthly_spending` | `customer_id × period_month × category × direction` | Agrégats mensuels pré-calculés avec variation `M vs M-1`, moyenne 3 mois et part des dépenses mensuelles (`< 15 ms` dans AlloyDB). |
| `customer_recurring_commitments` | `customer_id × category` récurrente | Détection des revenus/charges récurrents, alertes proactives de hausse d'abonnement (`STRMFLIX DIGITAL` `15,99 € → 19,99 €`, `+4,00 €`) et charges restant à passer avant fin de mois. |
| `customer_card_spending_forecast` | 1 ligne par client (`80 000`) | Prévision zéro-shot `AI.FORECAST` (`TimesFM 2.5`, horizon 1 mois, IC 80 %) des dépenses carte mensuelles, avec repli statistique pour les clients `< 3` mois d'historique. |
| `customer_mobile_insights` | 1 ligne par client (`80 000`) | Table maîtresse synchronisée vers `AlloyDB` pour les 3 agents ADK : reste à vivre projeté (`+300,00 €` pour `CUST00002026`), alertes récentes et offre conforme `ACPR 2024-R-01` (coussin `>= 100 €`, plafond `70 %`, priorité Livret A / LDDS puis `Livret Boost Maison 3,50 %` sur 3 mois). |

## Construire & tester la couche GOLD (`dp_budget_insight`)

```bash
cd 02_demo2_silver_dbt_dq
uv run dbt seed --profiles-dir . --select movement_categories budget_insight_rules
uv run dbt build --profiles-dir . --select path:models/gold/budget_insight
```

## Backtesting chronologique `TimesFM 2.5` (`AI.EVALUATE`)

```bash
bq query --use_legacy_sql=false --project_id=data-days-demo --location=europe-west1 \
  --label datacloud:antigravity < 04_demo4_scale_mobile_adk/sql/01_evaluate_timesfm_budget_forecast.sql
```
