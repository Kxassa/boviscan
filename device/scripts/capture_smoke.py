#!/usr/bin/env python3
"""Capture one still frame: picamera2 when available, MockCamera otherwise.

Usage:
  python device/scripts/capture_smoke.py --out /tmp/boviscan-still.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _save_rgb(path: Path, image) -> Path:
    """Save RGB ndarray as JPEG/PNG without hard-requiring Pillow. Returns path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # type: ignore

        Image.fromarray(image).save(path)
        return path
    except ImportError:
        pass
    import numpy as np

    arr = np.asarray(image)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise SystemExit("expected HxWx3 RGB array")
    h, w = arr.shape[:2]
    ppm = path.with_suffix(".ppm")
    with open(ppm, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        f.write(arr[:, :, :3].astype("uint8").tobytes())
    if path.suffix.lower() in (".jpg", ".jpeg", ".png"):
        print(f"warn: Pillow not installed; wrote {ppm} instead of {path}", file=sys.stderr)
    return ppm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BoviScan camera capture smoke")
    parser.add_argument("--out", default="/tmp/boviscan-still.jpg", help="Output image path")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--force-mock", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out)
    source = "mock"

    if not args.force_mock:
        try:
            from livestock_weight_device.camera.picamera2_backend import PiCamera2Camera

            cam = PiCamera2Camera(width=args.width, height=args.height)
            cam.open()
            try:
                frame = cam.capture()
                source = "picamera2"
            finally:
                cam.close()
            written = _save_rgb(out, frame.image)
            print(f"ok source={source} path={written} size={frame.width}x{frame.height}")
            return 0
        except Exception as exc:
            print(f"info: picamera2 unavailable ({exc}); using mock", file=sys.stderr)

    # Ensure package import works when run from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from livestock_weight_device.camera.mock import MockCamera

    cam = MockCamera(width=args.width, height=args.height)
    cam.open()
    try:
        frame = cam.capture()
    finally:
        cam.close()
    written = _save_rgb(out, frame.image)
    print(f"ok source=mock path={written} size={frame.width}x{frame.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
