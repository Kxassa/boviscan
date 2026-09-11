from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from ..firestore_sync import enqueue
from ..models import DeviceStatusIn, DeviceStatusOut

router = APIRouter(prefix="/status", tags=["status"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.put("", response_model=DeviceStatusOut)
def put_status(body: DeviceStatusIn, conn: sqlite3.Connection = Depends(get_db)) -> DeviceStatusOut:
    conn.execute(
        "INSERT OR REPLACE INTO device_status "
        "(device_id, online, camera_ok, inference_backend, pipeline_state, "
        "cpu_temp_c, disk_free_gb, last_heartbeat, version) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            body.device_id,
            int(body.online),
            int(body.camera_ok),
            body.inference_backend,
            body.pipeline_state,
            body.cpu_temp_c,
            body.disk_free_gb,
            body.last_heartbeat,
            body.version,
        ),
    )
    payload = body.model_dump()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    enqueue(conn, "device_health", body.device_id, payload)
    return DeviceStatusOut(**body.model_dump(), synced_at=None)


@router.get("", response_model=list[DeviceStatusOut])
def get_status(conn: sqlite3.Connection = Depends(get_db)) -> list[DeviceStatusOut]:
    rows = conn.execute("SELECT * FROM device_status").fetchall()
    return [
        DeviceStatusOut(
            device_id=r["device_id"],
            online=bool(r["online"]),
            camera_ok=bool(r["camera_ok"]),
            inference_backend=r["inference_backend"],
            pipeline_state=r["pipeline_state"],
            cpu_temp_c=r["cpu_temp_c"],
            disk_free_gb=r["disk_free_gb"],
            last_heartbeat=r["last_heartbeat"],
            version=r["version"],
            synced_at=r["synced_at"],
        )
        for r in rows
    ]
