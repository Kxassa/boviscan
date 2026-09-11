"""CLI entry: run mock or configured pipeline."""

from __future__ import annotations

import argparse
import json
import sys

from .calibration.geometry import default_calibration
from .camera.factory import create_camera
from .config import load_config
from .inference.factory import create_inference_backend
from .pipeline.runner import Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="livestock-weight-device")
    parser.add_argument("--config", default=None, help="Path to device YAML config")
    parser.add_argument("--steps", type=int, default=30, help="Pipeline iterations")
    parser.add_argument("--json", action="store_true", help="Print events as JSON lines")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    camera = create_camera(cfg.camera)
    backend = create_inference_backend(cfg.inference)
    cal = default_calibration(
        height_m=cfg.camera.height_m,
        fov_horizontal_deg=cfg.camera.fov_horizontal_deg,
        width=cfg.camera.width,
        height=cfg.camera.height,
        species=cfg.species_default,
    )
    pipeline = Pipeline(
        camera=camera,
        backend=backend,
        calibration=cal,
        device_id=cfg.api.device_id,
        species=cfg.species_default,
        api_base_url=cfg.api.base_url if args.steps else None,
    )
    # Only post if explicitly desired via env or many steps with API up — keep smoke local
    pipeline.api_base_url = None
    events = pipeline.run(steps=args.steps)
    if args.json:
        for e in events:
            print(json.dumps(e.to_dict()))
    else:
        print(f"backend={cfg.inference.backend} camera={cfg.camera.backend} events={len(events)}")
        for e in events:
            print(
                f"  {e.track_id} weight_kg={e.estimated_weight_kg} "
                f"conf={e.confidence:.2f} area_m2={e.proxy_metrics.get('area_m2')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
