#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export LW_CAMERA_BACKEND=mock
export LW_INFERENCE_BACKEND=cpu_mock
cd "$ROOT/device"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python -m livestock_weight_device --steps "${1:-30}" --json
