from __future__ import annotations

from fastapi import APIRouter

from ..auth import auth_status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def get_auth_status() -> dict:
    """Secret-free Firebase Auth configuration status."""
    return auth_status()
