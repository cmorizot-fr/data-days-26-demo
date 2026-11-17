# État des données — Démo Banque Hexagone

> Dernière mise à jour : 17/11/2026. À tenir à jour à chaque régénération ou nouveau Data Product.

Projet `data-days-demo` · région `europe-west1` · données synthétiques déterministes (`seed=2026`).

## En bref
- **RAW** : les 5 silos sont chargés dans `raw_bank`, **cohérents entre eux** et certifiés.
- **SILVER** : 2 Data Products sur 5 sont construits avec `dbt` (`dp_customer_360`, `dp_customer_timeline`), **39/39 tests OK**, 100 % des colonnes documentées.
- **GOLD** : pas encore construit (`dp_budget_insight`, `dp_certified_pnb`).

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
| `dp_customer_360` | `customers` (80 000), `accounts` (95 000) | Référentiel client et comptes unifié Mainframe + CRM, solde J-1, 650 orphelins signalés | ✅ |
| `dp_customer_timeline` | `customer_movements` (5,5 M), `beneficiaries` (113 936) | Vie du client catégorisée (revenus, charges fixes, carte, épargne, néobanques) : le Mainframe fait foi, enrichi par SEPA, flux temps réel ajouté | ✅ |
| `dp_customer_relationship` | `interactions` | Interactions CRM | ⏳ à faire |
| `dp_finance_pnb` | `gl_entries` | Grand livre SAP, budget, coût ALM | ⏳ à faire |
| `dp_commercial_commitments` | `promo_contracts` | 250 PDF extraits par IA | ⏳ à faire |

Le catalogue de référence est dans [`data_products_catalog.yaml`](../02_demo2_silver_dbt_dq/kc_products/data_products_catalog.yaml). Les noms techniques sont en anglais.

## Chiffres clés à retenir (identiques dans tous les silos)
| Indicateur | Valeur |
|---|---|
| Fuite des dépôts vers les néobanques (90 j) | **2 420 000 000,00 €**, dont 68,0 % chez les 18-32 ans entre le 1er et le 5 du mois |
| Écart PNB, requête naïve | **+42 800 000,00 €** |
| Écart PNB, certifié | **-38 420 000,00 €** (-24,12 M€ coût ALM à 3,99 % + -14,30 M€ promos PDF) |
| Client témoin | Lucas Martin `CUST00002026` : abonnement +4 €, remboursement santé +42 €, excédent fin de mois +300 € |

## Comment régénérer / vérifier
```bash
./scripts/generate_all_data.sh                    # génération + GCS + chargements
./scripts/run_demo1_mainframe_spark_iceberg.sh    # Mainframe -> Iceberg (Spark)
./scripts/run_demo1_payments_history_unified.sh   # paiements historique + temps réel
cd 02_demo2_silver_dbt_dq && uv run dbt build --profiles-dir .   # couche SILVER + tests (voir 02_demo2_silver_dbt_dq/README.md)
```
Contrôles locaux : `validate_corebanking.py` (10/10), `validate_payments_coherence.py` (9/9) et `verify_invariants.py` (15/15).

## Limites connues
- **Vie client simplifiée** : 3 à 5 opérations par client et par mois (volume plafonné à 5,5 M de mouvements). La plupart des clients ont donc un excédent mensuel élevé. Le client témoin, lui, est calibré.
- **Scénario de l'UI** : certains chiffres affichés dans l'interface (Démo 2) sont écrits à la main et ne reflètent pas encore les vrais résultats (ex. nombre de tests).
- **Authentification dbt** : nécessite `gcloud auth application-default login` (le `profiles.yml` versionné ne contient aucun secret).

## Prochaines étapes
1. Construire les 3 Data Products SILVER restants.
2. GOLD : `dp_budget_insight` (prévision de fin de mois, Démo 4) et `dp_certified_pnb` (Démo 3).
3. Publier les Data Products dans Knowledge Catalog et aligner le scénario de l'UI sur les vrais résultats.
4. Ajuster la vie client (plus d'opérations carte) si le Budget Insight doit montrer des restes à vivre plus variés.
