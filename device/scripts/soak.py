#!/usr/bin/env python3
"""Performance / thermal soak harness for BoviScan edge inference.

Runs N frames with the chosen backend; logs FPS, latency p50/p95, CPU temp
(if /sys thermal is available), and Hailo presence. Writes JSON results to
/tmp or artifacts/ (gitignored).

Examples:
  python device/scripts/soak.py --frames 100 --backend cpu_mock
  python device/scripts/soak.py --frames 50 --backend hailo --out artifacts/soak.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Allow running without install when cwd is device/
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from livestock_weight_device.camera.mock import MockCamera  # noqa: E402
from livestock_weight_device.config import InferenceConfig, load_config  # noqa: E402
from livestock_weight_device.inference.factory import create_inference_backend  # noqa: E402
from livestock_weight_device.inference.hailo import probe_hailo_sdk  # noqa: E402


def _cpu_temp_c() -> float | None:
    path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(path, encoding="utf-8") as f:
            return int(f.read().strip()) / 1000.0
    except OSError:
        return None


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BoviScan inference soak harness")
    parser.add_argument("--frames", "-n", type=int, default=100, help="Number of frames")
    parser.add_argument(
        "--backend",
        default=None,
        help="Inference backend (default: config / LW_INFERENCE_BACKEND / cpu_mock)",
    )
    parser.add_argument("--config", default=None, help="device YAML path")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument(
        "--out",
        default=None,
        help="JSON output path (default: /tmp/boviscan-soak-<ts>.json)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Warmup frames excluded from latency stats",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    backend_name = (
        args.backend
        or os.environ.get("LW_INFERENCE_BACKEND")
        or cfg.inference.backend
        or "cpu_mock"
    )
    inf = InferenceConfig(
        backend=backend_name,
        model_path=cfg.inference.model_path,
        hef_path=cfg.inference.hef_path or os.environ.get("LW_HEF_PATH"),
        batch=cfg.inference.batch,
        input_width=cfg.inference.input_width,
        input_height=cfg.inference.input_height,
        input_channels=cfg.inference.input_channels,
        confidence_threshold=cfg.inference.confidence_threshold,
        postprocess=cfg.inference.postprocess,
        fallback_to_cpu=cfg.inference.fallback_to_cpu,
        labels=list(cfg.inference.labels),
    )

    hailo_probe = probe_hailo_sdk()
    backend = create_inference_backend(inf)
    t_load0 = time.perf_counter()
    backend.load()
    load_ms = (time.perf_counter() - t_load0) * 1000.0

    cam = MockCamera(width=args.width, height=args.height, seed=42)
    cam.open()

    latencies_ms: list[float] = []
    temps: list[float] = []
    det_counts: list[int] = []
    status = getattr(backend, "status", lambda: {})()
    fallback = bool(status.get("fallback_active")) if status else False

    total = args.frames + max(0, args.warmup)
    t0 = time.perf_counter()
    for i in range(total):
        frame = cam.capture()
        t1 = time.perf_counter()
        dets = backend.predict(frame.image)
        dt_ms = (time.perf_counter() - t1) * 1000.0
        if i >= args.warmup:
            latencies_ms.append(dt_ms)
            det_counts.append(len(dets))
            temp = _cpu_temp_c()
            if temp is not None:
                temps.append(temp)
    elapsed = time.perf_counter() - t0
    cam.close()
    backend.close()

    measured = len(latencies_ms)
    sorted_lat = sorted(latencies_ms)
    fps = (measured / elapsed) if elapsed > 0 and measured else 0.0
    # Prefer measured-window FPS (exclude rough wall for warmup by re-timing):
    # approximate: use sum of latencies
    if latencies_ms:
        fps = 1000.0 / (sum(latencies_ms) / len(latencies_ms))

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "backend_requested": backend_name,
        "frames": measured,
        "warmup": args.warmup,
        "width": args.width,
        "height": args.height,
        "load_ms": round(load_ms, 3),
        "fps": round(fps, 3),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies_ms), 3) if latencies_ms else None,
            "p50": round(_percentile(sorted_lat, 50) or 0, 3) if sorted_lat else None,
            "p95": round(_percentile(sorted_lat, 95) or 0, 3) if sorted_lat else None,
            "min": round(min(latencies_ms), 3) if latencies_ms else None,
            "max": round(max(latencies_ms), 3) if latencies_ms else None,
        },
        "detections_mean": round(statistics.fmean(det_counts), 3) if det_counts else 0,
        "cpu_temp_c": {
            "available": bool(temps),
            "mean": round(statistics.fmean(temps), 2) if temps else None,
            "max": round(max(temps), 2) if temps else None,
            "samples": len(temps),
        },
        "hailo": {
            "sdk_importable": hailo_probe.get("sdk_importable"),
            "sdk_module": hailo_probe.get("sdk_module"),
            "device_node": hailo_probe.get("device_node"),
            "fallback_active": fallback,
            "backend_status": status,
        },
        "note": "No accuracy claims; timings only. Hardware-blocked when Hailo SDK/HEF absent.",
    }

    out = args.out
    if not out:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        art = Path("artifacts")
        if art.is_dir():
            out = str(art / f"soak-{ts}.json")
        else:
            out = f"/tmp/boviscan-soak-{ts}.json"
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
