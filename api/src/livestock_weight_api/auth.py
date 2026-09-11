"""Firebase Auth verification hooks (disabled by default for local mock)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import settings

_bearer = HTTPBearer(auto_error=False)


async def optional_firebase_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    When FIREBASE_AUTH_ENABLED=true, require a Bearer ID token and verify
    via firebase_admin (must be initialized by the deployer — no keys in-repo).
    """
    if not settings.firebase_auth_enabled:
        return None
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        from firebase_admin import auth as fb_auth  # type: ignore
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="firebase-admin not installed",
        ) from e
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase ID token"
        ) from e
