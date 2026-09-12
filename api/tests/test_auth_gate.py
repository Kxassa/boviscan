"""Auth gate: when disabled, open; when enabled without token, 401."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["LW_API_DB_PATH"] = str(Path("/tmp") / "lw-auth-test.db")
os.environ["FIREBASE_AUTH_ENABLED"] = "false"
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "boviscan-c2430")
os.environ.setdefault("FIREBASE_PROJECT_ID", "boviscan-c2430")
if Path(os.environ["LW_API_DB_PATH"]).exists():
    Path(os.environ["LW_API_DB_PATH"]).unlink()

# Fresh settings — reimport after env
from livestock_weight_api import settings as settings_mod  # noqa: E402
from livestock_weight_api.main import app  # noqa: E402


@pytest.fixture
def client():
    settings_mod.settings.firebase_auth_enabled = False
    with TestClient(app) as c:
        conn = c.app.state.db
        for t in ("weight_events", "weighing_sessions", "device_status", "sync_outbox"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
        yield c


def test_auth_status_disabled(client):
    r = client.get("/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert "boviscan" in body["project_id"]


def test_sessions_ok_when_auth_disabled(client):
    r = client.post("/sessions/start", json={"device_id": "dev-1"})
    assert r.status_code == 200


def test_sessions_401_when_auth_enabled_no_token(client):
    settings_mod.settings.firebase_auth_enabled = True
    try:
        r = client.post("/sessions/start", json={"device_id": "dev-1"})
        assert r.status_code == 401
    finally:
        settings_mod.settings.firebase_auth_enabled = False


def test_health_includes_auth_flag(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "auth_enabled" in r.json()
    assert "sync_mode" in r.json()
