# Démo #4 · Banque Hexagone · Socle opérationnel AlloyDB (`bigquery_fdw` + `alloydb_sync`)

## Ce qui tourne (`20/11/2026`)

| Ressource | Valeur |
|---|---|
| Cluster AlloyDB | `hexagone-d4-alloydb`, PostgreSQL 18, `europe-west1` (`READY`) |
| Primaire | `hexagone-d4-primary`, 2 vCPU, zonal, IP publique + IAM + mTLS (`READY`) |
| Pool de lecture | `hexagone-d4-read-pool`, 2 vCPU, 1 nœud, IP publique + IAM (`READY`) |
| Flags primaire | `alloydb.iam_authentication`, `alloydb_sync.enabled`, `bigquery_fdw.enabled`, `google_ml_integration.enable_model_support`, `password.enforce_complexity` |
| IAM BigQuery du cluster SA | `c-1051798075322-3e1d916d@gcp-sa-alloydb.iam.gserviceaccount.com` → `bigquery.dataViewer`, `bigquery.jobUser`, `bigquery.readSessionUser` |
| Base | `hexagone` |
| Ingestion temps réel | Pub/Sub `sepa-payments-alloydb-ops-sub` (push OIDC) → Cloud Run `hexagone-d4-payments-ingest` → `public.live_movements` |

## Fédération (`bigquery_fdw`) vs. Synchronisation (`alloydb_sync`)

| Mode | Objets dans `hexagone` | Latence mesurée (`CUST00002026`) | Usage Démo #4 |
|---|---|---|---|
| **Fédération zéro-copie** (`bigquery_fdw`, schéma `bq_fed`) | `bq_fed.customer_mobile_insights`, `bq_fed.customer_monthly_spending` (`5,0 M`), `bq_fed.customer_transactions_enriched` (`5,5 M`) | `~600 ms` (insights) / `~1,6 s` (spending) — session RW sur le primaire | Exploration HTAP sans copie et historique détaillé à la demande |
| **Synchronisation locale** (`alloydb_sync`, schéma `public`, refresh `1h`) | `customer_mobile_insights` (`80k`), `customer_card_spending_forecast` (`80k`), `customer_recurring_commitments` (`198,6k`), `savings_offers` (`4`), `movement_categories` (`18`), `budget_insight_rules` (`1`) | **`0,097 ms`** (primaire) / **`< 15 ms`** (Read Pool + vue live) | Exposition mobile haute concurrence et agents `ADK` |
| **Opérationnel transactionnel** (`public`) | `live_movements`, `v_live_movements_settled`, `savings_transfers`, `v_customer_live_summary` | `< 15 ms` | Flux SEPA J0 + virements 1-clic de l'Agent Action |

## Fichiers

- `infra/config.sh`, `infra/01_alloydb.sh`, `infra/02_payments_ingest.sh` : provisioning idempotent GCP.
- `services/payments_ingest/` : service FastAPI Cloud Run d'ingestion temps réel Pub/Sub → AlloyDB.
- `sql/alloydb/00_base.sql` : table `live_movements` + vue `v_live_movements_settled`.
- `sql/alloydb/01_federation_and_sync.sql` : `bigquery_fdw` (`bq_fed.*`) + `alloydb_sync` (`public.*`).
- `sql/alloydb/02_action_schema.sql` : table `savings_transfers` + vue `v_customer_live_summary`.
- `sql/alloydb/03_reset_demo4.sql` : reset propre avant chaque répétition ou passage sur scène.
