#!/usr/bin/env bash
# BoviScan pre-Pi software smoke gate (no Pi / Hailo / cloud creds required).
# Usage: ./ops/scripts/pre_pi_smoke.sh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Step results: name|status|detail
declare -a RESULTS=()
FAILED=0

pass() {
  local name="$1" detail="${2:-}"
  RESULTS+=("PASS|$name|$detail")
  printf '✓ PASS  %s%s\n' "$name" "${detail:+ — $detail}"
}

fail() {
  local name="$1" detail="${2:-}"
  RESULTS+=("FAIL|$name|$detail")
  FAILED=1
  printf '✗ FAIL  %s%s\n' "$name" "${detail:+ — $detail}" >&2
}

note() {
  local name="$1" detail="${2:-}"
  RESULTS+=("NOTE|$name|$detail")
  printf '· NOTE  %s%s\n' "$name" "${detail:+ — $detail}"
}

ensure_venv() {
  # $1 = package dir (device|api)
  local pkg="$1"
  local venv="$ROOT/$pkg/.venv"
  if [[ ! -x "$venv/bin/pytest" ]]; then
    echo "==> Creating/installing $pkg/.venv [dev]"
    python3 -m venv "$venv"
    "$venv/bin/pip" install -q -e "$ROOT/$pkg[dev]"
  fi
}

echo "============================================================"
echo "BoviScan pre-Pi software smoke gate"
echo "  root: $ROOT"
echo "============================================================"
echo

# --- 1. Device pytest ---
echo "==> [1/7] pytest device/tests"
ensure_venv device
RC=0
(
  cd "$ROOT/device"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pytest -q tests
) || RC=$?
if [[ "$RC" -eq 0 ]]; then
  pass "device pytest" "device/tests"
else
  fail "device pytest" "exit $RC"
fi
echo

# --- 2. API pytest + Hailo note ---
echo "==> [2/7] pytest api/tests"
ensure_venv api
RC=0
(
  cd "$ROOT/api"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pytest -q tests
) || RC=$?
if [[ "$RC" -eq 0 ]]; then
  pass "api pytest" "api/tests"
else
  fail "api pytest" "exit $RC"
fi
note "Hailo fallback" "covered by device tests (test_hailo_backend / cpu_mock fallback)"
echo

# --- 3. Demo (non-interactive) ---
echo "==> [3/7] run_demo.sh (LW_DEMO_EXIT=1, 25 steps)"
RC=0
LW_DEMO_EXIT=1 "$ROOT/ops/scripts/run_demo.sh" 25 || RC=$?
if [[ "$RC" -eq 0 ]]; then
  pass "run_demo" "LW_DEMO_EXIT=1 steps=25"
else
  fail "run_demo" "exit $RC"
fi
echo

# --- 4. Soak ---
echo "==> [4/7] soak_device.sh 50 cpu_mock"
RC=0
"$ROOT/ops/scripts/soak_device.sh" 50 cpu_mock || RC=$?
if [[ "$RC" -eq 0 ]]; then
  pass "soak_device" "50 frames cpu_mock"
else
  fail "soak_device" "exit $RC"
fi
echo

# --- 5. Firestore dry-run ---
echo "==> [5/7] firestore_soak_check.py (dry-run)"
FS_OUT="$(mktemp)"
RC=0
python3 "$ROOT/ops/scripts/firestore_soak_check.py" >"$FS_OUT" 2>&1 || RC=$?
if [[ "$RC" -eq 0 ]] && grep -q '"ok": true' "$FS_OUT"; then
  MODE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('mode_estimate','?'))" "$FS_OUT" 2>/dev/null || echo "?")
  pass "firestore_soak_check" "dry-run ok mode=$MODE"
else
  fail "firestore_soak_check" "exit $RC (expect disabled/ok without creds)"
  cat "$FS_OUT" >&2 || true
fi
rm -f "$FS_OUT"
echo

# --- 6. Capture smoke (mock) ---
echo "==> [6/7] capture_smoke.py --out /tmp/boviscan-still.jpg"
RC=0
(
  cd "$ROOT/device"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python scripts/capture_smoke.py --out /tmp/boviscan-still.jpg --force-mock
) || RC=$?
if [[ "$RC" -eq 0 ]]; then
  pass "capture_smoke" "mock → /tmp/boviscan-still.jpg"
else
  fail "capture_smoke" "exit $RC"
fi
echo

# --- 7. Web build + test ---
echo "==> [7/7] apps/web npm ci|install + build + test"
WEB_RC=0
(
  cd "$ROOT/apps/web"
  if [[ -f package-lock.json ]]; then
    npm ci || npm install
  else
    npm install
  fi
  npm run build
  if node -e "const p=require('./package.json'); process.exit(p.scripts&&p.scripts.test?0:1)"; then
    npm test
  else
    echo "(no npm test script — skip)"
  fi
) || WEB_RC=$?
if [[ "$WEB_RC" -eq 0 ]]; then
  pass "web build+test" "apps/web"
else
  fail "web build+test" "exit $WEB_RC"
fi
echo

# --- Summary table ---
echo "============================================================"
echo "Pre-Pi smoke summary"
echo "============================================================"
printf '%-6s  %-24s  %s\n' "STATUS" "STEP" "DETAIL"
printf '%-6s  %-24s  %s\n' "------" "----" "------"
for row in "${RESULTS[@]}"; do
  IFS='|' read -r st name detail <<<"$row"
  printf '%-6s  %-24s  %s\n' "$st" "$name" "$detail"
done
echo "============================================================"
if [[ "$FAILED" -ne 0 ]]; then
  echo "RESULT: FAIL (one or more steps failed)"
  exit 1
fi
echo "RESULT: PASS (all software smoke gates green)"
exit 0
