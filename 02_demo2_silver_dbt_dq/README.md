# Couche SILVER — projet `dbt` (`02_demo2_silver_dbt_dq/`)

Transformations `RAW → SILVER` de la Banque Hexagone, industrialisées avec **dbt** (`dbt-bigquery` 1.10) sur le projet `data-days-demo` (`europe-west1`). Chaque table SILVER appartient à un **Data Product** défini dans [`kc_products/data_products_catalog.yaml`](./kc_products/data_products_catalog.yaml).

## Lancer
```bash
gcloud auth application-default login          # une fois (identifiants ADC)
cd 02_demo2_silver_dbt_dq
uv run dbt build --profiles-dir .              # seed + modèles + tests
uv run dbt build --profiles-dir . --select +path:models/silver/customer_360   # un seul Data Product
```
- `profiles.yml` est versionné et **ne contient aucun secret**.
- La cible de repli `gcloud_token` s'utilise sans ADC :
  ```bash
  DBT_BQ_TOKEN=$(gcloud auth print-access-token) uv run dbt build --profiles-dir . --target gcloud_token
  ```
- Chaque job BigQuery porte le label `datacloud:antigravity`, défini par `query-comment` dans `dbt_project.yml`.

## Structure
```text
02_demo2_silver_dbt_dq/
├── dbt_project.yml              # staging -> raw_bank (vues stg_*), silver -> silver_bank (tables), labels data_product
├── profiles.yml                 # cibles prod (ADC) et gcloud_token
├── kc_products/
│   └── data_products_catalog.yaml   # catalogue de référence : 5 SILVER + 2 GOLD
├── macros/
│   ├── generate_schema_name.sql     # datasets utilisés tels quels (raw_bank, silver_bank)
│   ├── mainframe_cleaning.sql       # normalize_agency_code, parse_mainframe_date
│   └── tests/                       # tests génériques row_count_equals, expression_equals
├── seeds/
│   └── movement_category_rules.csv  # règles de catégorisation des mouvements (modifiables par le métier)
└── models/
    ├── staging/                     # 1 vue de nettoyage par source RAW + _raw_sources.yml
    └── silver/
        ├── customer_360/            # dp_customer_360
        └── customer_timeline/       # dp_customer_timeline
```

## Data Products construits
| Data Product | Table `silver_bank` | Grain | Contenu |
|---|---|---|---|
| `dp_customer_360` | `customers` | 1 ligne par client (80 000) | Fusion Mainframe + CRM AWS : profil, segment, agence normalisée, région, opt-in digital, `is_mainframe_orphan` (650) |
| `dp_customer_360` | `accounts` | 1 ligne par compte (95 000) | IBAN, type, taux, ouverture, **solde J-1** (Mainframe), `is_mainframe_orphan` |
| `dp_customer_timeline` | `customer_movements` | 1 ligne par mouvement réglé (~5,5 M) | Vie du client catégorisée : montant signé, catégorie et famille, contrepartie (nom, IBAN, BIC), `is_neobank_outflow`, `is_internal_transfer`, `value_date_was_invalid` |
| `dp_customer_timeline` | `beneficiaries` | 1 ligne par compte et IBAN (113 936) | Bénéficiaires externes ajoutés, néobanque ou courtier, canal, première date d'enrôlement |

Les 3 autres Data Products SILVER (`dp_customer_relationship`, `dp_finance_pnb`, `dp_commercial_commitments`) et les 2 GOLD (`dp_budget_insight`, `dp_certified_pnb`) restent à construire. Le dictionnaire complet des colonnes est dans les fichiers `_*.yml` de chaque dossier et poussé dans BigQuery (`persist_docs`).

## Règles de qualité appliquées
| Anomalie RAW | Traitement SILVER |
|---|---|
| Codes agence `'42  '` ou vides (9 773 clients) | `normalize_agency_code` : `LPAD` sur 4 caractères, repli sur le code guichet |
| Dates de valeur `00000000` / `99999999` (66 000) | Remplacées par la date comptable, signalées par `value_date_was_invalid` ; aucune ligne supprimée |
| Doublons techniques de paiements (3,4 %) | 1 ligne par `end_to_end_id` (première exécution) |
| Paiements `RJCT` / `PDNG` (8,1 %) | Exclus des mouvements (seuls les paiements `ACSC` sont réglés) |
| Même virement dans le Mainframe et dans SEPA | Le Mainframe fait foi, SEPA l'enrichit ; seuls les paiements postérieurs au batch J-1 ou des comptes hors Mainframe sont ajoutés |
| 650 comptes absents du Mainframe J-1 | Conservés et signalés (`is_mainframe_orphan`) ; leurs paiements alimentent la timeline |

## Tests (39) et contrats
- Clés uniques et non nulles, valeurs autorisées, liens `accounts → customers` et `customer_movements → customers / accounts`.
- Volumétries exactes : 80 000 clients, 95 000 comptes, 5 500 000 mouvements issus du Mainframe.
- Invariants métier :
  - `neobank_leak_90d_equals_2_42bn` : fuite vers les néobanques sur 90 jours = 2 420 000 000,00 € ;
  - `no_sepa_payment_counted_twice` : aucun paiement SEPA compté deux fois.
- Documentation : 75/75 colonnes de `silver_bank` décrites.

## Ajouter un Data Product
1. Le déclarer d'abord dans `kc_products/data_products_catalog.yaml` (AGENTS.md §3), avec un nom en anglais.
2. Créer `models/silver/<domaine>/` avec ses modèles et un `_<domaine>.yml` : descriptions de toutes les colonnes, tests, `meta.data_product`.
3. Ajouter le label `data_product` dans `dbt_project.yml`.
4. `uv run dbt build --profiles-dir .`, puis contrôle visuel ([`bq-visual-audit`](../.agents/skills/bq-visual-audit/SKILL.md)).
5. Le faire apparaître dans la démo avec le skill [`stage-ui-step-authoring`](../.agents/skills/stage-ui-step-authoring/SKILL.md).
