"""Prove sync path without real GCP: dry-run + injectable stub client."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-firestore-test.db")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "boviscan-c2430")
os.environ.setdefault("FIREBASE_PROJECT_ID", "boviscan-c2430")
# Ensure we start without emulator unless a test sets it
os.environ.pop("FIRESTORE_EMULATOR_HOST", None)

from livestock_weight_api.db.sqlite import init_db  # noqa: E402
from livestock_weight_api.firestore_sync import (  # noqa: E402
    COLLECTIONS,
    enqueue,
    run_sync,
    status_snapshot,
    sync_mode,
)


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "sync.db"
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def _seed_outbox(conn: sqlite3.Connection) -> None:
    enqueue(
        conn,
        "weighing_session",
        "sess-1",
        {"id": "sess-1", "device_id": "dev-1", "status": "stopped"},
    )
    enqueue(
        conn,
        "device_health",
        "dev-1",
        {"device_id": "dev-1", "online": True},
    )


def test_collections_documented():
    assert COLLECTIONS["weighing_sessions"] == "weighing_sessions"
    assert COLLECTIONS["device_health"] == "device_health"


def test_dry_run_without_gcp(conn):
    _seed_outbox(conn)
    report = run_sync(conn, dry_run=True)
    assert report.ok is True
    assert report.mode == "stub"
    assert "pending" in report.message.lower() or report.pending >= 2
    # Outbox retained
    n = conn.execute("SELECT COUNT(*) AS n FROM sync_outbox").fetchone()["n"]
    assert n == 2


def test_disabled_mode_keeps_outbox(conn):
    # No emulator, no credentials file → disabled
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    _seed_outbox(conn)
    assert sync_mode() == "disabled"
    report = run_sync(conn)
    assert report.mode == "disabled"
    assert report.pushed_sessions == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM sync_outbox").fetchone()["n"] == 2


def test_stub_client_pushes_and_clears(conn):
    _seed_outbox(conn)
    sleeps: list[float] = []

    doc = MagicMock()
    coll = MagicMock()
    coll.document.return_value = doc
    client = MagicMock()
    client.collection.return_value = coll

    report = run_sync(conn, client=client, sleep_fn=sleeps.append)
    assert report.ok is True
    assert report.mode == "firestore"
    assert report.pushed_sessions == 1
    assert report.pushed_health == 1
    assert report.failed == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM sync_outbox").fetchone()["n"] == 0
    # set called for both collections
    names = {c.args[0] for c in client.collection.call_args_list}
    assert "weighing_sessions" in names
    assert "device_health" in names
    assert doc.set.call_count == 2


def test_backoff_retries_then_succeeds(conn):
    enqueue(conn, "weighing_session", "sess-r", {"id": "sess-r"})
    sleeps: list[float] = []
    doc = MagicMock()
    attempts = {"n": 0}

    def flaky_set(*_a, **_k):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise ConnectionError("transient")
        return None

    doc.set.side_effect = flaky_set
    coll = MagicMock()
    coll.document.return_value = doc
    client = MagicMock()
    client.collection.return_value = coll

    report = run_sync(conn, client=client, sleep_fn=sleeps.append)
    assert report.ok is True
    assert report.pushed_sessions == 1
    assert sleeps  # backoff slept at least once


def test_status_snapshot_includes_collections(conn):
    _seed_outbox(conn)
    snap = status_snapshot(conn)
    assert snap["collections"]["weighing_sessions"] == "weighing_sessions"
    assert snap["pending"]["total"] == 2
    assert "boviscan" in snap["project_id"].lower() or snap["mode"]
