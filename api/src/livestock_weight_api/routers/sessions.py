from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from ..auth import optional_firebase_user
from ..firestore_sync import enqueue
from ..models import SessionStartIn, SessionStopIn, WeighingSessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


def _row_to_out(r: sqlite3.Row) -> WeighingSessionOut:
    status = "stopped" if r["ended_at"] else "active"
    # Prefer explicit status column if migration added it
    try:
        if r["status"]:
            status = r["status"]
    except (IndexError, KeyError):
        pass
    return WeighingSessionOut(
        id=r["id"],
        device_id=r["device_id"],
        started_at=r["started_at"],
        ended_at=r["ended_at"],
        event_count=r["event_count"],
        notes=r["notes"],
        sync_state=r["sync_state"],
        status=status,
    )


def _enqueue_session(conn: sqlite3.Connection, session_id: str) -> None:
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        return
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
            "status": _row_to_out(row).status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.post("/start", response_model=WeighingSessionOut)
def start_session(
    body: SessionStartIn,
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> WeighingSessionOut:
    sid = body.id or str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT id FROM weighing_sessions WHERE id=?", (sid,)).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="session already exists")
    conn.execute(
        "INSERT INTO weighing_sessions (id, device_id, started_at, event_count, notes, sync_state, status) "
        "VALUES (?, ?, ?, 0, ?, 'pending', 'active')",
        (sid, body.device_id, now, body.notes),
    )
    conn.commit()
    _enqueue_session(conn, sid)
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (sid,)).fetchone()
    return _row_to_out(row)


@router.post("/{session_id}/stop", response_model=WeighingSessionOut)
def stop_session(
    session_id: str,
    body: SessionStopIn | None = None,
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> WeighingSessionOut:
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    now = datetime.now(timezone.utc).isoformat()
    notes = (body.notes if body and body.notes is not None else row["notes"])
    conn.execute(
        "UPDATE weighing_sessions SET ended_at=?, status='stopped', notes=?, sync_state='pending' WHERE id=?",
        (now, notes, session_id),
    )
    conn.commit()
    _enqueue_session(conn, session_id)
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    return _row_to_out(row)


@router.get("", response_model=list[WeighingSessionOut])
def list_sessions(conn: sqlite3.Connection = Depends(get_db)) -> list[WeighingSessionOut]:
    rows = conn.execute(
        "SELECT * FROM weighing_sessions ORDER BY started_at DESC LIMIT 100"
    ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/{session_id}", response_model=WeighingSessionOut)
def get_session(session_id: str, conn: sqlite3.Connection = Depends(get_db)) -> WeighingSessionOut:
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    return _row_to_out(row)


@router.get("/{session_id}/events")
def session_events(session_id: str, conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    row = conn.execute("SELECT id FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    rows = conn.execute(
        "SELECT * FROM weight_events WHERE session_id=? ORDER BY timestamp ASC",
        (session_id,),
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "device_id": r["device_id"],
                "track_id": r["track_id"],
                "timestamp": r["timestamp"],
                "species": r["species"],
                "estimated_weight_kg": r["estimated_weight_kg"],
                "confidence": r["confidence"],
                "proxy_metrics": json.loads(r["proxy_metrics"] or "{}"),
                "calibration_id": r["calibration_id"],
                "session_id": r["session_id"],
            }
        )
    return out


@router.get("/{session_id}/export.csv")
def export_session_csv(session_id: str, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    row = conn.execute("SELECT * FROM weighing_sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    events = conn.execute(
        "SELECT * FROM weight_events WHERE session_id=? ORDER BY timestamp ASC",
        (session_id,),
    ).fetchall()
    weights = [e["estimated_weight_kg"] for e in events if e["estimated_weight_kg"] is not None]
    avg_kg = (sum(weights) / len(weights)) if weights else None
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# BoviScan session export — research proxy weights"])
    writer.writerow(
        [
            "# disclaimer",
            "Estimativas visuais (proxy de pesquisa). Não use como peso certificado ou comercial.",
        ]
    )
    writer.writerow(
        [
            "# session",
            row["id"],
            row["device_id"],
            row["started_at"],
            row["ended_at"] or "",
            f"event_count={row['event_count']}",
            f"avg_kg={avg_kg if avg_kg is not None else ''}",
            f"min_kg={min(weights) if weights else ''}",
            f"max_kg={max(weights) if weights else ''}",
        ]
    )
    writer.writerow([])
    writer.writerow(
        [
            "event_id",
            "session_id",
            "device_id",
            "track_id",
            "timestamp",
            "species",
            "estimated_weight_kg",
            "confidence",
            "area_m2",
            "length_m",
            "width_m",
            "height_proxy_m",
            "research_proxy",
            "calibration_id",
            "notes",
        ]
    )
    for e in events:
        pm = json.loads(e["proxy_metrics"] or "{}")
        writer.writerow(
            [
                e["id"],
                e["session_id"],
                e["device_id"],
                e["track_id"],
                e["timestamp"],
                e["species"],
                e["estimated_weight_kg"],
                e["confidence"],
                pm.get("area_m2"),
                pm.get("length_m"),
                pm.get("width_m"),
                pm.get("height_m") or pm.get("height_proxy_m"),
                pm.get("research_proxy", True),
                e["calibration_id"],
                row["notes"] or "",
            ]
        )
    data = buf.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="boviscan-session-{session_id}.csv"'},
    )
