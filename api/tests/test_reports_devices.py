import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-phase4-test.db")
os.environ["LW_MOCK_REGISTER_DEVICE"] = "true"
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "boviscan-c2430")
os.environ.setdefault("FIREBASE_PROJECT_ID", "boviscan-c2430")
db = Path(os.environ["LW_API_DB_PATH"])
if db.exists():
    db.unlink()

from livestock_weight_api.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        conn = c.app.state.db
        for t in ("weight_events", "weighing_sessions", "device_status", "sync_outbox", "devices"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
        # re-register mock after truncate
        from livestock_weight_api.routers.devices import register_mock_local_device

        register_mock_local_device(conn)
        yield c


def test_mock_device_registered(client):
    r = client.get("/devices")
    assert r.status_code == 200
    ids = [d["device_id"] for d in r.json()]
    assert "device-local-01" in ids
    local = next(d for d in r.json() if d["device_id"] == "device-local-01")
    assert local["source"] == "mock"
    assert local["last_seen"]


def test_device_beacon_and_list(client):
    r = client.post(
        "/devices/beacon",
        json={
            "device_id": "pi-barn-02",
            "display_name": "Galpão 2",
            "host": "192.168.1.42",
            "port": 8000,
            "api_base": "http://192.168.1.42:8000",
            "version": "0.1.0",
            "source": "udp",
            "health": {"camera_ok": True, "inference_backend": "cpu_mock"},
        },
    )
    assert r.status_code == 200
    assert r.json()["device_id"] == "pi-barn-02"
    listed = client.get("/devices").json()
    assert any(d["device_id"] == "pi-barn-02" for d in listed)
    one = client.get("/devices/pi-barn-02")
    assert one.status_code == 200
    assert one.json()["host"] == "192.168.1.42"


def test_heartbeat_upserts_device(client):
    assert (
        client.put(
            "/status",
            json={
                "device_id": "dev-hb",
                "online": True,
                "camera_ok": True,
                "inference_backend": "hailo",
                "pipeline_state": "running",
                "last_heartbeat": "2026-09-12T03:00:00+00:00",
                "version": "0.1.0",
            },
        ).status_code
        == 200
    )
    ids = [d["device_id"] for d in client.get("/devices").json()]
    assert "dev-hb" in ids


def test_farm_report_and_csv(client):
    start = client.post("/sessions/start", json={"device_id": "dev-1", "notes": "report"})
    sid = start.json()["id"]
    for i, kg in enumerate((400.0, 450.0, 500.0)):
        assert (
            client.post(
                "/events",
                json={
                    "id": f"evt-r-{i}",
                    "device_id": "dev-1",
                    "track_id": f"t-{i}",
                    "timestamp": f"2026-09-12T1{i}:00:00+00:00",
                    "species": "cattle",
                    "estimated_weight_kg": kg,
                    "confidence": 0.7,
                    "proxy_metrics": {"research_proxy": True, "area_m2": 1.1},
                    "session_id": sid,
                },
            ).status_code
            == 200
        )
    # sheep event for by_species
    client.post(
        "/events",
        json={
            "id": "evt-sheep",
            "device_id": "dev-1",
            "track_id": "t-s",
            "timestamp": "2026-09-12T15:00:00+00:00",
            "species": "sheep",
            "estimated_weight_kg": 55.0,
            "confidence": 0.6,
            "proxy_metrics": {"research_proxy": True},
            "session_id": sid,
        },
    )

    rep = client.get("/reports/farm?date_from=2026-09-12&date_to=2026-09-12&species=cattle")
    assert rep.status_code == 200
    body = rep.json()
    assert body["event_count"] == 3
    assert body["avg_kg"] == pytest.approx(450.0)
    assert body["min_kg"] == 400.0
    assert body["max_kg"] == 500.0
    assert body["research_proxy"] is True
    assert "pesquisa" in body["disclaimer"].lower() or "proxy" in body["disclaimer"].lower()

    all_rep = client.get("/reports/farm")
    assert all_rep.json()["event_count"] == 4
    assert len(all_rep.json()["by_species"]) >= 2

    csv_r = client.get("/reports/farm/export.csv?species=cattle")
    assert csv_r.status_code == 200
    assert "text/csv" in csv_r.headers["content-type"]
    assert "evt-r-0" in csv_r.text
    assert "research" in csv_r.text.lower() or "proxy" in csv_r.text.lower()

    sess_csv = client.get(f"/sessions/{sid}/export.csv")
    assert sess_csv.status_code == 200
    assert "height_proxy_m" in sess_csv.text or "research_proxy" in sess_csv.text
    assert "disclaimer" in sess_csv.text.lower() or "pesquisa" in sess_csv.text.lower()
