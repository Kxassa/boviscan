"""Tests for POST /bridge/lis/estimated-weight stub + outbound mapping."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-lis-bridge-test.db")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "boviscan-c2430")
os.environ.setdefault("FIREBASE_PROJECT_ID", "boviscan-c2430")
# Ensure stub mode for default tests
os.environ.pop("LIS_INGEST_URL", None)
os.environ.pop("LIS_DEVICE_TOKEN", None)
os.environ.pop("LIS_INGEST_TOKEN", None)
if Path(os.environ["LW_API_DB_PATH"]).exists():
    Path(os.environ["LW_API_DB_PATH"]).unlink()

from livestock_weight_api.lis_bridge import build_outbound_payload  # noqa: E402
from livestock_weight_api.main import app  # noqa: E402


VALID = {
    "farm_id": "farm-001",
    "device_id": "device-local-01",
    "idempotency_key": "evt-abc-123",
    "peso_kg": 420.5,
    "confidence": 0.8,
    "captured_at": "2026-09-12T12:00:00+00:00",
    "animal_id": "lis-animal-1",
    "session_id": "sess-1",
    "track_id": "trk-1",
    "proxy_metrics": {"area_m2": 1.2, "research_proxy": True},
    "species": "cattle",
}


@pytest.fixture
def client():
    with TestClient(app) as c:
        conn = c.app.state.db
        for t in ("weight_events", "weighing_sessions", "device_status", "sync_outbox", "devices"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
        yield c


def test_outbound_payload_mapping():
    out = build_outbound_payload(VALID)
    assert out["farmId"] == "farm-001"
    assert out["deviceId"] == "device-local-01"
    assert out["idempotencyKey"] == "evt-abc-123"
    assert out["pesoKg"] == 420.5
    assert out["metodo"] == "estimativa_visual"
    assert out["confidence"] == 0.8
    assert out["capturedAt"] == "2026-09-12T12:00:00+00:00"
    assert out["animalId"] == "lis-animal-1"
    assert out["sessionId"] == "sess-1"
    assert out["trackId"] == "trk-1"
    assert out["proxyMetrics"]["area_m2"] == 1.2
    assert "Authorization" not in out


def test_outbound_omits_optional_animal():
    body = {k: v for k, v in VALID.items() if k != "animal_id"}
    body["m_bio_match"] = None
    out = build_outbound_payload(body)
    assert "animalId" not in out
    assert out["metodo"] == "estimativa_visual"


def test_bridge_stub_accepts_without_lis_url(client):
    r = client.post("/bridge/lis/estimated-weight", json=VALID)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] == "stub"
    assert body["metodo"] == "estimativa_visual"
    assert body["idempotency_key"] == "evt-abc-123"
    assert body["outbound"]["pesoKg"] == 420.5
    assert body["outbound"]["metodo"] == "estimativa_visual"
    assert body["outbound"]["idempotencyKey"] == "evt-abc-123"
    # Queued in outbox
    row = client.app.state.db.execute(
        "SELECT entity_type, entity_id, payload FROM sync_outbox WHERE entity_type=?",
        ("lis_estimated_weight",),
    ).fetchone()
    assert row is not None
    assert row["entity_id"] == "evt-abc-123"
    payload = json.loads(row["payload"])
    assert payload["metodo"] == "estimativa_visual"


def test_bridge_allows_missing_animal_id(client):
    payload = {k: v for k, v in VALID.items() if k != "animal_id"}
    r = client.post("/bridge/lis/estimated-weight", json=payload)
    assert r.status_code == 200
    assert r.json()["animal_id"] is None
    assert "animalId" not in r.json()["outbound"]


def test_bridge_rejects_invalid_peso(client):
    bad = {**VALID, "peso_kg": 0}
    r = client.post("/bridge/lis/estimated-weight", json=bad)
    assert r.status_code == 422


def test_bridge_rejects_bad_confidence(client):
    bad = {**VALID, "confidence": 1.5}
    r = client.post("/bridge/lis/estimated-weight", json=bad)
    assert r.status_code == 422


def test_bridge_forwarded_uses_x_device_token(client, monkeypatch):
    monkeypatch.setenv("LIS_INGEST_URL", "https://lis.example")
    monkeypatch.setenv("LIS_DEVICE_TOKEN", "dev-token-secret")

    captured: dict = {}

    class FakeResp:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResp()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        r = client.post("/bridge/lis/estimated-weight", json=VALID)

    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "forwarded"
    assert body["http_status"] == 201
    assert captured["url"] == "https://lis.example/api/boviscan/weight-events"
    # urllib normalizes header keys
    assert captured["headers"].get("X-device-token") == "dev-token-secret" or captured[
        "headers"
    ].get("X-Device-Token") == "dev-token-secret"
    assert "Authorization" not in captured["headers"]
    assert captured["body"]["idempotencyKey"] == "evt-abc-123"
    assert captured["body"]["metodo"] == "estimativa_visual"
    # Cleared from outbox on success
    row = client.app.state.db.execute(
        "SELECT 1 FROM sync_outbox WHERE entity_type=? AND entity_id=?",
        ("lis_estimated_weight", "evt-abc-123"),
    ).fetchone()
    assert row is None


def test_bridge_queued_on_http_error(client, monkeypatch):
    import urllib.error

    monkeypatch.setenv("LIS_INGEST_URL", "https://lis.example")
    monkeypatch.setenv("LIS_INGEST_TOKEN", "alias-token")  # alias path

    def boom(req, timeout=10):
        raise urllib.error.HTTPError(
            req.full_url, 503, "Unavailable", hdrs=None, fp=MagicMock(read=lambda: b"busy")
        )

    with patch("urllib.request.urlopen", side_effect=boom):
        r = client.post("/bridge/lis/estimated-weight", json=VALID)

    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "queued"
    assert body["http_status"] == 503
    row = client.app.state.db.execute(
        "SELECT attempts, last_error FROM sync_outbox WHERE entity_id=?",
        ("evt-abc-123",),
    ).fetchone()
    assert row is not None
    assert row["attempts"] >= 1
