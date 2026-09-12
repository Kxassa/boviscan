"""Firebase Auth verification for BoviScan companion API.

Disabled by default (FIREBASE_AUTH_ENABLED=false) so local mock E2E works
without credentials. When enabled, Bearer ID tokens are verified with
firebase-admin against project boviscan-c2430 (or FIREBASE_PROJECT_ID).

No secrets in-repo. Initialize with Application Default Credentials,
GOOGLE_APPLICATION_CREDENTIALS (path outside repo), or the Auth emulator.

Enable for project boviscan-c2430
---------------------------------
1. Firebase Console → Project settings → Service accounts → Generate key
   (store JSON outside the repo; never commit).
2. export GOOGLE_APPLICATION_CREDENTIALS=/path/outside/repo/sa.json
3. export FIREBASE_PROJECT_ID=boviscan-c2430
4. export GOOGLE_CLOUD_PROJECT=boviscan-c2430
5. export FIREBASE_AUTH_ENABLED=true
6. pip install -e '.[firestore]'   # pulls firebase-admin
7. Restart uvicorn

Auth emulator (optional):
  export FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
  # Web client: connectAuthEmulator(auth, "http://127.0.0.1:9099")
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)
_firebase_app: Any | None = None
_init_attempted = False
_init_error: str | None = None


def auth_status() -> dict[str, Any]:
    """Public, secret-free description of auth configuration."""
    return {
        "enabled": settings.firebase_auth_enabled,
        "project_id": (
            settings.firebase_project_id
            or os.environ.get("FIREBASE_PROJECT_ID")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or "boviscan-c2430"
        ),
        "emulator": bool(os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")),
        "firebase_admin_ready": _firebase_app is not None,
        "init_error": _init_error,
        "docs": (
            "Set FIREBASE_AUTH_ENABLED=true and install firebase-admin "
            "(pip install -e '.[firestore]'). Provide GOOGLE_APPLICATION_CREDENTIALS "
            "outside the repo, or FIREBASE_AUTH_EMULATOR_HOST for local Auth emulator. "
            "Project: boviscan-c2430. See docs/AUTH.md."
        ),
    }


def ensure_firebase_app() -> Any:
    """Lazily initialize firebase_admin once. Raises RuntimeError on failure."""
    global _firebase_app, _init_attempted, _init_error
    if _firebase_app is not None:
        return _firebase_app
    if _init_attempted and _init_error:
        raise RuntimeError(_init_error)
    _init_attempted = True
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as e:
        _init_error = "firebase-admin not installed; pip install -e '.[firestore]'"
        raise RuntimeError(_init_error) from e

    project = (
        settings.firebase_project_id
        or os.environ.get("FIREBASE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or "boviscan-c2430"
    )
    try:
        # Reuse existing default app if another module initialized it
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass

        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
            # Emulator accepts unsigned tokens; still need an app object
            _firebase_app = firebase_admin.initialize_app(options={"projectId": project})
        elif cred_path and os.path.isfile(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred, options={"projectId": project})
        else:
            # ADC / metadata server (Cloud Run, GCE) — no file required
            _firebase_app = firebase_admin.initialize_app(options={"projectId": project})
        logger.info("firebase_admin initialized for project=%s", project)
        return _firebase_app
    except Exception as e:
        _init_error = f"firebase_admin init failed: {e}"
        raise RuntimeError(_init_error) from e


async def optional_firebase_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    When FIREBASE_AUTH_ENABLED=true, require a Bearer ID token and verify it.
    When disabled, return None and allow anonymous local access.
    """
    if not settings.firebase_auth_enabled:
        return None
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        ensure_firebase_app()
        from firebase_admin import auth as fb_auth
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_firebase_user(
    user: dict | None = Depends(optional_firebase_user),
) -> dict | None:
    """Same as optional_firebase_user; named for routes that always depend on auth policy."""
    return user
