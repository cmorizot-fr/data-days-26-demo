#!/usr/bin/env bash
# ==============================================================================
# startup.sh — Lance les 2 UIs de la démo (Demo UI + Business UI)
# - Vérifie les ports 5173, 5174 et 3000, et tue toute ancienne instance
# - Démarre :
#   1. Business UI Backend (kc_marketplace_ui/backend) -> http://localhost:3000
#   2. Business UI Frontend (kc_marketplace_ui)        -> http://localhost:5174
#   3. Demo UI (stage_ui)                              -> http://localhost:5173
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_UI_DIR="${ROOT_DIR}/stage_ui"
KC_UI_DIR="${ROOT_DIR}/kc_marketplace_ui"
KC_BACKEND_DIR="${KC_UI_DIR}/backend"

PORTS=(5173 5174 3000)
EXPECTED_PROJECT="data-days-demo"
export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

check_gcloud_auth() {
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "❌ 'gcloud' introuvable dans le PATH. Vérifie ton installation Google Cloud SDK." >&2
    exit 1
  fi

  local active_account
  active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
  if [[ -z "${active_account}" ]] || ! gcloud auth print-access-token >/dev/null 2>&1; then
    echo "❌ Authentification gcloud absente ou expirée." >&2
    echo "👉 Lance : gcloud auth login && gcloud auth application-default login" >&2
    exit 1
  fi

  local active_project
  active_project="$(gcloud config get-value project 2>/dev/null || true)"
  if [[ "${active_project}" != "${EXPECTED_PROJECT}" ]]; then
    echo "⚠️  Projet gcloud actif '${active_project:-aucun}' ≠ '${EXPECTED_PROJECT}'. Bascule automatique..."
    gcloud config set project "${EXPECTED_PROJECT}" >/dev/null
    active_project="${EXPECTED_PROJECT}"
  fi

  echo "✅ Auth gcloud OK : ${active_account} (projet : ${active_project})"
}

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    echo "⚠️  Port ${port} déjà occupé (PID: ${pids//$'\n'/ }). Arrêt des anciennes instances..."
    echo "${pids}" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    local remaining
    remaining="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
    if [[ -n "${remaining}" ]]; then
      echo "🔨 Force-kill sur le port ${port} (PID: ${remaining//$'\n'/ })..."
      echo "${remaining}" | xargs kill -KILL 2>/dev/null || true
      sleep 0.5
    fi
  else
    echo "✅ Port ${port} libre."
  fi
}

echo "🔐 Vérification de l'authentification gcloud..."
check_gcloud_auth

echo ""
echo "🔍 Vérification et nettoyage des ports (${PORTS[*]})..."
for p in "${PORTS[@]}"; do
  free_port "${p}"
done

if [[ ! -d "${STAGE_UI_DIR}" ]] || [[ ! -d "${KC_UI_DIR}" ]] || [[ ! -d "${KC_BACKEND_DIR}" ]]; then
  echo "❌ Dossiers UI introuvables sous ${ROOT_DIR}" >&2
  exit 1
fi

PIDS=()
cleanup() {
  echo ""
  echo "🛑 Arrêt des serveurs..."
  for pid in "${PIDS[@]:-}"; do
    kill -TERM "${pid}" 2>/dev/null || true
  done
  for p in "${PORTS[@]}"; do
    local rem
    rem="$(lsof -ti "tcp:${p}" 2>/dev/null || true)"
    [[ -n "${rem}" ]] && echo "${rem}" | xargs kill -TERM 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo ""
echo "🚀 Démarrage de Business UI Backend (:3000)..."
(
  cd "${KC_BACKEND_DIR}"
  npm start
) &
PIDS+=($!)

echo "🚀 Démarrage de Business UI Frontend (:5174)..."
(
  cd "${KC_UI_DIR}"
  npm run dev -- --host localhost --port 5174 --strictPort
) &
PIDS+=($!)

echo "🚀 Démarrage de Demo UI (:5173)..."
(
  cd "${STAGE_UI_DIR}"
  npm run dev -- --host localhost --port 5173 --strictPort
) &
PIDS+=($!)

sleep 2
echo ""
echo "✅ Les 2 UIs sont lancées :"
echo "   👉 Demo UI (Antigravity)      : http://localhost:5173"
echo "   👉 Business UI (Marketplace)  : http://localhost:5174"
echo "   👉 Business UI Backend API    : http://localhost:3000/api/health"
echo ""
echo "   (Appuie sur Ctrl+C pour tout arrêter proprement)"
echo ""

wait
