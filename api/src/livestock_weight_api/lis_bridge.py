"""
BoviScan → LIS estimated-weight bridge (minimal stub).

Contract: docs/INTEGRATION_LIS.md
Env: LIS_INGEST_URL, LIS_DEVICE_TOKEN (or LIS_INGEST_TOKEN alias).
Outbound: POST {LIS}/api/boviscan/weight-events with X-Device-Token.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .firestore_sync import enqueue

ENTITY_TYPE = "lis_estimated_weight"
METODO = "estimativa_visual"
WEIGHT_EVENTS_PATH = "/api/boviscan/weight-events"


def lis_ingest_url() -> str | None:
    v = (os.environ.get("LIS_INGEST_URL") or "").strip().rstrip("/")
    return v or None


def lis_device_token() -> str | None:
    """Prefer LIS_DEVICE_TOKEN; accept LIS_INGEST_TOKEN as alias."""
    for key in ("LIS_DEVICE_TOKEN", "LIS_INGEST_TOKEN"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return None


def build_outbound_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Map validated bridge input → LIS wire JSON (camelCase)."""
    outbound: dict[str, Any] = {
        "farmId": body["farm_id"],
        "deviceId": body["device_id"],
        "idempotencyKey": body["idempotency_key"],
        "pesoKg": body["peso_kg"],
        "metodo": METODO,
        "confidence": body["confidence"],
        "capturedAt": body["captured_at"],
    }
    optional = (
        ("animal_id", "animalId"),
        ("m_bio_match", "mBioMatch"),
        ("session_id", "sessionId"),
        ("track_id", "trackId"),
        ("proxy_metrics", "proxyMetrics"),
        ("species", "species"),
        ("calibration_id", "calibrationId"),
    )
    for src, dest in optional:
        val = body.get(src)
        if val is not None:
            outbound[dest] = val
    return outbound


@dataclass
class BridgeResult:
    ok: bool
    mode: str  # stub | forwarded | queued
    outbox_id: str
    outbound: dict[str, Any]
    message: str
    http_status: int | None = None


def _post_outbound(base_url: str, payload: dict[str, Any], token: str | None) -> tuple[bool, int | None, str]:
    url = f"{base_url.rstrip('/')}{WEIGHT_EVENTS_PATH}"
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["X-Device-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            return True, int(status), "LIS ingest accepted"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return False, int(exc.code), f"LIS HTTP {exc.code}: {detail}"
    except Exception as exc:  # noqa: BLE001 — stub bridge: surface any transport error
        return False, None, f"LIS outbound failed: {exc}"


def accept_estimated_weight(conn: Any, body: dict[str, Any]) -> BridgeResult:
    """Pydantic already validated. Enqueue + stub or forward outbound."""
    outbound = build_outbound_payload(body)
    entity_id = body["idempotency_key"] or f"lis-{uuid4()}"
    outbox_id = enqueue(conn, ENTITY_TYPE, entity_id, outbound)

    base = lis_ingest_url()
    if not base:
        return BridgeResult(
            ok=True,
            mode="stub",
            outbox_id=outbox_id,
            outbound=outbound,
            message=(
                "Accepted and queued locally; LIS_INGEST_URL unset — outbound stubbed. "
                "See docs/INTEGRATION_LIS.md"
            ),
        )

    ok, status, msg = _post_outbound(base, outbound, lis_device_token())
    if ok:
        conn.execute(
            "DELETE FROM sync_outbox WHERE entity_type=? AND entity_id=?",
            (ENTITY_TYPE, entity_id),
        )
        conn.commit()
        return BridgeResult(
            ok=True,
            mode="forwarded",
            outbox_id=outbox_id,
            outbound=outbound,
            message=msg,
            http_status=status,
        )

    conn.execute(
        "UPDATE sync_outbox SET attempts = attempts + 1, last_error=? WHERE id=?",
        ((msg or "")[:500], outbox_id),
    )
    conn.commit()
    return BridgeResult(
        ok=True,
        mode="queued",
        outbox_id=outbox_id,
        outbound=outbound,
        message=msg,
        http_status=status,
    )
