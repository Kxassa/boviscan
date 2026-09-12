# Firebase Auth — BoviScan (`boviscan-c2430`)

Auth is **optional**. Default: `FIREBASE_AUTH_ENABLED=false` so mock E2E works offline.

## Enable on the companion API

1. Firebase Console → project **boviscan-c2430** → Project settings → Service accounts → Generate new private key.  
   Store the JSON **outside the repo** (never commit).
2. Environment:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/outside/repo/sa.json
export FIREBASE_PROJECT_ID=boviscan-c2430
export GOOGLE_CLOUD_PROJECT=boviscan-c2430
export FIREBASE_AUTH_ENABLED=true
cd api && pip install -e '.[firestore]'
uvicorn livestock_weight_api.main:app --port 8000
```

3. Check: `GET /auth/status` → `enabled: true`. Write routes require `Authorization: Bearer <ID_TOKEN>`.

### Auth emulator

```bash
# Firebase CLI / gcloud Auth emulator on 9099
export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
export FIREBASE_AUTH_ENABLED=true
export FIREBASE_PROJECT_ID=boviscan-c2430
```

## Enable on the web console (pt-BR login)

1. Firebase Console → Authentication → enable **Email/Password** (and optionally Google).
2. Web app config (Project settings → Your apps). Put values in `apps/web/.env.local` (gitignored via `.env`):

```bash
VITE_FIREBASE_AUTH_ENABLED=true
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=boviscan-c2430.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=boviscan-c2430
VITE_FIREBASE_APP_ID=...
# Optional Google popup (otherwise button is clearly stubbed):
# VITE_FIREBASE_GOOGLE_ENABLED=true
```

3. `npm run dev` — login screen appears; API calls attach `Bearer` when a session exists.
4. When `VITE_FIREBASE_AUTH_ENABLED` is false (default), UI behaves as before (no login gate).

Google Sign-In stays **stubbed** until `VITE_FIREBASE_GOOGLE_ENABLED=true` and the Google provider is configured in Firebase Console.
