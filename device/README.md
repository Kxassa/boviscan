# device — livestock-weight edge runtime

Python package: Camera Module 3 capture (picamera2) + MockCamera, Hailo stub + CPU/mock inference, pipeline, calibration (default height **3.0 m**), health checks.

## Laptop mock mode (no Pi / no Hailo)

```bash
cd device
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export LW_CAMERA_BACKEND=mock
export LW_INFERENCE_BACKEND=cpu_mock
livestock-weight-device --steps 30
livestock-weight-health
pytest -q
```

## Pi 5 bring-up (summary)

1. Raspberry Pi OS (64-bit), enable camera via `raspi-config` / libcamera
2. Install system deps for picamera2 as per Raspberry Pi docs
3. `pip install -e ".[pi,dev]"` inside a venv
4. Copy `config/device.example.yaml` → `/etc/livestock-weight/device.yaml`
5. Set `camera.backend: picamera2`, `camera.height_m: 3.0`
6. Optional: `inference.backend: hailo` when HEF + HailoRT are installed (stub falls back otherwise)
7. Install `systemd/livestock-weight-device.service` and start the unit

## Interfaces

| Concern | Interface | Mocks |
|---------|-----------|-------|
| Capture | `Camera` | `MockCamera` |
| Inference | `InferenceBackend` | `MockBackend`, `CPUMockBackend`, `HailoBackend` stub |
| Geometry | `Calibration` | defaults at 3.0 m height |

Farmer-facing copy for install UIs lives in the web app (**pt-BR** for v1).
