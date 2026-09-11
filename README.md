# livestock-weight

Estimate livestock weight from a **fixed overhead camera** (not a physical scale). Edge runtime targets **Raspberry Pi 5 (8 GB) + Hailo-8 HAT (~26 TOPS) + Camera Module 3** mounted ~**3 m** above ground. Offline-first SQLite on the edge; weighing sessions and device health sync to **Google Cloud Firestore** when configured. Auth via **Firebase Auth**. Farmer-facing UI ships **pt-BR only** in v1.

> Early ML is placeholder/research. Visual weight needs species-specific calibration. **No fabricated accuracy claims.**

## Repository layout

| Path | Role |
|------|------|
| `docs/` | Product, architecture (Mermaid), hardware, data model, roadmap |
| `device/` | Python edge: capture, inference stubs, pipeline, calibration, health |
| `api/` | FastAPI companion: events, sessions, status, Firestore sync stubs |
| `apps/web/` | React (Vite) UI — default locale **pt-BR** |
| `ml/` | Dataset conventions, train/eval placeholders, model card, HEF notes |
| `ops/` | docker-compose, seed + mock scripts, CI mirror |

## BOM (field device)

- Raspberry Pi 5, 8 GB RAM, ≥128 GB storage  
- Hailo-8 HAT (~26 TOPS — not PFLOPS)  
- Raspberry Pi Camera Module 3  
- Mount ~3.0 m AGL; outdoor enclosure as needed  

## Quickstart — laptop mock mode

No Pi, no Hailo, no cloud credentials required.

### 1) Device mock pipeline

```bash
cd /workspace/livestock-weight/device
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LW_CAMERA_BACKEND=mock LW_INFERENCE_BACKEND=cpu_mock
livestock-weight-device --steps 30
livestock-weight-health
pytest -q
```

Or: `ops/scripts/run_mock_pipeline.sh 30`

### 2) Companion API

```bash
cd /workspace/livestock-weight/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LW_API_DB_PATH=/tmp/livestock-weight.db
uvicorn livestock_weight_api.main:app --port 8000
# other terminal:
python /workspace/livestock-weight/ops/scripts/seed_demo_data.py
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/sync/run   # stub without credentials
```

### 3) Web UI (pt-BR)

```bash
cd /workspace/livestock-weight/apps/web
npm install
npm run dev
```

Open http://127.0.0.1:5173 — interface defaults to **português (Brasil)**. Optional `en` / `es` stubs exist for engineering only.

### Docker (api + web)

```bash
cd /workspace/livestock-weight/ops
docker compose up --build
```

## Pi bring-up (high level)

See `device/README.md` and `docs/HARDWARE.md`. Set `camera.height_m: 3.0`, use picamera2, optional Hailo HEF (documented in `ml/notes/hailo_hef_export.md`).

## Cloud (Firestore / Firebase)

- Edge SQLite + `sync_outbox` remain source of truth offline  
- `api` sync stubs push **weighing sessions** and **device health** when `GOOGLE_CLOUD_PROJECT` + credentials (or emulator) are set  
- **Never commit** service-account JSON or API keys  

## How pieces relate

```
Camera/Mock → device pipeline → WeightEvent → local API (SQLite)
                                              ↓
                                    Firestore sync stub (sessions + health)
                                              ↓
                                    apps/web (pt-BR) on LAN
```

Product name: **livestock-weight** (Vector Trends).
