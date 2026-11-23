#!/usr/bin/env bash
# ==============================================================================
# Lance en local la Data Marketplace Knowledge Catalog (kc_marketplace_ui)
# - Backend API Express : http://localhost:3000
# - Frontend Vite React : http://localhost:5174 (sans conflit avec stage_ui :5173)
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI_DIR="${ROOT_DIR}/kc_marketplace_ui"

if [[ ! -d "${UI_DIR}" ]]; then
  echo "❌ Dossier introuvable : ${UI_DIR}" >&2
  exit 1
fi

cleanup() {
  echo ""
  echo "🛑 Arrêt de Knowledge Catalog Business UI..."
  [[ -n "${BACKEND_PID:-}" ]] && kill "${BACKEND_PID}" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "${FRONTEND_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "🚀 Démarrage du backend Knowledge Catalog sur http://localhost:3000 ..."
(
  cd "${UI_DIR}/backend"
  npm start
) &
BACKEND_PID=$!

echo "🎨 Démarrage du frontend Knowledge Catalog sur http://localhost:5174 ..."
(
  cd "${UI_DIR}"
  npm run dev -- --host localhost --port 5174 --strictPort
) &
FRONTEND_PID=$!

echo ""
echo "✅ Knowledge Catalog Data Marketplace prête :"
echo "   👉 Frontend : http://localhost:5174"
echo "   👉 Backend  : http://localhost:3000/api/health"
echo "   (Appuyez sur Ctrl+C pour arrêter les deux serveurs)"
echo ""

wait
