"""LAN device registry: UDP beacon ingest + list known devices with health snippet."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import optional_firebase_user

router = APIRouter(prefix="/devices", tags=["devices"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


class DeviceRegisterIn(BaseModel):
    device_id: str
    display_name: str | None = None
    host: str | None = None
    port: int | None = None
    api_base: str | None = None
    version: str | None = None
    source: str = "manual"  # manual | udp | mdns | mock | heartbeat
    health: dict = Field(default_factory=dict)
    online: bool = True


class DeviceOut(BaseModel):
    device_id: str
    display_name: str | None = None
    host: str | None = None
    port: int | None = None
    api_base: str | None = None
    version: str | None = None
    source: str = "manual"
    online: bool = True
    last_seen: str
    health: dict = Field(default_factory=dict)
    registered_at: str | None = None


def _row_to_out(r: sqlite3.Row) -> DeviceOut:
    health: dict = {}
    try:
        health = json.loads(r["health_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        health = {}
    return DeviceOut(
        device_id=r["device_id"],
        display_name=r["display_name"],
        host=r["host"],
        port=r["port"],
        api_base=r["api_base"],
        version=r["version"],
        source=r["source"] or "manual",
        online=bool(r["online"]),
        last_seen=r["last_seen"],
        health=health,
        registered_at=r["registered_at"],
    )


def upsert_device(conn: sqlite3.Connection, body: DeviceRegisterIn) -> DeviceOut:
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT * FROM devices WHERE device_id=?", (body.device_id,)
    ).fetchone()
    health_json = json.dumps(body.health or {})
    if existing:
        conn.execute(
            """
            UPDATE devices SET
              display_name=COALESCE(?, display_name),
              host=COALESCE(?, host),
              port=COALESCE(?, port),
              api_base=COALESCE(?, api_base),
              version=COALESCE(?, version),
              source=?,
              online=?,
              last_seen=?,
              health_json=?
            WHERE device_id=?
            """,
            (
                body.display_name,
                body.host,
                body.port,
                body.api_base,
                body.version,
                body.source,
                int(body.online),
                now,
                health_json,
                body.device_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO devices (
              device_id, display_name, host, port, api_base, version,
              source, online, last_seen, health_json, registered_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                body.device_id,
                body.display_name or body.device_id,
                body.host,
                body.port,
                body.api_base,
                body.version,
                body.source,
                int(body.online),
                now,
                health_json,
                now,
            ),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM devices WHERE device_id=?", (body.device_id,)
    ).fetchone()
    return _row_to_out(row)


def register_mock_local_device(conn: sqlite3.Connection) -> DeviceOut:
    """Called on API start in mock mode and by demo script."""
    return upsert_device(
        conn,
        DeviceRegisterIn(
            device_id="device-local-01",
            display_name="BoviScan local (mock)",
            host="127.0.0.1",
            port=8000,
            api_base="http://127.0.0.1:8000",
            version="0.1.0",
            source="mock",
            online=True,
            health={
                "camera_ok": True,
                "inference_backend": "cpu_mock",
                "pipeline_state": "idle",
                "note": "auto-registered mock device",
            },
        ),
    )


@router.get("", response_model=list[DeviceOut])
def list_devices(
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> list[DeviceOut]:
    rows = conn.execute(
        "SELECT * FROM devices ORDER BY last_seen DESC"
    ).fetchall()
    # Merge health snippet from device_status when present
    out: list[DeviceOut] = []
    for r in rows:
        d = _row_to_out(r)
        st = conn.execute(
            "SELECT * FROM device_status WHERE device_id=?", (d.device_id,)
        ).fetchone()
        if st:
            snippet = {
                **d.health,
                "camera_ok": bool(st["camera_ok"]),
                "inference_backend": st["inference_backend"],
                "pipeline_state": st["pipeline_state"],
                "cpu_temp_c": st["cpu_temp_c"],
                "disk_free_gb": st["disk_free_gb"],
                "last_heartbeat": st["last_heartbeat"],
            }
            d = d.model_copy(
                update={
                    "health": snippet,
                    "version": d.version or st["version"],
                    "online": bool(st["online"]),
                }
            )
        out.append(d)
    return out


@router.post("/register", response_model=DeviceOut)
def register_device(
    body: DeviceRegisterIn,
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> DeviceOut:
    return upsert_device(conn, body)


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> DeviceOut:
    row = conn.execute(
        "SELECT * FROM devices WHERE device_id=?", (device_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="device not found")
    return _row_to_out(row)


@router.post("/beacon", response_model=DeviceOut)
def ingest_beacon(
    body: DeviceRegisterIn,
    conn: sqlite3.Connection = Depends(get_db),
) -> DeviceOut:
    """HTTP fallback for UDP beacon payload (same schema)."""
    body.source = body.source or "udp"
    return upsert_device(conn, body)
