#!/usr/bin/env bash
# Placeholder: documents Hailo Dataflow Compiler CLI invocations.
# Does NOT bundle proprietary Hailo binaries or run them in CI.
# Requires a licensed Hailo AI Software Suite install on an x86 workstation.
#
# Usage (on a Hailo DFC machine, after editing paths):
#   ./ml/export/export_hef_placeholder.sh /path/to/model.onnx ./calib_images ./out
set -euo pipefail

ONNX="${1:-model.onnx}"
CALIB="${2:-./calib_images}"
OUT="${3:-./out}"
HW_ARCH="${HW_ARCH:-hailo8}"

echo "== BoviScan HEF export placeholder =="
echo "ONNX=$ONNX  CALIB=$CALIB  OUT=$OUT  HW_ARCH=$HW_ARCH"
echo
echo "This script only prints the intended commands."
echo "Install Hailo Dataflow Compiler separately; do not commit HEF/ONNX."
echo

mkdir -p "$OUT"

cat <<COMMANDS
# --- Illustrative DFC flow (adjust to your hailo CLI version) ---

# 1) Parse ONNX → HAR
hailo parser onnx "$ONNX" --har-path "$OUT/model.har"

# 2) Optimize + quantize with farm calibration frames (~3 m AGL)
hailo optimize "$OUT/model.har" \\
  --calib-set-path "$CALIB" \\
  --optimized-har-path "$OUT/model_optimized.har"

# 3) Compile → HEF for Hailo-8
hailo compiler "$OUT/model_optimized.har" \\
  --hw-arch "$HW_ARCH" \\
  --hef-path "$OUT/detect.hef"

# 4) Inspect (on device or host with HailoRT)
hailortcli parse-hef "$OUT/detect.hef"

# 5) Deploy (example)
# scp "$OUT/detect.hef" pi@device:/opt/livestock-weight/models/detect.hef
# Set inference.backend=hailo and inference.hef_path accordingly.
COMMANDS

if ! command -v hailo >/dev/null 2>&1; then
  echo
  echo "note: 'hailo' CLI not found on PATH — expected on DFC workstation only."
  exit 0
fi

echo
echo "'hailo' found on PATH. Refusing to auto-run proprietary steps from CI placeholder."
echo "Run the printed commands manually after validating versions."
exit 0
