from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from ..auth import optional_firebase_user
from ..firestore_sync import run_sync, status_snapshot
from ..models import SyncResult

router = APIRouter(prefix="/sync", tags=["sync"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.post("/run", response_model=SyncResult)
def sync_run(
    conn: sqlite3.Connection = Depends(get_db),
    dry_run: bool = Query(False, description="Report pending without writing"),
    _user: dict | None = Depends(optional_firebase_user),
) -> SyncResult:
    report = run_sync(conn, dry_run=dry_run)
    return SyncResult(
        ok=report.ok,
        mode=report.mode,
        pushed_sessions=report.pushed_sessions,
        pushed_health=report.pushed_health,
        retried=report.retried,
        failed=report.failed,
        message=report.message,
        pending=report.pending,
        collections=report.collections,
    )


@router.get("/status")
def sync_status(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Describe current sync configuration + outbox (no secrets)."""
    return status_snapshot(conn)
