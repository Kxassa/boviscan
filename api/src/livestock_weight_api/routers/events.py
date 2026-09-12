from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request

from ..auth import optional_firebase_user
from ..firestore_sync import enqueue
from ..models import WeightEventIn, WeightEventOut

router = APIRouter(prefix="/events", tags=["events"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.post("", response_model=WeightEventOut)
def create_event(
    body: WeightEventIn,
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> WeightEventOut:
    session_id = body.session_id
    if session_id is None:
        session_id = str(uuid4())
        conn.execute(
            "INSERT OR IGNORE INTO weighing_sessions "
            "(id, device_id, started_at, event_count, sync_state, status) "
            "VALUES (?, ?, ?, 0, 'pending', 'active')",
            (session_id, body.device_id, body.timestamp),
        )
    else:
        # Ensure session row exists when device supplies session_id
        conn.execute(
            "INSERT OR IGNORE INTO weighing_sessions "
            "(id, device_id, started_at, event_count, sync_state, status) "
            "VALUES (?, ?, ?, 0, 'pending', 'active')",
            (session_id, body.device_id, body.timestamp),
        )
    conn.execute(
        "INSERT OR REPLACE INTO weight_events "
        "(id, device_id, track_id, session_id, timestamp, species, estimated_weight_kg, "
        "confidence, proxy_metrics, calibration_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            body.id,
            body.device_id,
            body.track_id,
            session_id,
            body.timestamp,
            body.species,
            body.estimated_weight_kg,
            body.confidence,
            json.dumps(body.proxy_metrics),
            body.calibration_id,
        ),
    )
    conn.execute(
        "UPDATE weighing_sessions SET event_count = event_count + 1 WHERE id=?",
        (session_id,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if row:
        enqueue(
            conn,
            "weighing_session",
            session_id,
            {
                "id": row["id"],
                "device_id": row["device_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "event_count": row["event_count"],
                "notes": row["notes"],
                "status": row["status"] if "status" in row.keys() else "active",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    data = body.model_dump()
    data["session_id"] = session_id
    data["synced_at"] = None
    return WeightEventOut(**data)


@router.get("", response_model=list[WeightEventOut])
def list_events(
    conn: sqlite3.Connection = Depends(get_db),
    device_id: str | None = None,
    session_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[WeightEventOut]:
    q = "SELECT * FROM weight_events WHERE 1=1"
    args: list = []
    if device_id:
        q += " AND device_id=?"
        args.append(device_id)
    if session_id:
        q += " AND session_id=?"
        args.append(session_id)
    q += " ORDER BY timestamp DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(q, args).fetchall()
    out: list[WeightEventOut] = []
    for r in rows:
        out.append(
            WeightEventOut(
                id=r["id"],
                device_id=r["device_id"],
                track_id=r["track_id"],
                timestamp=r["timestamp"],
                species=r["species"],
                estimated_weight_kg=r["estimated_weight_kg"],
                confidence=r["confidence"],
                proxy_metrics=json.loads(r["proxy_metrics"] or "{}"),
                calibration_id=r["calibration_id"],
                session_id=r["session_id"],
                synced_at=r["synced_at"],
            )
        )
    return out
