"""
Firestore sync stubs for weighing sessions + device health.

Offline-first: local SQLite / sync_outbox remain authoritative until a real
Google Cloud project and credentials are configured via environment variables.

Never invent or commit credentials. Expected env when enabling real sync:
  - GOOGLE_CLOUD_PROJECT (or alias FIREBASE_PROJECT_ID)
  - GOOGLE_APPLICATION_CREDENTIALS  (path to SA JSON outside the repo)
  - optional FIRESTORE_EMULATOR_HOST for local emulator

Firebase Auth is separate (see auth.py); this module only projects data.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


COLLECTIONS = {
    "weighing_sessions": "weighing_sessions",
    "device_health": "device_health",
}


@dataclass
class SyncReport:
    ok: bool
    mode: str  # disabled | stub | firestore
    pushed_sessions: int = 0
    pushed_health: int = 0
    message: str = ""


def _project_id() -> str | None:
    return os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("FIREBASE_PROJECT_ID")


def _credentials_configured() -> bool:
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return True
    return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")) and bool(_project_id())


def enqueue(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
) -> str:
    oid = str(uuid4())
    conn.execute(
        "INSERT INTO sync_outbox (id, entity_type, entity_id, payload) VALUES (?, ?, ?, ?)",
        (oid, entity_type, entity_id, json.dumps(payload)),
    )
    conn.commit()
    return oid


def _mark_synced(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    if entity_type == "weighing_session":
        conn.execute(
            "UPDATE weighing_sessions SET sync_state=? WHERE id=?",
            ("synced", entity_id),
        )
    elif entity_type == "device_health":
        conn.execute(
            "UPDATE device_status SET synced_at=? WHERE device_id=?",
            (now, entity_id),
        )
    conn.execute(
        "DELETE FROM sync_outbox WHERE entity_type=? AND entity_id=?",
        (entity_type, entity_id),
    )
    conn.commit()


def _try_firestore_client() -> Any | None:
    """Return a Firestore client or None. Import is optional."""
    if not _credentials_configured():
        return None
    try:
        from google.cloud import firestore  # type: ignore
    except ImportError:
        return None
    project = _project_id()
    return firestore.Client(project=project) if project else firestore.Client()


def run_sync(conn: sqlite3.Connection, *, dry_run: bool = False) -> SyncReport:
    """
    Drain sync_outbox for weighing_session and device_health.

    Without credentials: stub mode — reports pending counts, does not fake success.
    With credentials + library: attempts Firestore set() (best-effort).
    """
    rows = conn.execute(
        "SELECT id, entity_type, entity_id, payload FROM sync_outbox "
        "WHERE entity_type IN ('weighing_session', 'device_health') "
        "ORDER BY created_at ASC LIMIT 100"
    ).fetchall()

    if not rows:
        return SyncReport(ok=True, mode="stub", message="Outbox empty")

    client = None if dry_run else _try_firestore_client()
    if client is None:
        return SyncReport(
            ok=True,
            mode="disabled" if not _credentials_configured() else "stub",
            message=(
                f"{len(rows)} pending outbox item(s); "
                "Firestore client not active (missing credentials or google-cloud-firestore). "
                "Local SQLite remains source of truth."
            ),
            pushed_sessions=0,
            pushed_health=0,
        )

    sessions = health = 0
    for row in rows:
        payload = json.loads(row["payload"])
        coll = COLLECTIONS.get(
            "weighing_sessions" if row["entity_type"] == "weighing_session" else "device_health"
        )
        if row["entity_type"] == "weighing_session":
            client.collection(coll).document(row["entity_id"]).set(payload, merge=True)
            sessions += 1
        else:
            client.collection(coll).document(row["entity_id"]).set(payload, merge=True)
            health += 1
        _mark_synced(conn, row["entity_type"], row["entity_id"])

    return SyncReport(
        ok=True,
        mode="firestore",
        pushed_sessions=sessions,
        pushed_health=health,
        message="Synced to Firestore",
    )
