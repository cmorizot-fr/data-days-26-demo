# PRD — Agentic Data Cloud Day 2026 · Keynote Part 4 (Banque Hexagone)

- **Owner:** Matt Cornillon (`cornillon@google.com` / `matt@cmorizot.altostrat.com`)
- **Event:** Agentic Data Cloud Day Paris — **Thursday 26 Nov 2026** (Casino de Paris)
- **Keynote Slot:** **10:55–11:15** (20 min live demo, Matt + Clément) + **11:15–11:20** (5 min slide recap: AlloyDB Federation, AlloyDB, ADK)
- **Status:** Step 1 (Infra, Federation, Sync, Read Pool, Action Schema) **DONE** · Brand & Stitch UI **LOCKED** · Ready for Step 2 (App & ADK Build) in a fresh session.

---

## 1. Confirmed Decisions (from `/grill-me` alignment)

| Area | Decision |
| :--- | :--- |
| **Stage Hosting** | **Hybrid**: Local dev server (`Vite` + `FastAPI/ADK`) for live stage demo + **Cloud Run deployment** of `final` repo as an instant 5-second fallback. |
| **Act 1 — AlloyDB Sync** | **Live sync of 1 hero table** (`customer_mobile_insights`, ~23 s): keep the other 5 tables pre-synced; reset only `customer_mobile_insights` (+ dependent view) before the show; query `bq_fed.customer_mobile_insights` (`~600 ms`) live, trigger `alloydb_sync.create_bq_sync_table` live, recreate `v_customer_live_summary`, and show **`< 1 ms`** lookup on the Read Pool. |
| **GitHub Repositories** | 2 **Private** repos under `Matthieu68857`:<br>1. `Matthieu68857/banque-hexagone-mobile-starter` (Before app + 3 GitHub Issues + `.agents/skills/` + reset script)<br>2. `Matthieu68857/banque-hexagone-mobile-final` (Completed After app + deployed to Cloud Run). |
| **ADK & LLM** | Single **Root ADK Orchestrator** (`hexagone_coach`) delegating to **3 ADK sub-agents** (`budget_insight`, `offer_advisor`, `action_agent`) running on **Gemini Hydrogen** (Vertex AI in `data-days-demo`), paired with direct `< 15 ms` REST endpoints reading AlloyDB Read Pool for instant card rendering. |
| **Live `/swarm` Choreography** | **Start live, don't wait to finish**: Run `/swarm` live on `starter` to showcase the Antigravity Swarm UI spawning 3 parallel workers that immediately query live data via **DAK MCP**. After ~60–90 s of watching them work, switch to a **pre-run completed historical Swarm session** (with all 3 PRs/commits done) and demo the live `final` app. |
| **Stage Frame & Controls** | Clean `390 × 844` phone frame + subtle **toggleable Presenter Dock** (hotkey `P`) showing: live AlloyDB Read Pool latency badge (`ms`), **`Fire Live SEPA Payment`** button (Pub/Sub → Cloud Run → AlloyDB `live_movements`), and **`Reset Demo State`** button for instant rehearsals. |

---

## 2. Live Infrastructure & Verified Data Contracts (Step 1 — Already Live)

- **GCP Project:** `data-days-demo` (`project_number: 1051798075322`, region `europe-west1`, gcloud account `matt@cmorizot.altostrat.com`)
- **Upstream Demo Repo:** `cmorizot-fr/data-days-26-demo` (Demo 4 infra & SQL committed at `afed9fb` under `04_demo4_scale_mobile_adk/`).
- **AlloyDB Cluster (`POSTGRES_18`, `READY`):**
  - Cluster: `projects/data-days-demo/locations/europe-west1/clusters/hexagone-d4-alloydb`
  - Primary: `hexagone-d4-primary` (`2 vCPU`, public IP `34.62.202.201`, IAM + mTLS, flags `alloydb_sync.enabled=on`, `bigquery_fdw.enabled=on`, `alloydb.iam_authentication=on`, `google_ml_integration.enable_model_support=on`)
  - Read Pool: `hexagone-d4-read-pool` (`2 vCPU`, 1 node, public IP `207.175.225.45`, IAM auth)
  - Database: `hexagone`
- **Real-Time SEPA Ingest (Already Live):**
  - Topic `sepa-payments-pacs008-topic` → Push Sub `sepa-payments-alloydb-ops-sub` (OIDC) → Cloud Run `hexagone-d4-payments-ingest` → `public.live_movements` (`v_live_movements_settled`).
- **AlloyDB Objects in `hexagone`:**
  - **Federated (`bigquery_fdw`, schema `bq_fed` — requires RW session on primary):**
    - `bq_fed.customer_mobile_insights` (`~600 ms`)
    - `bq_fed.customer_monthly_spending` (`5.0M` rows, `~1.6 s`)
    - `bq_fed.customer_transactions_enriched` (`5.5M` rows)
  - **Synced (`alloydb_sync`, schema `public`, 1h refresh — works on Read Pool in `< 1 ms`):**
    - `public.customer_mobile_insights` (`80k` rows, PK `customer_id`, `0.097 ms` lookup)
    - `public.customer_card_spending_forecast` (`80k` rows, PK `customer_id`)
    - `public.customer_recurring_commitments` (`198,636` rows)
    - `public.savings_offers` (`4` rows, PK `offer_code` — synced from `silver_bank.savings_offers`)
    - `public.movement_categories` (`18` rows)
    - `public.budget_insight_rules` (`1` row)
  - **Operational Transactional (`public`):**
    - `public.live_movements` + `public.v_live_movements_settled`
    - `public.savings_transfers` (ACID target for Action Agent: `transfer_id`, `idempotency_key`, `customer_id`, `source_account_id`, `target_offer_code`, `target_offer_label`, `amount_eur`, `rate_bps`, `acpr_cushion_ok`, `status`, `initiated_by`, `created_at`)
    - `public.v_customer_live_summary` (joins `customer_mobile_insights` + `v_live_movements_settled` + `savings_transfers` → exposes `live_current_balance_eur`, `live_eom_surplus_eur`, `savings_transferred_eur`).
- **Witness Customer Baseline (`CUST00002026` — Lucas Martin, `ACC00002026`):**
  - D-1 balance: **`6 892,00 €`**
  - Subscription hike: **`STRMFLIX DIGITAL`** (`15,99 € → 19,99 €`, **`+4,00 €`**)
  - Health refund: **`CPAM ILE DE FRANCE`** (**`+42,00 €`**)
  - TimesFM 2.5 card forecast: **`788,00 €`** → EOM surplus: **`+300,00 €`**
  - ACPR 2024-R-01 reco: **`200,00 €`** (`>= 100 €` cushion preserved, `<= 70 %` surplus) · Primary `LIVRET_A` (`3,00 %`) · Alternative `LIV_BOOST_MAISON` (`3,50 %` over 3 months).

---

## 3. Locked Brand & Stitch UI Specification

- **Brand Assets:**
  - Interactive Brand Sheet: [hexagone_brand_sheet.html](file:///usr/local/google/home/cornillon/ace/banque-hexagone/brand/hexagone_brand_sheet.html)
  - Design Tokens: [DESIGN.md](file:///usr/local/google/home/cornillon/ace/banque-hexagone/brand/DESIGN.md)
- **Stitch Project:** `717705868757685868` (*Banque Hexagone — Mobile Keynote 2026*), Design System `assets/5606578281136188180` (*Hexagone Fintech Design System — Light Stage*).
- **Matched Light-Mode Screens (download HTML from Stitch via `download_file` in Step 2 as exact visual reference):**
  - **Before (Starter):** `7039702ec3794b588d47656838d684e9` — Light `#FAFAFA` canvas, dark Ink `#11131A` hero account card (`6 892,00 €`, `Visa Infinite · •••• 4829`, hexagon watermark & Indigo→Coral hairline), `Compte Courant` / `Livret A` switcher, 4 circular quick-action buttons (`Virement`, `Ajouter`, `Cartes`, `RIB`), and `Dernières opérations` with tinted category icons.
  - **After (Final):** `39620453242043528138187cd5995f20` — **Exact same shell**, with ONLY the 3 new features slotted cleanly between quick-actions and `Dernières opérations`: (1) Budget Insight card, (2) Conseil Épargne ACPR 1-clic card, (3) floating `Coach IA` pill.

---

## 4. Technical Architecture & Disjoint File Ownership

```text
banque-hexagone-mobile-{starter|final}/
├── .agents/skills/
│   ├── alloydb-federation-and-sync/SKILL.md
│   ├── hexagone-adk-conventions/SKILL.md
│   └── hexagone-swarm-orchestrator/SKILL.md
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, registers core + 3 feature routers
│   │   ├── db.py                        # AlloyDB Python Connector (IAM) pools: read_pool + primary
│   │   ├── core_routes.py               # /api/account, /api/transactions, /api/presenter/* (SEPA fire + reset)
│   │   └── features/
│   │       ├── budget_insight/          # [OWNED BY ISSUE #1 / budget-worker]
│   │       │   ├── agent.py             # ADK budget_insight_agent (Gemini Hydrogen)
│   │       │   └── router.py            # GET /api/features/budget-insight/{customer_id}
│   │       ├── offer_advisor/           # [OWNED BY ISSUE #2 / offers-worker]
│   │       │   ├── agent.py             # ADK offer_advisor_agent (ACPR 2024-R-01)
│   │       │   └── router.py            # GET /api/features/offers/{customer_id}
│   │       └── action_agent/            # [OWNED BY ISSUE #3 / action-worker]
│   │           ├── agent.py             # ADK action_agent (1-click transfer tool)
│   │           └── router.py            # POST /api/features/transfers
│   ├── agents/
│   │   └── hexagone_coach/agent.py      # Root ADK orchestrator composing the 3 sub-agents + /api/chat
│   ├── Dockerfile
│   └── pyproject.toml                   # Managed with uv
├── frontend/                            # React + Vite + Tailwind (390x844 mobile frame + Presenter Dock)
│   └── src/
│       ├── App.tsx                      # Shared Hexagone shell with 3 feature slots + PresenterDock (hotkey 'P')
│       ├── components/                  # HeroAccountCard, QuickActions, TransactionsList, PresenterDock, CoachDrawer
│       └── features/
│           ├── budget_insight/          # [OWNED BY ISSUE #1] BudgetInsightCard.tsx
│           ├── offer_advisor/           # [OWNED BY ISSUE #2] OfferAdvisorCard.tsx
│           └── action_agent/            # [OWNED BY ISSUE #3] TransferConfirmSheet.tsx
└── scripts/
    └── reset_demo4.sh                   # Full reset (git + AlloyDB transfers/live_movements + optional --reset-hero-sync)
```

---

## 5. The 3 GitHub Issues (PRDs / User Journeys for `starter`)

1. **Issue #1 — `[Feature] Budget Insight Agent (« Depuis votre dernière connexion » + TimesFM)`**
   - **User Journey:** When Lucas opens Hexagone, he immediately sees what changed since his last login (`STRMFLIX DIGITAL +4,00 €`, `CPAM +42,00 €`, TimesFM EOM surplus `+300,00 €` + clean mini forecast curve) loaded in `< 15 ms` from AlloyDB Read Pool, and can ask the ADK Coach spending/subscription questions.
   - **Data Contract:** `public.v_customer_live_summary`, `public.customer_recurring_commitments`, `public.customer_card_spending_forecast`, `bq_fed.customer_monthly_spending` (on primary RW for deep MoM breakdown).
   - **Owned Paths:** `backend/app/features/budget_insight/*`, `frontend/src/features/budget_insight/*`.
2. **Issue #2 — `[Feature] Conseil Offres Agent (Recommandation Épargne ACPR 2024-R-01)`**
   - **User Journey:** Based on Lucas's live surplus, Hexagone recommends placing `200,00 €` while guaranteeing his `100 €` safety cushion (`ACPR 2024-R-01` badge), letting him toggle between `Livret A · 3,00 %` and `Livret Boost Maison · 3,50 % (3 mois)` with zero hardcoded rates.
   - **Data Contract:** `public.v_customer_live_summary`, `public.savings_offers`, `public.budget_insight_rules`.
   - **Owned Paths:** `backend/app/features/offer_advisor/*`, `frontend/src/features/offer_advisor/*`.
3. **Issue #3 — `[Feature] Action Agent (Virement Épargne 1-Clic dans AlloyDB)`**
   - **User Journey:** Tapping *"Épargner 200 € en 1 clic"* opens an explicit confirmation sheet (source `ACC00002026`, target offer, amount, ACPR cushion check). On confirm, the ADK Action Agent executes an idempotent ACID `INSERT` into `public.savings_transfers`, updating Lucas's live balance (`6 892,00 € → 6 692,00 €`) and Livret balance immediately.
   - **Data Contract:** `public.savings_transfers` (primary RW), `public.v_customer_live_summary` (read-after-write verification).
   - **Owned Paths:** `backend/app/features/action_agent/*`, `frontend/src/features/action_agent/*`.

---

## 6. Deterministic Workspace Skills (`.agents/skills/`)

1. **`alloydb-federation-and-sync`**: Guides DAK MCP (`dak-alloydb`) for Act 1: run `EXPLAIN ANALYZE` on `bq_fed.customer_mobile_insights` (`~600 ms`), run `alloydb_sync.create_bq_sync_table('data-days-demo.gold_bank.customer_mobile_insights', 'public.customer_mobile_insights', INTERVAL '1 hour', 'replace', ARRAY['customer_id'])`, recreate `public.v_customer_live_summary`, and benchmark `< 1 ms` on `hexagone-d4-read-pool`.
2. **`hexagone-swarm-orchestrator`**: Instructs the Swarm coordinator to read GitHub Issues #1, #2, #3 and spawn 3 parallel workers (`budget-worker`, `offers-worker`, `action-worker`) with `workspace: "share"` and **mandatory Step 1 = inspect live AlloyDB/BQ schemas via DAK MCP** (so the audience sees DAK tool calls immediately in the Swarm UI!).
3. **`hexagone-adk-conventions`**: Pins Google ADK Python patterns, **Gemini Hydrogen** model config on Vertex AI (`data-days-demo`), AlloyDB IAM Connector usage, Light Mode Hexagone tokens, French UI copy, and ACPR 2024-R-01 zero-hardcoding rules.

---

## 7. Next Fresh Session — Execution Checklist

1. **Verify Gemini Hydrogen exact model ID** in Vertex AI (`data-days-demo`).
2. **Download Stitch HTML** for screens `7039702ec3794b588d47656838d684e9` (Before) and `39620453242043528138187cd5995f20` (After) to match pixel-perfectly.
3. **Build & verify `Matthieu68857/banque-hexagone-mobile-final`** end-to-end against live `hexagone-d4-alloydb` (Read Pool + Primary + Pub/Sub Presenter Dock + 3 ADK sub-agents + Cloud Run fallback deploy).
4. **Carve out `Matthieu68857/banque-hexagone-mobile-starter`**: strip the 3 feature folders to empty slots, create the 3 GitHub Issues, add the 3 `.agents/skills/`, and add `scripts/reset_demo4.sh`.
5. **Run 1 full Swarm rehearsal** on `starter` to generate the authentic completed historical session & PRs, then run `reset_demo4.sh --reset-hero-sync` so everything is primed for stage!
