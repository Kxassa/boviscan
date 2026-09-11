from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..firestore_sync import run_sync
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
        message=report.message,
    )
