from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..firestore_sync import run_sync, sync_mode, _project_id
from ..models import SyncResult

router = APIRouter(prefix="/sync", tags=["sync"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.post("/run", response_model=SyncResult)
def sync_run(conn: sqlite3.Connection = Depends(get_db)) -> SyncResult:
    report = run_sync(conn)
    return SyncResult(
        ok=report.ok,
        mode=report.mode,
        pushed_sessions=report.pushed_sessions,
        pushed_health=report.pushed_health,
        retried=report.retried,
        failed=report.failed,
        message=report.message,
    )


@router.get("/status")
def sync_status() -> dict:
    """Describe current sync configuration (no secrets)."""
    return {
        "mode": sync_mode(),
        "project_id": _project_id() or "boviscan-c2430 (default example)",
        "emulator": bool(__import__("os").environ.get("FIRESTORE_EMULATOR_HOST")),
        "docs": (
            "Set GOOGLE_CLOUD_PROJECT=boviscan-c2430 and either "
            "GOOGLE_APPLICATION_CREDENTIALS or FIRESTORE_EMULATOR_HOST. "
            "Install optional extra: pip install -e '.[firestore]'."
        ),
    }
