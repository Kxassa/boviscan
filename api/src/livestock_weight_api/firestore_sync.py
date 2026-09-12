"""
Firestore sync for weighing sessions + device health (BoviScan).

Modes:
  - disabled: no project/credentials/emulator → outbox retained, nothing pushed
  - stub: credentials/emulator flag set but client library missing / dry_run → report only
  - firestore: real google.cloud.firestore client (or emulator via FIRESTORE_EMULATOR_HOST)

Offline-first: local SQLite + sync_outbox remain authoritative.
Never invent or commit credentials.

Collections (documented):
  weighing_sessions  — session documents keyed by session id
  device_health      — device heartbeat documents keyed by device_id

Env:
  GOOGLE_CLOUD_PROJECT / FIREBASE_PROJECT_ID  (example: boviscan-c2430)
  GOOGLE_APPLICATION_CREDENTIALS             (SA JSON path outside repo)
  FIRESTORE_EMULATOR_HOST                    (e.g. 127.0.0.1:8080)

Emulator (gcloud or docker-compose profile):
  1. docker compose -f ops/docker-compose.yml --profile emulator up firestore-emulator
     # or: gcloud emulators:start --only firestore --host-port=127.0.0.1:8080
  2. export FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
  3. export GOOGLE_CLOUD_PROJECT=boviscan-c2430
  4. pip install -e '.[firestore]' && POST /sync/run
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

# Canonical Firestore collection names (do not rename without a migration plan)
COLLECTIONS = {
    "weighing_sessions": "weighing_sessions",
    "device_health": "device_health",
}

MAX_ATTEMPTS = 5
# Per-item write retries with exponential backoff (seconds)
WRITE_MAX_RETRIES = 3
WRITE_BACKOFF_BASE_S = 0.25
WRITE_BACKOFF_CAP_S = 4.0


@dataclass
class SyncReport:
    ok: bool
    mode: str  # disabled | stub | firestore
    pushed_sessions: int = 0
    pushed_health: int = 0
    retried: int = 0
    failed: int = 0
    message: str = ""
    pending: int = 0
    collections: dict[str, str] = field(default_factory=lambda: dict(COLLECTIONS))


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


def outbox_pending_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT entity_type, COUNT(*) AS n FROM sync_outbox GROUP BY entity_type"
    ).fetchall()
    counts = {"weighing_session": 0, "device_health": 0, "total": 0}
    for r in rows:
        key = r["entity_type"] if isinstance(r, sqlite3.Row) else r[0]
        n = r["n"] if isinstance(r, sqlite3.Row) else r[1]
        if key in counts:
            counts[key] = int(n)
        counts["total"] += int(n)
    return counts


def status_snapshot(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Clearer sync status for GET /sync/status (no secrets)."""
    pending = outbox_pending_counts(conn) if conn is not None else None
    last_errors: list[dict[str, Any]] = []
    if conn is not None:
        err_rows = conn.execute(
            "SELECT entity_type, entity_id, attempts, last_error FROM sync_outbox "
            "WHERE last_error IS NOT NULL AND last_error != '' "
            "ORDER BY attempts DESC LIMIT 5"
        ).fetchall()
        for r in err_rows:
            last_errors.append(
                {
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "attempts": r["attempts"],
                    "last_error": r["last_error"],
                }
            )
    return {
        "mode": sync_mode(),
        "project_id": _project_id() or "boviscan-c2430 (default example)",
        "emulator": bool(os.environ.get("FIRESTORE_EMULATOR_HOST")),
        "emulator_host": os.environ.get("FIRESTORE_EMULATOR_HOST"),
        "credentials_path_set": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
        "collections": dict(COLLECTIONS),
        "max_attempts": MAX_ATTEMPTS,
        "write_retries": WRITE_MAX_RETRIES,
        "pending": pending,
        "recent_errors": last_errors,
        "docs": (
            "Collections: weighing_sessions, device_health. "
            "Set GOOGLE_CLOUD_PROJECT=boviscan-c2430 and either "
            "GOOGLE_APPLICATION_CREDENTIALS or FIRESTORE_EMULATOR_HOST. "
            "Install: pip install -e '.[firestore]'. "
            "Optional emulator: docker compose -f ops/docker-compose.yml "
            "--profile emulator up firestore-emulator"
        ),
    }


def _write_with_backoff(
    write_fn: Callable[[], None],
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Retry a single Firestore write with exponential backoff."""
    delay = WRITE_BACKOFF_BASE_S
    last_exc: Exception | None = None
    for attempt in range(WRITE_MAX_RETRIES):
        try:
            write_fn()
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= WRITE_MAX_RETRIES - 1:
                break
            sleep_fn(min(delay, WRITE_BACKOFF_CAP_S))
            delay *= 2
    assert last_exc is not None
    raise last_exc


def run_sync(
    conn: sqlite3.Connection,
    *,
    dry_run: bool = False,
    client: Any | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> SyncReport:
    """
    Drain sync_outbox for weighing_session and device_health with retry accounting.

    Without credentials: mode=disabled — reports pending counts, keeps outbox.
    Credentials but no library: mode=stub.
    With client: mode=firestore — set() with per-write backoff; failures bump attempts.

    `client` may be injected for tests (duck-typed .collection().document().set()).
    """
    pending = outbox_pending_counts(conn)
    rows = conn.execute(
        "SELECT id, entity_type, entity_id, payload, attempts FROM sync_outbox "
        "WHERE entity_type IN ('weighing_session', 'device_health') "
        "AND attempts < ? "
        "ORDER BY created_at ASC LIMIT 100",
        (MAX_ATTEMPTS,),
    ).fetchall()

    mode = sync_mode() if client is None else "firestore"
    if not rows:
        return SyncReport(
            ok=True,
            mode=mode,
            message="Outbox empty",
            pending=pending["total"],
        )

    if dry_run:
        return SyncReport(
            ok=True,
            mode="stub",
            message=(
                f"{len(rows)} pending outbox item(s); dry_run=true. "
                f"Would push to collections {list(COLLECTIONS.values())}. "
                "Local SQLite remains source of truth."
            ),
            pending=pending["total"],
        )

    if client is None and mode != "firestore":
        return SyncReport(
            ok=True,
            mode=mode,
            message=(
                f"{len(rows)} pending outbox item(s); "
                f"mode={mode}. Local SQLite remains source of truth. "
                "Set GOOGLE_CLOUD_PROJECT=boviscan-c2430 + credentials or "
                "FIRESTORE_EMULATOR_HOST to enable push."
            ),
            pending=pending["total"],
        )

    if client is None:
        client = _try_firestore_client()
    if client is None:
        return SyncReport(
            ok=True,
            mode="stub",
            message=f"{len(rows)} pending; Firestore client unavailable",
            pending=pending["total"],
        )

    sessions = health = failed = retried = 0
    for row in rows:
        payload = json.loads(row["payload"])
        coll_key = (
            "weighing_sessions" if row["entity_type"] == "weighing_session" else "device_health"
        )
        coll = COLLECTIONS[coll_key]
        try:

            def _do_set(
                _coll: str = coll,
                _eid: str = row["entity_id"],
                _payload: dict = payload,
            ) -> None:
                client.collection(_coll).document(_eid).set(_payload, merge=True)

            _write_with_backoff(_do_set, sleep_fn=sleep_fn)
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
        pending=outbox_pending_counts(conn)["total"],
        message="Synced to Firestore" if failed == 0 else f"Partial sync; {failed} failed",
    )
