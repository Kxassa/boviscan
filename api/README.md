# api — livestock-weight companion

FastAPI + SQLite for weight events, sessions, and device status. Includes **Firestore sync stubs** (no credentials in-repo). Firebase Auth can be enabled via env when configured.

## Run locally

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export LW_API_DB_PATH=/tmp/livestock-weight.db
uvicorn livestock_weight_api.main:app --reload --port 8000
```

OpenAPI: http://127.0.0.1:8000/docs

## Env (no secrets committed)

| Variable | Purpose |
|----------|---------|
| `LW_API_DB_PATH` | SQLite path (default `./data/livestock-weight.db`) |
| `FIREBASE_AUTH_ENABLED` | `true` to require ID tokens (default `false` for mock) |
| `GOOGLE_CLOUD_PROJECT` | GCP project id for Firestore (default for this product: `boviscan-c2430`) |
| `FIREBASE_PROJECT_ID` | Optional alias for `GOOGLE_CLOUD_PROJECT` (same value: `boviscan-c2430`) |
| `FIRESTORE_EMULATOR_HOST` | Use emulator if set |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA JSON **outside repo** when using real Firestore |

Sync endpoint `POST /sync/run` is a safe stub without credentials.
