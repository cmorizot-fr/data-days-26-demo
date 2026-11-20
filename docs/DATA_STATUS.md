# État des données — Démo Banque Hexagone

> Dernière mise à jour : 20/11/2026. À tenir à jour à chaque régénération ou nouveau Data Product.

Projet `data-days-demo` · région `europe-west1` · données synthétiques déterministes (`seed=2026`).

## En bref
- **RAW** : les 5 silos sont chargés dans `raw_bank`, **cohérents entre eux** et certifiés.
- **SILVER** : 5 / 5 Data Products construits avec `dbt` (`dp_customer_360`, `dp_customer_timeline`, `dp_customer_relationship`, `dp_finance_pnb`, `dp_commercial_commitments`), 100 % des colonnes documentées.
- **GOLD** : `dp_budget_insight` (Démo 4) construit et certifié dans `gold_bank` (5 tables, `AI.FORECAST TimesFM 2.5` sur 16 shards, `63/63` checks dbt, `134/134` colonnes documentées, `0` violation ACPR 2024-R-01) · `dp_certified_pnb` (Démo 3) reste à industrialiser.

> [!IMPORTANT]
> Les mouvements Mainframe et les paiements SEPA décrivent désormais **la même vie client** : chaque paiement réglé d'un compte Mainframe existe à l'identique dans les deux silos (même identifiant, date et montant). Contrôle de rapprochement : **0 écart**.

## Couche RAW (`raw_bank`)
| Silo | Tables | Volume | Mode d'accès |
|---|---|---|---|
| Mainframe z/OS (EBCDIC + CFONB) | `cbk_customers_ref`, `cbk_accounts_master`, `cbk_cfonb_movements`, `cbk_cfonb_balances` | 79 350 clients · 94 350 comptes · 5 500 000 mouvements | BigLake Iceberg (Spark Serverless) |
| CRM SaaS AWS | `aws_crm_customers`, `aws_crm_account_portfolio`, `aws_crm_interactions`, `aws_crm_branches_ref` | 80 000 clients · 95 000 comptes · 320 000 interactions | Iceberg sur GCS (sans copie) |
| Paiements SEPA | `raw_sepa_payments_history` + `_pubsub_stream` → vue `raw_sepa_payments_unified` | 6 200 000 événements historiques + flux temps réel | BigLake + Pub/Sub, CLS sur les champs sensibles |
| Bénéficiaires IBAN | `raw_iban_events_*` → vue `raw_iban_events_unified` | ~118 000 enrôlements | idem |
| Finance SAP / ALM | `raw_sap_gl_alm` | 1 200 000 écritures | Chargement direct (`bq load`) |
| Contrats PDF | `raw_promo_contracts_pdf`, `raw_cfo_regulatory_pdf` | 250 avenants + 6 normes CFO | Object Tables (Dataplex Discovery) |

**Anomalies volontairement conservées en RAW** (pour la Démo 2) :
- 3,4 % de doublons de paiements et 8,1 % de paiements rejetés ou en attente ;
- 66 000 dates de valeur Mainframe invalides (1,2 %) ;
- codes agence mal formés ;
- 650 comptes du CRM absents du Mainframe J-1.

## Couche SILVER (`silver_bank`, projet `dbt` dans `02_demo2_silver_dbt_dq/`)
| Data Product | Tables | Contenu | État |
|---|---|---|---|
| `dp_customer_360` | `customers` (80 000), `accounts` (95 000), `account_monthly_balances` (1 437 531) | Référentiel client et comptes unifié Mainframe + CRM, soldes 18 mois rapprochés, 650 orphelins signalés | ✅ |
| `dp_customer_timeline` | `customer_movements` (5,5 M), `beneficiaries` (113 936) | Vie du client catégorisée (revenus, charges fixes, carte, épargne, néobanques) : le Mainframe fait foi, enrichi par SEPA, flux temps réel ajouté | ✅ |
| `dp_customer_relationship` | `interactions` (320 000) | Interactions CRM, verbatims masqués par CLS, indicateurs risque de fuite | ✅ |
| `dp_finance_pnb` | `gl_entries` (1 200 000) | Grand livre SAP, budget BPC, coût ALM (naïf `+42,80 M€`, signé hors `58*` `-24,12 M€`) | ✅ |
| `dp_commercial_commitments` | `promo_contracts` (250), `promo_contracts_pdf_tracking` (250), `savings_offers` (4) | 250 PDF extraits par `AI.GENERATE` (`14,30 M€`), suivi PDF par PDF, offres d'épargne conformes ACPR 2024-R-01 | ✅ |

## Couche GOLD (`gold_bank`, projet `dbt` dans `02_demo2_silver_dbt_dq/models/gold/`)
| Data Product | Tables | Contenu | État |
|---|---|---|---|
| `dp_budget_insight` | `customer_transactions_enriched` (5,5 M), `customer_monthly_spending` (5,0 M), `customer_recurring_commitments` (198 636), `customer_card_spending_forecast` (80 000), `customer_mobile_insights` (80 000) | Transactions typées FR + marchands nettoyés (0 NULL), agrégats mensuels M vs M-1, détection des engagements récurrents & hausses d'abonnements (`14 627` alertes), prévision `AI.FORECAST (TimesFM 2.5)` (`68 927` clients + repli nouveaux clients), recommandations conformes ACPR 2024-R-01 (`72 234` éligibles, `7 766` protégés, `0` violation). Témoin `CUST00002026` : `+300,00 €` reste à vivre, `+4,00 €` `STRMFLIX DIGITAL`, `+42,00 €` CPAM, reco `200,00 €`. | ✅ |
| `dp_certified_pnb` | `v_cfo_certified_pnb_variance` | Écart PNB certifié (`-38,42 M€`) + Knowledge Catalog OKF (Démo 3) | ⏳ à industrialiser |

Le catalogue de référence est dans [`data_products_catalog.yaml`](../02_demo2_silver_dbt_dq/kc_products/data_products_catalog.yaml). Les noms techniques sont en anglais.

## Chiffres clés à retenir (identiques dans tous les silos)
| Indicateur | Valeur |
|---|---|
| Fuite des dépôts vers les néobanques (90 j) | **2 420 000 000,00 €**, dont 68,0 % chez les 18-32 ans entre le 1er et le 5 du mois |
| Écart PNB, requête naïve | **+42 800 000,00 €** |
| Écart PNB, certifié | **-38 420 000,00 €** (-24,12 M€ coût ALM à 3,99 % + -14,30 M€ promos PDF) |
| Client témoin | Lucas Martin `CUST00002026` : abonnement +4 €, remboursement santé +42 €, prévision carte TimesFM 788 €, excédent fin de mois +300 €, épargne conseillée ACPR 200 € |

## Comment régénérer / vérifier
```bash
./scripts/generate_all_data.sh                    # génération + GCS + chargements
./scripts/run_demo1_mainframe_spark_iceberg.sh    # Mainframe -> Iceberg (Spark)
./scripts/run_demo1_payments_history_unified.sh   # paiements historique + temps réel
cd 02_demo2_silver_dbt_dq && uv run dbt build --profiles-dir .   # couches SILVER + GOLD + tests
```
Contrôles locaux : `validate_corebanking.py` (10/10), `validate_payments_coherence.py` (9/9) et `verify_invariants.py` (15/15).

## Limites connues
- **Vie client simplifiée** : 3 à 5 opérations par client et par mois (volume plafonné à 5,5 M de mouvements). La plupart des clients ont donc un excédent mensuel élevé (médiane `+1 921,66 €`). Le client témoin, lui, est calibré (`+300,00 €`).
- **Scénario de l'UI** : certains chiffres affichés dans l'interface (Démos 3–4) restent à aligner sur les vrais résultats GOLD (`3,50 %` ACPR vs `4 %` dans le brouillon).
- **Authentification dbt** : nécessite `gcloud auth application-default login` ou la cible `--target gcloud_token` (le `profiles.yml` versionné ne contient aucun secret).

## Prochaines étapes
1. Démo #4 : synchroniser `gold_bank` (`dp_budget_insight`) vers `AlloyDB` (`alloydb_sync`, `< 15 ms`) et brancher les 3 agents mobiles `ADK`.
2. Démo #3 : industrialiser `dp_certified_pnb` + Context Set Knowledge Catalog OKF.
3. Aligner `stage_ui/public/demo_config.yaml` sur les vrais résultats GOLD.
