# BoviScan

**BoviScan** estimates livestock weight from a **fixed overhead camera** (not a physical scale). Edge runtime targets **Raspberry Pi 5 (8 GB) + Hailo-8 HAT (~26 TOPS) + Camera Module 3** mounted ~**3 m** above ground. Offline-first SQLite on the edge; weighing sessions and device health sync to **Google Cloud Firestore** (Firebase project **`boviscan-c2430`**) when configured. Auth via **Firebase Auth**. Farmer-facing UI ships **pt-BR only** in v1.

> Early ML is placeholder/research. Visual weight uses a **cattle height/area → kg heuristic table** (YAML-configurable) labeled as a research proxy. **No fabricated accuracy claims.**

Repo / package path may still say `livestock-weight`; the product name is **BoviScan**.

## Repository layout

| Path | Role |
|------|------|
| `docs/` | Product, architecture, hardware, AUTH, Firestore soak, discovery, OTA, data model, **LIS integration**, roadmap |
| `device/` | Python edge: capture, inference stubs, pipeline, calibration, health |
| `api/` | FastAPI companion: events, sessions, status, Firestore sync, optional Auth |
| `apps/web/` | React (Vite) UI — default locale **pt-BR** (console + calibração + login) |
| `ml/` | Datasets schema, cattle YAML curves, eval MAE, Hailo HEF export notes, model card |
| `ops/` | docker-compose (+ Firestore emulator profile), seed, **run_demo.sh**, **pre_pi_smoke.sh**, **pi_bringup.sh**, **soak_device.sh** |

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

```bash
cd apps/web && npm install && npm run dev
# Open http://127.0.0.1:5173 — console de pesagem + checklist (pt-BR)
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
```


## Pre-Pi smoke

Full software gate **before** Pi / Hailo hardware. No camera HAT or cloud credentials required.

```bash
./ops/scripts/pre_pi_smoke.sh
```

Runs: device + API pytest (Hailo fallback covered by device tests), non-interactive `run_demo.sh`, soak (`cpu_mock`), Firestore dry-run, capture smoke (mock), and `apps/web` install/build/test. Exits non-zero if any step fails; prints a summary table.

## Phase 2 — enable Auth + Firestore + Pi bring-up

### Firebase Auth (optional)

See **`docs/AUTH.md`**. Short version:

```bash
# API
export FIREBASE_AUTH_ENABLED=true
export FIREBASE_PROJECT_ID=boviscan-c2430
export GOOGLE_APPLICATION_CREDENTIALS=/path/outside/repo/sa.json
pip install -e '.[firestore]'   # from api/

# Web (apps/web/.env.local)
VITE_FIREBASE_AUTH_ENABLED=true
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=boviscan-c2430.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=boviscan-c2430
```

When auth is disabled (default), API and web work as in Phase 1. Google Sign-In is clearly stubbed until `VITE_FIREBASE_GOOGLE_ENABLED=true`.

### Firestore sync / emulator

Collections: **`weighing_sessions`**, **`device_health`**. Status: `GET /sync/status`. Dry-run: `POST /sync/run?dry_run=true`.

```bash
# Optional emulator via compose profile
docker compose -f ops/docker-compose.yml --profile emulator up firestore-emulator
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
cd api && pip install -e '.[firestore]'
curl -X POST 'http://127.0.0.1:8000/sync/run'
```

Never commit `GOOGLE_APPLICATION_CREDENTIALS` JSON.

### Pi 5 bring-up

```bash
./ops/scripts/pi_bringup.sh
python device/scripts/capture_smoke.py --out /tmp/boviscan-still.jpg
# Full steps: docs/HARDWARE.md
```

### Species calibration / eval

- Curves: `ml/calibration/cattle_proxy.yaml` (also `device/config/cattle_proxy.yaml`)
- Datasets: `ml/datasets/cattle|sheep|goat/` — CSV schema `image_id,scale_kg,bbox,date,farm_id`
- MAE: `python ml/eval/eval_proxy_mae.py ml/eval/sample_proxy_vs_scale.csv`

## Phase 3 — Hailo acceleration + soak prep

### Hailo backend

```bash
cd device && source .venv/bin/activate
# CI / laptop: selects hailo, falls back to cpu_mock with clear errors
export LW_INFERENCE_BACKEND=hailo
# optional: export LW_HEF_PATH=/opt/livestock-weight/models/detect.hef
pytest -q tests/test_hailo_backend.py
livestock-weight-device --steps 5   # uses config / env backend
```

Config knobs: `inference.hef_path`, `batch`, `input_size`, `postprocess`, `fallback_to_cpu`
(see `device/config/device.example.yaml`). HEF export checklist: `ml/notes/hailo_hef_export.md`.

### Soak harness (FPS / latency / temp)

```bash
./ops/scripts/soak_device.sh 100 cpu_mock
# or: python device/scripts/soak.py --frames 100 --backend hailo --out artifacts/soak.json
```

### Firestore production soak

See **`docs/FIRESTORE_SOAK.md`**. Dry-run:

```bash
python ops/scripts/firestore_soak_check.py
# with SA / emulator: python ops/scripts/firestore_soak_check.py --write
```


## Phase 4 — Product hardening

### Farm reports + CSV

```bash
# JSON summary (date range + species)
curl -s 'http://127.0.0.1:8000/reports/farm?date_from=2026-09-01&date_to=2026-09-12&species=cattle' | python3 -m json.tool
# Downloadable CSV
curl -OJ 'http://127.0.0.1:8000/reports/farm/export.csv?date_from=2026-09-01&date_to=2026-09-12'
```

Web (pt-BR): **Relatórios** — filter by date/species, summary cards (count / avg / min / max kg*), CSV download. Session CSV also includes disclaimer + session summary. Weights remain **research proxy**.

### Devices / LAN discovery

- Device UDP beacon (port **45454**) + HTTP `POST /devices/beacon`
- `GET /devices` — known devices, `last_seen`, health snippet
- Mock: API auto-registers `device-local-01` (`LW_MOCK_REGISTER_DEVICE=true`)
- Docs: `docs/DISCOVERY.md` (UDP implemented; mDNS documented)

Web: **Dispositivos** page.

### OTA (design + stubs)

- `docs/OTA.md` — signed manifest flow (ed25519 / sigstore-style), rollback
- Device: `check_for_update` / `apply_update` safe no-ops without `LW_OTA_MANIFEST_URL`
- Example schema: `ops/ota/manifest.schema.json`, `ops/ota/example-manifest.json` (no real keys)

## How pieces relate

```
Camera/Mock → detect (motion/blob|Hailo HEF / cpu fallback) → track → cattle YAML research proxy (kg)
                                                    → WeightEvent POST → companion API (SQLite)
                                                                         ↓ outbox + backoff
                                                                 Firestore (boviscan-c2430)
                                                                         ↓
                                                                 apps/web BoviScan (pt-BR)
```


## LIS integration (visual → registerWeighing)

BoviScan does **not** share Firebase with LIS. Visual estimates can be forwarded to LIS:

- Contract: **`docs/INTEGRATION_LIS.md`** (diagram, schema, Firebase boundaries, `X-Device-Token`)
- Companion stub: `POST /bridge/lis/estimated-weight` → outbound `POST {LIS_INGEST_URL}/api/boviscan/weight-events`
- Env: `LIS_INGEST_URL`, `LIS_DEVICE_TOKEN` (or `LIS_INGEST_TOKEN`); unset = local stub queue
- `animalId` optional (m-bio); unmatched animals are **LIS-side pending**
- `metodo` always `estimativa_visual`; real scale weight stays in LIS

## Product

**BoviScan** — Vector Trends — Firebase `boviscan-c2430`.
