#!/usr/bin/env bash
set -euo pipefail

# Remise à zéro de l'environnement de démo entre deux répétitions.
# Usage : ./scripts/reset_demo_state.sh [--stage demo1|demo2|demo3|demo4|all]

STAGE="${1:---stage}"
TARGET="${2:-all}"

if [[ "$STAGE" != "--stage" ]]; then
  TARGET="$STAGE"
fi

echo "[reset_demo_state] Cible sélectionnée : $TARGET"
echo "[reset_demo_state] Script squelette prêt — les commandes BigQuery/GCS/AlloyDB seront branchées au fil des étapes."
