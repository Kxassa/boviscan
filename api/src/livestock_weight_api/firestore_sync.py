"""
Firestore sync for weighing sessions + device health (BoviScan).

Modes:
  - disabled: no project/credentials/emulator → outbox retained, nothing pushed
  - stub: credentials flag set but client library missing / dry_run → report only
  - firestore: real google.cloud.firestore client (or emulator via FIRESTORE_EMULATOR_HOST)

Offline-first: local SQLite + sync_outbox remain authoritative.
Never invent or commit credentials.

Env:
  GOOGLE_CLOUD_PROJECT / FIREBASE_PROJECT_ID  (example: boviscan-c2430)
  GOOGLE_APPLICATION_CREDENTIALS             (SA JSON path outside repo)
  FIRESTORE_EMULATOR_HOST                    (e.g. 127.0.0.1:8080)

Emulator usage:
  1. gcloud emulators:start --only firestore
  2. export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
  3. export GOOGLE_CLOUD_PROJECT=boviscan-c2430
  4. pip install -e '.[firestore]' && POST /sync/run
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

MAX_ATTEMPTS = 5


@dataclass
class SyncReport:
    ok: bool
    mode: str  # disabled | stub | firestore
    pushed_sessions: int = 0
    pushed_health: int = 0
    retried: int = 0
    failed: int = 0
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
    # Replace prior pending outbox row for same entity to avoid duplicates
    conn.execute(
        "DELETE FROM sync_outbox WHERE entity_type=? AND entity_id=?",
        (entity_type, entity_id),
    )
    oid = str(uuid4())
    conn.execute(
        "INSERT INTO sync_outbox (id, entity_type, entity_id, payload, attempts) VALUES (?, ?, ?, ?, 0)",
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


def _bump_attempt(conn: sqlite3.Connection, outbox_id: str, error: str) -> None:
    conn.execute(
        "UPDATE sync_outbox SET attempts = attempts + 1, last_error=? WHERE id=?",
        (error[:500], outbox_id),
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
    project = _project_id() or "boviscan-c2430"
    return firestore.Client(project=project)


def sync_mode() -> str:
    if not _credentials_configured():
        return "disabled"
    try:
        from google.cloud import firestore  # noqa: F401
    except ImportError:
        return "stub"
    return "firestore"


def run_sync(conn: sqlite3.Connection, *, dry_run: bool = False) -> SyncReport:
    """
    Drain sync_outbox for weighing_session and device_health with retry accounting.

    Without credentials: mode=disabled — reports pending counts, keeps outbox.
    Credentials but no library: mode=stub.
    With client: mode=firestore — set() and mark synced; failures bump attempts.
    """
    rows = conn.execute(
        "SELECT id, entity_type, entity_id, payload, attempts FROM sync_outbox "
        "WHERE entity_type IN ('weighing_session', 'device_health') "
        "AND attempts < ? "
        "ORDER BY created_at ASC LIMIT 100",
        (MAX_ATTEMPTS,),
    ).fetchall()

    mode = sync_mode()
    if not rows:
        return SyncReport(ok=True, mode=mode, message="Outbox empty")

    if dry_run or mode != "firestore":
        return SyncReport(
            ok=True,
            mode=mode if not dry_run else "stub",
            message=(
                f"{len(rows)} pending outbox item(s); "
                f"mode={mode}. Local SQLite remains source of truth. "
                "Set GOOGLE_CLOUD_PROJECT=boviscan-c2430 + credentials or "
                "FIRESTORE_EMULATOR_HOST to enable push."
            ),
            pushed_sessions=0,
            pushed_health=0,
        )

    client = _try_firestore_client()
    if client is None:
        return SyncReport(
            ok=True,
            mode="stub",
            message=f"{len(rows)} pending; Firestore client unavailable",
        )

    sessions = health = failed = retried = 0
    for row in rows:
        payload = json.loads(row["payload"])
        coll_key = (
            "weighing_sessions" if row["entity_type"] == "weighing_session" else "device_health"
        )
        coll = COLLECTIONS[coll_key]
        try:
            client.collection(coll).document(row["entity_id"]).set(payload, merge=True)
            _mark_synced(conn, row["entity_type"], row["entity_id"])
            if row["entity_type"] == "weighing_session":
                sessions += 1
            else:
                health += 1
            if row["attempts"] and row["attempts"] > 0:
                retried += 1
        except Exception as exc:
            _bump_attempt(conn, row["id"], str(exc))
            failed += 1

    return SyncReport(
        ok=failed == 0,
        mode="firestore",
        pushed_sessions=sessions,
        pushed_health=health,
        retried=retried,
        failed=failed,
        message="Synced to Firestore" if failed == 0 else f"Partial sync; {failed} failed",
    )
