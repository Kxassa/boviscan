# device — BoviScan edge runtime

Python package: Camera Module 3 capture (picamera2) + MockCamera, Hailo stub + CPU/mock inference, multi-track IoU tracker, **cattle research weight proxy** (area/height table), health checks.

Default camera height **3.0 m**. Species default **cattle**.

## Laptop mock mode (no Pi / no Hailo)

```bash
cd device
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export LW_CAMERA_BACKEND=mock
export LW_INFERENCE_BACKEND=cpu_mock
livestock-weight-device --steps 30
# Post events to companion API:
export LW_API_BASE_URL=http://127.0.0.1:8000
livestock-weight-device --steps 40 --post-api --start-session
livestock-weight-health
pytest -q
```

Or use `../ops/scripts/run_demo.sh`.

## Pi 5 bring-up

Run `../ops/scripts/pi_bringup.sh` or `scripts/pi_bringup.sh`.
Capture smoke: `python scripts/capture_smoke.py --out /tmp/boviscan-still.jpg`.
Details: `docs/HARDWARE.md`.

## Pi 5 bring-up (summary)

1. Raspberry Pi OS (64-bit), enable camera via `raspi-config` / libcamera
2. Install system deps for picamera2 as per Raspberry Pi docs
3. `pip install -e ".[pi,dev]"` inside a venv
4. Copy `config/device.example.yaml` → `/etc/livestock-weight/device.yaml`
5. Set `camera.backend: picamera2`, `camera.height_m: 3.0`
6. Optional: `inference.backend: hailo` when HEF + HailoRT are installed (stub falls back otherwise)
7. Install `systemd/livestock-weight-device.service` and start the unit

## Weight proxy

`calibration/cattle_proxy.py` loads `config/cattle_proxy.yaml` (or `ml/calibration/cattle_proxy.yaml`). Marked **research_proxy**; not for trade settlement.

## Interfaces

| Concern | Interface | Mocks |
|---------|-----------|-------|
| Capture | `Camera` | `MockCamera` |
| Inference | `InferenceBackend` | `MockBackend`, `CPUMockBackend`, `HailoBackend` stub |
| Tracking | `SimpleTracker` | IoU IDs across frames |
| Geometry | `Calibration` | defaults at 3.0 m + cattle table |

Farmer-facing copy for install UIs lives in the web app (**pt-BR** for v1).
