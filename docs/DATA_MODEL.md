# Data model: livestock-weight

## Edge (SQLite) — source of truth while offline

### WeightEvent

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID / string | Unique event id |
| `device_id` | string | Field device identifier |
| `track_id` | string | Tracker id for this passage |
| `session_id` | string \| null | Weighing session grouping |
| `timestamp` | ISO-8601 UTC | Event time |
| `species` | string | e.g. `cattle`, `pig`, `unknown` |
| `estimated_weight_kg` | float \| null | Calibrated estimate; null if uncalibrated |
| `confidence` | float 0–1 | Model/proxy confidence (not accuracy claim) |
| `proxy_metrics` | JSON | e.g. `area_px`, `length_m`, `width_m` |
| `calibration_id` | string \| null | Calibration profile used |
| `synced_at` | ISO-8601 \| null | When pushed to Firestore |

### WeighingSession

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Session id |
| `device_id` | string | Source device |
| `started_at` / `ended_at` | ISO-8601 | Bounds |
| `event_count` | int | Aggregated |
| `notes` | string \| null | Optional |
| `sync_state` | string | `pending` \| `synced` \| `error` |

### DeviceStatus / DeviceHealth

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | Device id |
| `online` | bool | Last heartbeat fresh |
| `camera_ok` | bool | Capture healthy |
| `inference_backend` | string | `hailo` \| `cpu_mock` \| `mock` |
| `pipeline_state` | string | `idle` \| `running` \| `error` |
| `cpu_temp_c` | float \| null | If available |
| `disk_free_gb` | float \| null | Storage headroom |
| `last_heartbeat` | ISO-8601 UTC | Last status update |
| `version` | string | Device software version |
| `synced_at` | ISO-8601 \| null | Last successful cloud sync |

### CalibrationProfile

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Profile id |
| `species` | string | Target species |
| `camera_height_m` | float | Default 3.0 |
| `fov_horizontal_deg` | float | Horizontal FOV |
| `ground_plane` | JSON | Homography / scale params |
| `reference_object` | JSON | Known size object used |
| `curve` | JSON | Placeholder mapping proxy → kg |

### SyncOutbox

Queue rows for eventual Firestore upload:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Outbox id |
| `entity_type` | string | `weighing_session` \| `device_health` \| `weight_event` |
| `entity_id` | string | Local entity id |
| `payload` | JSON | Snapshot to sync |
| `attempts` | int | Retry count |
| `last_error` | string \| null | Last failure message |
| `created_at` | ISO-8601 | Enqueued time |

## Cloud (Firestore) — synced projections

Collections (conventional names; project configured via env):

| Collection | Documents | Notes |
|------------|-----------|-------|
| `weighing_sessions` | Session aggregates + event summaries | Synced from edge outbox |
| `device_health` | Latest health per `device_id` | Heartbeat / status |
| `weight_events` (optional) | Individual events | May stay edge-only in early phases |

Document shapes mirror edge entities; add `farm_id` / `owner_uid` when Auth is wired.

## Auth (Firebase Auth)

- Companion web and API-facing clients authenticate with Firebase Auth (ID tokens)
- API verifies tokens when `FIREBASE_AUTH_ENABLED=true`; local mock mode skips Auth
- No API keys or service-account material in the repository

## Local API surface (summary)

- `POST /events` — ingest weight events (enqueues sync outbox)
- `GET /events` — history
- `GET /sessions` — weighing sessions
- `GET /status` / `PUT /status` — device health
- `POST /sync/run` — trigger sync stub (no-op without credentials)
- OpenAPI from FastAPI typed models

## Storage summary

- **Edge:** SQLite + outbox (`api/migrations/`)
- **Cloud:** Firestore (Google Cloud / Firebase)
- Credentials: environment variables only (see `api` sync module docstrings)
