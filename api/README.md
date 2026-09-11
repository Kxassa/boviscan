# api — BoviScan companion

FastAPI + SQLite for weight events, weighing sessions (start/stop/list/get/CSV), and device status. Firestore sync supports **disabled / stub / firestore** modes (no credentials in-repo). Firebase Auth can be enabled via env when configured.

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

## Endpoints (Phase 1)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/events` | Ingest weight event (research proxy fields OK) |
| GET | `/events` | List; filter `session_id`, `device_id` |
| POST | `/sessions/start` | Start weighing session |
| POST | `/sessions/{id}/stop` | Stop session |
| GET | `/sessions` | List |
| GET | `/sessions/{id}` | Get |
| GET | `/sessions/{id}/export.csv` | CSV export |
| PUT/GET | `/status` | Device heartbeat |
| POST | `/sync/run` | Drain outbox (retry with attempts) |
| GET | `/sync/status` | Mode + project hint (no secrets) |

## Env (no secrets committed)

| Variable | Purpose |
|----------|---------|
| `LW_API_DB_PATH` | SQLite path (default `./data/livestock-weight.db`) |
| `FIREBASE_AUTH_ENABLED` | `true` to require ID tokens (default `false` for mock) |
| `GOOGLE_CLOUD_PROJECT` | GCP project id (example/default: `boviscan-c2430`) |
| `FIREBASE_PROJECT_ID` | Alias (same: `boviscan-c2430`) |
| `FIRESTORE_EMULATOR_HOST` | e.g. `127.0.0.1:8080` |
| `GOOGLE_APPLICATION_CREDENTIALS` | SA JSON **outside repo** for real Firestore |

### Emulator

```bash
gcloud emulators:start --only firestore
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
pip install -e '.[firestore]'
curl -X POST http://127.0.0.1:8000/sync/run
```
