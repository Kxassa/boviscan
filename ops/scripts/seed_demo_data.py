#!/usr/bin/env python3
"""Seed demo weight events + device status into the local companion API."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.environ.get("LW_API_BASE_URL", "http://127.0.0.1:8000")


def post(path: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if path != "/status" else "PUT",
    )
    # status uses PUT
    if path == "/status":
        req.get_method = lambda: "PUT"  # type: ignore
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(path, resp.status)


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    post(
        "/status",
        {
            "device_id": "device-local-01",
            "online": True,
            "camera_ok": True,
            "inference_backend": "cpu_mock",
            "pipeline_state": "running",
            "cpu_temp_c": 52.0,
            "disk_free_gb": 80.0,
            "last_heartbeat": now,
            "version": "0.1.0",
        },
    )
    for i, kg in enumerate((405.0, 412.5, 398.2)):
        post(
            "/events",
            {
                "id": str(uuid4()),
                "device_id": "device-local-01",
                "track_id": f"trk-demo-{i}",
                "timestamp": now,
                "species": "cattle",
                "estimated_weight_kg": kg,
                "confidence": 0.75,
                "proxy_metrics": {"area_m2": 1.1 + i * 0.05},
            },
        )
    print("seed complete")


if __name__ == "__main__":
    main()
