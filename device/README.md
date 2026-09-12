# device — BoviScan edge runtime

Python package: Camera Module 3 capture (picamera2) + MockCamera, Hailo production backend (HEF + SDK with cpu_mock fallback) + CPU/mock inference, multi-track IoU tracker, **cattle research weight proxy** (area/height table), health checks, soak harness.

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
6. Optional: `inference.backend: hailo` + `hef_path` when HEF + HailoRT are installed (clear fallback to cpu_mock otherwise)
7. Install `systemd/livestock-weight-device.service` and start the unit

## Weight proxy

`calibration/cattle_proxy.py` loads `config/cattle_proxy.yaml` (or `ml/calibration/cattle_proxy.yaml`). Marked **research_proxy**; not for trade settlement.

## Interfaces

| Concern | Interface | Mocks |
|---------|-----------|-------|
| Capture | `Camera` | `MockCamera` |
| Inference | `InferenceBackend` | `MockBackend`, `CPUMockBackend`, `HailoBackend` (SDK/HEF or fallback) |
| Tracking | `SimpleTracker` | IoU IDs across frames |
| Geometry | `Calibration` | defaults at 3.0 m + cattle table |

Farmer-facing copy for install UIs lives in the web app (**pt-BR** for v1).

## Soak / Hailo

```bash
python scripts/soak.py --frames 100 --backend cpu_mock --out /tmp/soak.json
pytest -q tests/test_hailo_backend.py
```

HEF checklist: `../ml/notes/hailo_hef_export.md`. Firestore soak: `../docs/FIRESTORE_SOAK.md`.


## Phase 4 — discovery + OTA stubs

- UDP beacon (default on): announces to LAN + `POST {api}/devices/beacon`. See `docs/DISCOVERY.md`.
- OTA: `livestock_weight_device.ota.check_for_update()` / `apply_update()` — safe no-ops without `LW_OTA_MANIFEST_URL`. See `docs/OTA.md`.
