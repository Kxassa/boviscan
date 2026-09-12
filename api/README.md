# api — BoviScan companion

FastAPI + SQLite for weight events, weighing sessions (start/stop/list/get/CSV), and device status. Firestore sync: **disabled / stub / firestore** with per-write backoff. Optional Firebase Auth (`docs/AUTH.md`).

## Run locally

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export LW_API_DB_PATH=/tmp/boviscan.db
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
export FIREBASE_PROJECT_ID=boviscan-c2430
uvicorn livestock_weight_api.main:app --reload --port 8000
```

OpenAPI: http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Includes `auth_enabled`, `sync_mode` |
| GET | `/auth/status` | Firebase Auth config (no secrets) |
| POST | `/events` | Ingest weight event |
| GET | `/events` | List; filter `session_id`, `device_id` |
| POST | `/sessions/start` | Start weighing session |
| POST | `/sessions/{id}/stop` | Stop session |
| GET | `/sessions` | List |
| GET | `/sessions/{id}` | Get |
| GET | `/sessions/{id}/export.csv` | CSV export |
| PUT/GET | `/status` | Device heartbeat |
| POST | `/sync/run` | Drain outbox (`?dry_run=true` supported) |
| GET | `/sync/status` | Mode, collections, pending, errors |
| POST | `/bridge/lis/estimated-weight` | LIS visual-weight bridge (stub/queue) |

When `FIREBASE_AUTH_ENABLED=true`, mutating routes require `Authorization: Bearer <Firebase ID token>`.

## Env (no secrets committed)

| Variable | Purpose |
|----------|---------|
| `LW_API_DB_PATH` | SQLite path |
| `FIREBASE_AUTH_ENABLED` | Require ID tokens (default `false`) |
| `GOOGLE_CLOUD_PROJECT` / `FIREBASE_PROJECT_ID` | `boviscan-c2430` |
| `FIRESTORE_EMULATOR_HOST` | e.g. `127.0.0.1:8080` |
| `FIREBASE_AUTH_EMULATOR_HOST` | e.g. `127.0.0.1:9099` |
| `GOOGLE_APPLICATION_CREDENTIALS` | SA JSON **outside repo** |
| `LIS_INGEST_URL` | LIS base URL (optional; unset = stub) |
| `LIS_DEVICE_TOKEN` / `LIS_INGEST_TOKEN` | `X-Device-Token` for LIS ingest |

### Firestore collections

- `weighing_sessions`
- `device_health`

### Emulator

```bash
docker compose -f ../ops/docker-compose.yml --profile emulator up firestore-emulator
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
pip install -e '.[firestore]'
curl -X POST 'http://127.0.0.1:8000/sync/run'
curl -X POST 'http://127.0.0.1:8000/sync/run?dry_run=true'
```


## Phase 4 endpoints

- `GET /reports/farm` — farm summary (date_from, date_to, species) avg/min/max kg + count
- `GET /reports/farm/export.csv` — downloadable CSV with research disclaimer
- `GET /devices` — LAN registry (last_seen, health); mock auto-registers `device-local-01`
- `POST /devices/register` · `POST /devices/beacon`


## LIS bridge (stub)

See **`docs/INTEGRATION_LIS.md`**.

| Method | Path | Notes |
|--------|------|-------|
| POST | `/bridge/lis/estimated-weight` | Validate + queue; outbound stub or `POST {LIS}/api/boviscan/weight-events` |

Env: `LIS_INGEST_URL` (LIS base URL), `LIS_DEVICE_TOKEN` (or `LIS_INGEST_TOKEN`). Header to LIS: `X-Device-Token`. `metodo` forced to `estimativa_visual`.
