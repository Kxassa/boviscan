import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Isolate DB before app import side effects
os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-test.db")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "boviscan-c2430")
os.environ.setdefault("FIREBASE_PROJECT_ID", "boviscan-c2430")
if Path(os.environ["LW_API_DB_PATH"]).exists():
    Path(os.environ["LW_API_DB_PATH"]).unlink()

from livestock_weight_api.main import app  # noqa: E402


@pytest.fixture
def client():
    # Fresh DB each test module load; truncate tables for isolation
    with TestClient(app) as c:
        conn = c.app.state.db
        for t in ("weight_events", "weighing_sessions", "device_status", "sync_outbox"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["product"] == "BoviScan"


def test_session_lifecycle_and_csv(client):
    start = client.post(
        "/sessions/start",
        json={"device_id": "dev-1", "notes": "test"},
    )
    assert start.status_code == 200
    sid = start.json()["id"]
    assert start.json()["status"] == "active"

    got = client.get(f"/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["id"] == sid

    listed = client.get("/sessions")
    assert any(s["id"] == sid for s in listed.json())

    payload = {
        "id": "evt-sess-1",
        "device_id": "dev-1",
        "track_id": "trk-1",
        "timestamp": "2026-09-11T12:00:00+00:00",
        "species": "cattle",
        "estimated_weight_kg": 420.5,
        "confidence": 0.8,
        "proxy_metrics": {"area_m2": 1.2, "research_proxy": True},
        "session_id": sid,
    }
    assert client.post("/events", json=payload).status_code == 200

    csv_r = client.get(f"/sessions/{sid}/export.csv")
    assert csv_r.status_code == 200
    assert "text/csv" in csv_r.headers["content-type"]
    assert "evt-sess-1" in csv_r.text
    assert "research_proxy" in csv_r.text

    stop = client.post(f"/sessions/{sid}/stop", json={})
    assert stop.status_code == 200
    assert stop.json()["status"] == "stopped"
    assert stop.json()["ended_at"] is not None


def test_event_and_sync_stub(client):
    payload = {
        "id": "evt-1",
        "device_id": "dev-1",
        "track_id": "trk-1",
        "timestamp": "2026-09-11T12:00:00+00:00",
        "species": "cattle",
        "estimated_weight_kg": 420.5,
        "confidence": 0.8,
        "proxy_metrics": {"area_m2": 1.2},
    }
    r = client.post("/events", json=payload)
    assert r.status_code == 200
    r2 = client.get("/events")
    assert len(r2.json()) >= 1
    s = client.post("/sync/run")
    assert s.status_code == 200
    body = s.json()
    assert body["ok"] is True
    assert body["mode"] in ("disabled", "stub", "firestore")
    st = client.get("/sync/status")
    assert st.status_code == 200
    assert "boviscan" in st.json()["project_id"].lower() or st.json()["mode"]


def test_status_heartbeat(client):
    r = client.put(
        "/status",
        json={
            "device_id": "dev-1",
            "online": True,
            "camera_ok": True,
            "inference_backend": "cpu_mock",
            "pipeline_state": "running",
            "last_heartbeat": "2026-09-11T12:00:00+00:00",
            "version": "0.1.0",
        },
    )
    assert r.status_code == 200
    assert len(client.get("/status").json()) >= 1


def test_auth_and_sync_status_shape(client):
    a = client.get("/auth/status")
    assert a.status_code == 200
    assert a.json()["enabled"] is False
    s = client.get("/sync/status")
    assert s.status_code == 200
    body = s.json()
    assert "weighing_sessions" in body["collections"]
    assert "device_health" in body["collections"]
    dry = client.post("/sync/run?dry_run=true")
    assert dry.status_code == 200
    assert dry.json()["mode"] in ("disabled", "stub", "firestore")
