#!/usr/bin/env bash
# BoviScan performance / thermal soak wrapper
# Usage: ./ops/scripts/soak_device.sh [frames] [backend]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRAMES="${1:-100}"
BACKEND="${2:-${LW_INFERENCE_BACKEND:-cpu_mock}}"
OUT="${SOAK_OUT:-$ROOT/artifacts/soak-$(date -u +%Y%m%dT%H%M%SZ).json}"
mkdir -p "$(dirname "$OUT")"
export LW_INFERENCE_BACKEND="$BACKEND"
export LW_CAMERA_BACKEND="${LW_CAMERA_BACKEND:-mock}"
cd "$ROOT/device"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python scripts/soak.py --frames "$FRAMES" --backend "$BACKEND" --out "$OUT"
echo "soak results: $OUT"
