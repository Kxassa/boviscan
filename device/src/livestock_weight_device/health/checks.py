"""Device health checks for livestock-weight edge runtime."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class HealthReport:
    camera_ok: bool
    inference_backend: str
    disk_free_gb: float | None
    cpu_temp_c: float | None
    ok: bool
    details: dict[str, Any]
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cpu_temp_c() -> float | None:
    path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(path, encoding="utf-8") as f:
            return int(f.read().strip()) / 1000.0
    except OSError:
        return None


def _disk_free_gb(path: str = "/") -> float | None:
    try:
        usage = shutil.disk_usage(path)
        return round(usage.free / (1024**3), 2)
    except OSError:
        return None


def run_health_checks(
    *,
    camera_backend: str = "mock",
    inference_backend: str = "cpu_mock",
    probe_camera: bool = True,
) -> HealthReport:
    details: dict[str, Any] = {}
    camera_ok = True
    if probe_camera:
        try:
            from ..camera.factory import create_camera
            from ..config import CameraConfig

            cam = create_camera(CameraConfig(backend=camera_backend, width=320, height=240))
            cam.open()
            frame = cam.capture()
            cam.close()
            details["frame_shape"] = list(frame.image.shape)
            camera_ok = frame.image.size > 0
        except Exception as e:
            camera_ok = False
            details["camera_error"] = str(e)

    try:
        from ..inference.factory import create_inference_backend
        from ..config import InferenceConfig

        backend = create_inference_backend(InferenceConfig(backend=inference_backend))
        backend.load()
        backend.close()
        details["inference_load"] = "ok"
    except Exception as e:
        details["inference_error"] = str(e)

    disk = _disk_free_gb()
    temp = _cpu_temp_c()
    ok = camera_ok and "inference_error" not in details and (disk is None or disk > 1.0)
    return HealthReport(
        camera_ok=camera_ok,
        inference_backend=inference_backend,
        disk_free_gb=disk,
        cpu_temp_c=temp,
        ok=ok,
        details=details,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    import json

    cam = os.environ.get("LW_CAMERA_BACKEND", "mock")
    inf = os.environ.get("LW_INFERENCE_BACKEND", "cpu_mock")
    report = run_health_checks(camera_backend=cam, inference_backend=inf)
    print(json.dumps(report.to_dict(), indent=2))
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
