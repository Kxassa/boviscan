# BoviScan

**BoviScan** estimates livestock weight from a **fixed overhead camera** (not a physical scale). Edge runtime targets **Raspberry Pi 5 (8 GB) + Hailo-8 HAT (~26 TOPS) + Camera Module 3** mounted ~**3 m** above ground. Offline-first SQLite on the edge; weighing sessions and device health sync to **Google Cloud Firestore** (Firebase project **`boviscan-c2430`**) when configured. Auth via **Firebase Auth**. Farmer-facing UI ships **pt-BR only** in v1.

> Early ML is placeholder/research. Visual weight uses a **cattle height/area → kg heuristic table** labeled as a research proxy. **No fabricated accuracy claims.**

Repo / package path may still say `livestock-weight`; the product name is **BoviScan**.

## Repository layout

| Path | Role |
|------|------|
| `docs/` | Product, architecture (Mermaid), hardware, data model, roadmap |
| `device/` | Python edge: capture, inference stubs, pipeline, calibration, health |
| `api/` | FastAPI companion: events, sessions (start/stop/CSV), status, Firestore sync |
| `apps/web/` | React (Vite) UI — default locale **pt-BR** (console + calibração) |
| `ml/` | Dataset conventions, train/eval placeholders, model card, HEF notes |
| `ops/` | docker-compose, seed + **run_demo.sh**, CI mirror |

## BOM (field device)

- Raspberry Pi 5, 8 GB RAM, ≥128 GB storage  
- Hailo-8 HAT (~26 TOPS — not PFLOPS)  
- Raspberry Pi Camera Module 3  
- Mount ~3.0 m AGL; outdoor enclosure as needed  

## Quickstart — mock E2E demo

No Pi, no Hailo, no cloud credentials required.

```bash
cd /workspace/livestock-weight
./ops/scripts/run_demo.sh 40
```

This starts the companion API, creates a weighing session, runs the mock device pipeline (POST weight events), prints sample events / sync mode, and leaves the API up. In another terminal:

```bash
cd apps/web && npm install && npm run dev
# Open http://127.0.0.1:5173 — console de pesagem + checklist de calibração (pt-BR)
```

### Manual pieces

**Device mock pipeline (post to API):**

```bash
cd device
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LW_CAMERA_BACKEND=mock LW_INFERENCE_BACKEND=cpu_mock
export LW_API_BASE_URL=http://127.0.0.1:8000 LW_POST_API=true
livestock-weight-device --steps 30 --post-api --start-session
pytest -q
```

**Companion API:**

```bash
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export LW_API_DB_PATH=/tmp/boviscan.db
export GOOGLE_CLOUD_PROJECT=boviscan-c2430 FIREBASE_PROJECT_ID=boviscan-c2430
uvicorn livestock_weight_api.main:app --port 8000
# POST /sessions/start | GET /sessions/{id}/export.csv | POST /sync/run
```

**Firestore emulator (optional):**

```bash
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
pip install -e ".[firestore]"
# then POST /sync/run → mode=firestore against emulator
```

Never commit `GOOGLE_APPLICATION_CREDENTIALS` JSON.

## Pi bring-up (high level)

See `device/README.md` and `docs/HARDWARE.md`. Set `camera.height_m: 3.0`, use picamera2, optional Hailo HEF (documented in `ml/notes/hailo_hef_export.md`).

## How pieces relate

```
Camera/Mock → detect → track IDs → cattle research proxy (kg)
                                 → WeightEvent POST → companion API (SQLite)
                                                      ↓ outbox retry
                                              Firestore (boviscan-c2430) when configured
                                                      ↓
                                              apps/web BoviScan (pt-BR)
```

## Product

**BoviScan** — Vector Trends — Firebase `boviscan-c2430`.
