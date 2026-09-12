"""YAML + environment configuration for the edge device."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CameraConfig:
    height_m: float = 3.0
    fov_horizontal_deg: float = 66.0
    backend: str = "mock"  # mock | picamera2
    width: int = 1280
    height: int = 720
    fps: int = 15


@dataclass
class InferenceConfig:
    backend: str = "cpu_mock"  # hailo | cpu_mock | mock
    model_path: str | None = None  # legacy alias; prefer hef_path for Hailo
    hef_path: str | None = None
    batch: int = 1
    input_width: int = 640
    input_height: int = 640
    input_channels: int = 3
    confidence_threshold: float = 0.4
    postprocess: str = "passthrough"  # passthrough | yolo_nms | none
    fallback_to_cpu: bool = True
    labels: list[str] = field(default_factory=lambda: ["livestock"])


@dataclass
class ApiConfig:
    base_url: str = "http://127.0.0.1:8000"
    device_id: str = "device-local-01"


@dataclass
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    species_default: str = "cattle"
    pipeline_interval_s: float = 0.2


def _merge_dict(dc: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    out = dict(dc)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _coerce_inference(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize YAML inference block (input_size shorthand, aliases)."""
    from dataclasses import fields as dc_fields

    out = dict(raw)
    size = out.pop("input_size", None)
    if isinstance(size, (list, tuple)) and len(size) >= 2:
        out.setdefault("input_width", int(size[0]))
        out.setdefault("input_height", int(size[1]))
        if len(size) >= 3:
            out.setdefault("input_channels", int(size[2]))
    # postprocess_hooks in YAML wins over default postprocess from dataclass merge
    if "postprocess_hooks" in out:
        hooks = out.pop("postprocess_hooks")
        if isinstance(hooks, list) and hooks:
            out["postprocess"] = str(hooks[0])
        elif isinstance(hooks, str):
            out["postprocess"] = hooks
    allowed = {f.name for f in dc_fields(InferenceConfig)}
    return {k: v for k, v in out.items() if k in allowed}



def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config from YAML file and optional env overrides."""
    raw: dict[str, Any] = {}
    cfg_path = path or os.environ.get("LIVESTOCK_WEIGHT_CONFIG")
    if cfg_path and Path(cfg_path).is_file():
        with open(cfg_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    cam = {**CameraConfig().__dict__, **(raw.get("camera") or {})}
    inf_raw = {**InferenceConfig().__dict__, **(raw.get("inference") or {})}
    inf = _coerce_inference(inf_raw)
    api = {**ApiConfig().__dict__, **(raw.get("api") or {})}

    # Env overrides (no secrets required)
    if v := os.environ.get("LW_CAMERA_BACKEND"):
        cam["backend"] = v
    if v := os.environ.get("LW_INFERENCE_BACKEND"):
        inf["backend"] = v
    if v := os.environ.get("LW_HEF_PATH"):
        inf["hef_path"] = v
    if v := os.environ.get("LW_API_BASE_URL"):
        api["base_url"] = v
    if v := os.environ.get("LW_DEVICE_ID"):
        api["device_id"] = v
    if v := os.environ.get("LW_CAMERA_HEIGHT_M"):
        cam["height_m"] = float(v)

    return AppConfig(
        camera=CameraConfig(**cam),
        inference=InferenceConfig(**inf),
        api=ApiConfig(**api),
        species_default=raw.get("species_default", "cattle"),
        pipeline_interval_s=float(raw.get("pipeline_interval_s", 0.2)),
    )
