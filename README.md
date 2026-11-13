# Paris Data Summit 2026 — Agentic Data Cloud Demo

Dépôt de démonstration end-to-end illustrant le passage d'un SI bancaire siloté à une architecture gouvernée sur **Google's Agentic Data Cloud**, de la couche `RAW` aux agents mobiles temps réel.

Le document de référence métier et technique est [`DESIGN_AND_CONTEXT.md`](./DESIGN_AND_CONTEXT.md).

## Structure du repository

```text
.
├── DESIGN_AND_CONTEXT.md              # Blueprint d'architecture & invariants métier
├── AGENTS.md                          # Règles pour Antigravity (AGY) & DAK
├── pyproject.toml                     # Dépendances Python (gérées via uv)
├── .env.example                       # Variables d'environnement GCP / AWS / AlloyDB
├── docs/
│   └── assets/                        # Schémas d'architecture & supports
├── 00_data_generator/                 # Générateur déterministe (seed=2026) Couche 0
├── 01_demo1_raw_aggregation/          # BigLake AWS (Omni), Iceberg RAW & init dbt
├── 02_demo2_silver_dbt_dq/            # Modèles dbt SILVER, Data Quality & Data Products KC
├── 03_demo3_kc_semantics_cfo/         # Catalogues legacy, interviews .mp4, KC & BQ Agents
├── 04_demo4_scale_mobile_adk/         # BQML, alloydb_sync, ADK & App mobile Android
└── scripts/
    └── reset_demo_state.sh            # Remise à zéro entre répétitions
```

## Démarrage rapide

```bash
# 1. Configurer l'environnement local
cp .env.example .env

# 2. Installer les dépendances Python avec uv
uv sync
```
