# Firestore production soak — boviscan-c2430

Engineer runbook for a **real** Firestore soak against Firebase / GCP project
**`boviscan-c2430`**. Never commit service-account JSON or tokens.

Offline-first remains the source of truth: local SQLite + `sync_outbox`.
Collections:

| Collection | Key | Purpose |
|------------|-----|---------|
| `weighing_sessions` | session id | Session documents from companion API outbox |
| `device_health` | device_id | Device heartbeat / health snapshots |

---

## 1. Create a service account

1. Open Google Cloud Console → project **`boviscan-c2430`**
   (or Firebase console → Project settings → Service accounts).
2. Create SA, e.g. `boviscan-firestore-soak@boviscan-c2430.iam.gserviceaccount.com`.
3. Grant **least privilege** roles (start narrow; widen only if needed):
   - `roles/datastore.user` (Cloud Datastore User) — read/write Firestore
   - Optionally `roles/firebase.viewer` if you need console-aligned metadata
4. Create a JSON key **outside the repo**, e.g.
   `/etc/boviscan/sa-firestore-soak.json` or `~/secrets/boviscan-sa.json`.
5. Restrict key filesystem perms: `chmod 600` that file.
6. Confirm Firestore is enabled in the project (Native mode).

---

## 2. Set credentials on the API host

```bash
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
export FIREBASE_PROJECT_ID=boviscan-c2430
export GOOGLE_APPLICATION_CREDENTIALS=/path/outside/repo/sa-firestore-soak.json
# Do NOT set FIRESTORE_EMULATOR_HOST for production soak
unset FIRESTORE_EMULATOR_HOST

cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[firestore,dev]'
export LW_API_DB_PATH=/tmp/boviscan-soak.db
uvicorn livestock_weight_api.main:app --port 8000
```

Optional Auth (separate from sync SA): see `docs/AUTH.md`.

---

## 3. Enable sync and verify collections

```bash
# Status should show mode transitioning toward firestore when creds + lib present
curl -s http://127.0.0.1:8000/sync/status | jq .

# Dry-run first (no writes)
curl -s -X POST 'http://127.0.0.1:8000/sync/run?dry_run=true' | jq .

# Seed a session + health via API, then real sync
curl -s -X POST http://127.0.0.1:8000/sessions/start \
  -H 'content-type: application/json' \
  -d '{"device_id":"soak-device-01","notes":"firestore soak"}' | jq .
curl -s -X PUT http://127.0.0.1:8000/status \
  -H 'content-type: application/json' \
  -d '{"device_id":"soak-device-01","online":true,"camera_ok":true,"inference_backend":"cpu_mock","pipeline_state":"soak","version":"0.1.0"}' | jq .

curl -s -X POST 'http://127.0.0.1:8000/sync/run' | jq .
```

In Firebase / GCP console, confirm documents under:

- `weighing_sessions/{sessionId}`
- `device_health/soak-device-01`

Helper script (dry-run by default):

```bash
python ops/scripts/firestore_soak_check.py
# Optional single test write when credentials present:
python ops/scripts/firestore_soak_check.py --write
```

---

## 4. Soak duration suggestions

- Short: 1 test doc + one session sync (this runbook).
- Medium: run `./ops/scripts/run_demo.sh` with API posting, then `/sync/run` every 1–5 min for 30–60 min; watch outbox drain and error rates.
- Do not log credential paths into shared tickets; redact SA emails if needed.

---

## 5. Rollback / disable

1. Stop sync traffic: do not call `POST /sync/run`; leave outbox unpushed (safe).
2. Unset credentials and restart API:
   ```bash
   unset GOOGLE_APPLICATION_CREDENTIALS
   # optional: unset GOOGLE_CLOUD_PROJECT
   ```
   Sync mode returns to **`disabled`**; local SQLite keeps data.
3. Delete soak documents in console if desired:
   - `weighing_sessions` docs with notes `firestore soak` / device `soak-device-01`
   - `device_health/soak-device-01`
4. Disable or delete the soak SA key in IAM; rotate if the key was exposed.
5. Emulator-only work: set `FIRESTORE_EMULATOR_HOST=127.0.0.1:8080` instead of production credentials (`ops/docker-compose.yml` profile `emulator`).

---

## Safety

- No secrets in git (see `.gitignore`: `GOOGLE_APPLICATION_CREDENTIALS*`, `*-service-account*.json`).
- Prefer emulator for CI; production soak is **manual / field**.
- pt-BR farmer UI unchanged by this runbook.
