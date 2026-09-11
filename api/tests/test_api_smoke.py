import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Isolate DB before app import side effects
os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-test.db")
if Path(os.environ["LW_API_DB_PATH"]).exists():
    Path(os.environ["LW_API_DB_PATH"]).unlink()

from livestock_weight_api.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


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
