"""CLI entry: run mock or configured pipeline; optionally POST events to companion API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from .calibration.geometry import default_calibration
from .camera.factory import create_camera
from .config import load_config
from .inference.factory import create_inference_backend
from .pipeline.runner import Pipeline


def _maybe_start_session(api_base: str, device_id: str, notes: str | None) -> str | None:
    try:
        r = httpx.post(
            f"{api_base.rstrip('/')}/sessions/start",
            json={"device_id": device_id, "notes": notes},
            timeout=5.0,
        )
        r.raise_for_status()
        return r.json().get("id")
    except Exception as exc:
        print(f"warn: could not start session via API ({exc}); continuing without session_id", file=sys.stderr)
        return None


def _heartbeat(api_base: str, device_id: str, backend: str, state: str) -> None:
    try:
        httpx.put(
            f"{api_base.rstrip('/')}/status",
            json={
                "device_id": device_id,
                "online": True,
                "camera_ok": True,
                "inference_backend": backend,
                "pipeline_state": state,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "version": "0.1.0",
            },
            timeout=3.0,
        )
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="livestock-weight-device")
    parser.add_argument("--config", default=None, help="Path to device YAML config")
    parser.add_argument("--steps", type=int, default=30, help="Pipeline iterations")
    parser.add_argument("--json", action="store_true", help="Print events as JSON lines")
    parser.add_argument(
        "--post-api",
        action="store_true",
        help="POST weight events to companion API (LW_API_BASE_URL / config api.base_url)",
    )
    parser.add_argument(
        "--api-base-url",
        default=None,
        help="Override companion API base URL",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Existing session id to attach events to",
    )
    parser.add_argument(
        "--start-session",
        action="store_true",
        help="Create a new weighing session via API before running",
    )
    parser.add_argument("--species", default=None, help="Override species (default cattle)")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    species = args.species or cfg.species_default or "cattle"
    api_base = args.api_base_url or os.environ.get("LW_API_BASE_URL") or cfg.api.base_url
    post_api = args.post_api or os.environ.get("LW_POST_API", "").lower() in ("1", "true", "yes")

    camera = create_camera(cfg.camera)
    backend = create_inference_backend(cfg.inference)
    cal = default_calibration(
        height_m=cfg.camera.height_m,
        fov_horizontal_deg=cfg.camera.fov_horizontal_deg,
        width=cfg.camera.width,
        height=cfg.camera.height,
        species=species,
    )

    session_id = args.session_id
    if post_api and args.start_session and not session_id:
        session_id = _maybe_start_session(api_base, cfg.api.device_id, notes="mock pipeline")
    if post_api and not session_id:
        # Local ephemeral id so events still group; API may create session on ingest
        session_id = str(uuid4())

    if post_api:
        _heartbeat(api_base, cfg.api.device_id, cfg.inference.backend, "running")

    pipeline = Pipeline(
        camera=camera,
        backend=backend,
        calibration=cal,
        device_id=cfg.api.device_id,
        species=species,
        api_base_url=api_base if post_api else None,
        session_id=session_id,
    )
    events = pipeline.run(steps=args.steps)

    if post_api:
        _heartbeat(api_base, cfg.api.device_id, cfg.inference.backend, "idle")

    if args.json:
        for e in events:
            print(json.dumps(e.to_dict()))
    else:
        print(
            f"backend={cfg.inference.backend} camera={cfg.camera.backend} "
            f"species={species} events={len(events)} post_api={post_api} "
            f"session_id={session_id}"
        )
        for e in events:
            print(
                f"  {e.track_id} weight_kg={e.estimated_weight_kg} "
                f"conf={e.confidence:.2f} area_m2={e.proxy_metrics.get('area_m2')} "
                f"(research proxy)"
            )
        if pipeline._post_errors:
            print(f"warn: {len(pipeline._post_errors)} API post error(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
