#!/usr/bin/env bash
# BoviScan Phase 1 mock E2E demo: start API → mock pipeline posts events → print web URL.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
API_PORT="${LW_API_PORT:-8000}"
API_BASE="${LW_API_BASE_URL:-http://127.0.0.1:${API_PORT}}"
DB_PATH="${LW_API_DB_PATH:-/tmp/boviscan-demo.db}"
WEB_URL="${LW_WEB_URL:-http://127.0.0.1:5173}"
STEPS="${1:-40}"

export LW_API_DB_PATH="$DB_PATH"
export LW_API_BASE_URL="$API_BASE"
export LW_CAMERA_BACKEND=mock
export LW_INFERENCE_BACKEND=cpu_mock
export LW_POST_API=true
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-boviscan-c2430}"
export FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-boviscan-c2430}"

echo "==> BoviScan demo (mock mode)"
echo "    API  $API_BASE"
echo "    DB   $DB_PATH"
echo "    WEB  $WEB_URL"

# Ensure venvs
if [[ ! -x "$ROOT/api/.venv/bin/python" ]]; then
  python3 -m venv "$ROOT/api/.venv"
  "$ROOT/api/.venv/bin/pip" install -q -e "$ROOT/api[dev]"
fi
if [[ ! -x "$ROOT/device/.venv/bin/python" ]]; then
  python3 -m venv "$ROOT/device/.venv"
  "$ROOT/device/.venv/bin/pip" install -q -e "$ROOT/device[dev]"
fi

rm -f "$DB_PATH"
API_PID=""
cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Starting companion API on :$API_PORT"
(
  cd "$ROOT/api"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn livestock_weight_api.main:app --host 127.0.0.1 --port "$API_PORT"
) &
API_PID=$!

# Wait for health
for i in $(seq 1 40); do
  if curl -sf "$API_BASE/health" >/dev/null; then
    break
  fi
  sleep 0.25
  if [[ "$i" -eq 40 ]]; then
    echo "API failed to become healthy" >&2
    exit 1
  fi
done
echo "    API healthy: $(curl -sf "$API_BASE/health")"

echo "==> Starting weighing session + mock pipeline (posting events)"
SESSION_JSON=$(curl -sf -X POST "$API_BASE/sessions/start" \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"device-local-01","notes":"run_demo.sh"}')
SESSION_ID=$(python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" <<<"$SESSION_JSON")
echo "    session_id=$SESSION_ID"

(
  cd "$ROOT/device"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  livestock-weight-device --steps "$STEPS" --post-api --api-base-url "$API_BASE" --session-id "$SESSION_ID"
)

echo "==> Events in API"
curl -sf "$API_BASE/events?session_id=$SESSION_ID&limit=10" | python3 -m json.tool | head -80
echo "==> Sync status (expect disabled/stub without credentials)"
curl -sf -X POST "$API_BASE/sync/run" | python3 -m json.tool
echo "==> CSV export: $API_BASE/sessions/$SESSION_ID/export.csv"

cat <<MSG

============================================================
BoviScan demo complete (mock).

Web UI (pt-BR):
  cd $ROOT/apps/web && npm install && npm run dev
  Open $WEB_URL

  - Console: start/stop session, live weight feed from API
  - Calibração: checklist 3 m / FOV / objeto de referência

API docs: $API_BASE/docs
Session:  $SESSION_ID
CSV:      $API_BASE/sessions/$SESSION_ID/export.csv

API will keep running until you Ctrl+C this script.
============================================================
MSG

if [[ "${LW_DEMO_EXIT:-}" == "1" ]]; then
  echo "(LW_DEMO_EXIT=1) stopping API and exiting"
  exit 0
fi

# Keep API up so user can point the web UI at it
wait "$API_PID"
