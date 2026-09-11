from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..models import WeighingSessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.get("", response_model=list[WeighingSessionOut])
def list_sessions(conn: sqlite3.Connection = Depends(get_db)) -> list[WeighingSessionOut]:
    rows = conn.execute(
        "SELECT * FROM weighing_sessions ORDER BY started_at DESC LIMIT 100"
    ).fetchall()
    return [
        WeighingSessionOut(
            id=r["id"],
            device_id=r["device_id"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            event_count=r["event_count"],
            notes=r["notes"],
            sync_state=r["sync_state"],
        )
        for r in rows
    ]
