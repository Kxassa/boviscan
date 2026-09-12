#!/usr/bin/env bash
# BoviScan — Raspberry Pi 5 + Camera Module 3 + Hailo-8 bring-up checklist
# Run on the Pi (or review commands offline). Safe to re-run.
set -euo pipefail

BOLD='\033[1m';NC='\033[0m'
OK='[OK]';WARN='[!!]'
INFO='[--]'

echo -e "${BOLD}BoviScan Pi 5 bring-up${NC}"
echo "Project: boviscan-c2430 | Camera ~3.0 m AGL | Storage target ≥128 GB"
echo

step() { echo -e "\n${BOLD}$1${NC}"; }

step "1. OS / architecture"
uname -a || true
if grep -qi 'Raspberry Pi' /proc/device-tree/model 2>/dev/null || \
   grep -qi raspberry /proc/cpuinfo 2>/dev/null; then
  echo "$OK Detected Raspberry Pi"
  cat /proc/device-tree/model 2>/dev/null; echo
else
  echo "$WARN Not running on a Pi — checklist continues with mock-friendly checks"
fi

step "2. Storage layout (128 GB+)"
df -h / /home 2>/dev/null || df -h
echo "$INFO Recommended layout:"
echo "  /               — OS + packages"
echo "  /var/lib/boviscan — SQLite + capture spool (bind mount or large partition)"
echo "  /mnt/data       — optional NVMe for frames/datasets"
echo "  Keep ≥20% free; prefer industrial microSD or NVMe"
mkdir -p /tmp/boviscan-check
echo "$OK Writable scratch: /tmp/boviscan-check"

step "3. Camera / libcamera / picamera2"
if command -v libcamera-hello >/dev/null 2>&1; then
  echo "$OK libcamera-hello present"
  echo "$INFO Smoke (5s preview, skip if headless): libcamera-hello -t 5000"
else
  echo "$WARN libcamera-hello not found — enable camera via raspi-config / Bookworm camera stack"
fi
python3 - <<'PY' || true
try:
    import picamera2
    print("[OK] picamera2 importable:", getattr(picamera2, "__file__", "?"))
except Exception as e:
    print("[!!] picamera2 not importable:", e)
    print("     On Pi OS: sudo apt install -y python3-picamera2  (or pip install -e '.[pi]')")
PY

step "4. Hailo driver / runtime presence (optional)"
if ls /dev/hailo* >/dev/null 2>&1; then
  echo "$OK Hailo device node(s) present:"
  ls -l /dev/hailo* 2>/dev/null || true
else
  echo "$WARN No /dev/hailo* — Hailo HAT not present or driver not loaded (CPU mock OK)"
fi
if command -v hailortcli >/dev/null 2>&1; then
  echo "$OK hailortcli found"
  hailortcli fw-control identify 2>/dev/null | head -20 || true
else
  echo "$INFO hailortcli not on PATH — install HailoRT when accelerating with HEF"
fi
python3 - <<'PY' || true
try:
    import hailo_platform  # noqa: F401
    print("[OK] hailo_platform importable")
except Exception:
    print("[--] hailo_platform not installed (expected until HEF path is wired)")
PY

step "5. Thermal notes"
if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
  t=$(cat /sys/class/thermal/thermal_zone0/temp)
  echo "$INFO SoC temp: $(awk -v t="$t" 'BEGIN{printf "%.1f C\n", t/1000}')"
else
  echo "$INFO No thermal_zone0 (not on Pi or sysfs limited)"
fi
echo "$INFO Continuous Hailo+Pi inference needs airflow; official 27W PSU recommended."
echo "$INFO Throttle check: vcgencmd get_throttled  (0x0 = good)"

step "6. Device package + capture smoke"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "$INFO Repo root: $REPO_ROOT"
if [[ -d "$REPO_ROOT/device" ]]; then
  echo "$OK device/ present"
  echo "$INFO Install: cd device && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
  echo "$INFO Capture smoke: python device/scripts/capture_smoke.py --out /tmp/boviscan-still.jpg"
else
  echo "$WARN device/ not found at $REPO_ROOT/device"
fi

step "7. Config checklist"
echo "  [ ] camera.height_m: 3.0 in device.yaml"
echo "  [ ] camera.backend: picamera2 (on Pi) or mock (laptop)"
echo "  [ ] inference.backend: cpu_mock until HEF ready; hailo when HEF+HailoRT installed"
echo "  [ ] LW_API_BASE_URL points at companion API"
echo "  [ ] See docs/HARDWARE.md for full bilingual steps"

echo -e "\n${BOLD}Done.${NC} Re-run after installing camera/Hailo packages."
