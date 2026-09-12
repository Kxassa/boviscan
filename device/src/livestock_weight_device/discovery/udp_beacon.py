"""Lightweight UDP beacon for multi-device LAN discovery.

Design
------
- Device broadcasts a small JSON payload to UDP port 45454 (configurable)
  on 255.255.255.255 (or a unicast companion API via HTTP /devices/beacon).
- Companion API maintains a /devices registry (last_seen + health snippet).
- mDNS / DNS-SD (_boviscan._tcp) is preferred on some LANs but pulls in
  zeroconf; see docs/DISCOVERY.md. This module implements UDP only.

Beacon is best-effort and never raises into the pipeline.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORT = 45454
DEFAULT_INTERVAL_S = 5.0

_stop = threading.Event()
_thread: threading.Thread | None = None


@dataclass
class BeaconPayload:
    device_id: str
    display_name: str | None = None
    host: str | None = None
    port: int | None = 8000
    api_base: str | None = None
    version: str = "0.1.0"
    source: str = "udp"
    online: bool = True
    health: dict[str, Any] = field(default_factory=dict)
    ts: str = ""

    def to_json(self) -> bytes:
        d = asdict(self)
        if not d["ts"]:
            d["ts"] = datetime.now(timezone.utc).isoformat()
        return json.dumps(d, separators=(",", ":")).encode("utf-8")


def _guess_host() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        s.close()
        return host
    except OSError:
        return "127.0.0.1"


def _broadcast_once(payload: BeaconPayload, port: int) -> None:
    data = payload.to_json()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)
        sock.sendto(data, ("255.255.255.255", port))
        # Also loopback for same-host mock demos
        sock.sendto(data, ("127.0.0.1", port))
    except OSError:
        pass
    finally:
        sock.close()


def _http_announce(api_base: str, payload: BeaconPayload) -> None:
    """Optional HTTP register so companion API learns the device without a UDP listener."""
    try:
        import httpx

        body = asdict(payload)
        body.pop("ts", None)
        httpx.post(
            f"{api_base.rstrip('/')}/devices/beacon",
            json=body,
            timeout=2.0,
        )
    except Exception:
        pass


def _loop(payload: BeaconPayload, port: int, interval_s: float, api_base: str | None) -> None:
    while not _stop.is_set():
        p = BeaconPayload(
            device_id=payload.device_id,
            display_name=payload.display_name or payload.device_id,
            host=payload.host or _guess_host(),
            port=payload.port,
            api_base=payload.api_base or (f"http://{payload.host or _guess_host()}:8000"),
            version=payload.version,
            source="udp",
            online=True,
            health=dict(payload.health),
        )
        _broadcast_once(p, port)
        if api_base:
            _http_announce(api_base, p)
        _stop.wait(interval_s)


def start_udp_beacon(
    device_id: str,
    *,
    display_name: str | None = None,
    version: str = "0.1.0",
    health: dict[str, Any] | None = None,
    port: int | None = None,
    interval_s: float | None = None,
    api_base: str | None = None,
    host: str | None = None,
) -> None:
    """Start background UDP beacon (idempotent)."""
    global _thread
    if _thread and _thread.is_alive():
        return
    port = port or int(os.environ.get("LW_DISCOVERY_PORT", DEFAULT_PORT))
    interval_s = interval_s or float(os.environ.get("LW_DISCOVERY_INTERVAL_S", DEFAULT_INTERVAL_S))
    payload = BeaconPayload(
        device_id=device_id,
        display_name=display_name or device_id,
        host=host,
        version=version,
        health=health or {},
        api_base=api_base,
    )
    _stop.clear()
    _thread = threading.Thread(
        target=_loop,
        args=(payload, port, interval_s, api_base),
        name="boviscan-udp-beacon",
        daemon=True,
    )
    _thread.start()


def stop_udp_beacon() -> None:
    global _thread
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2.0)
    _thread = None
