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
    model_path: str | None = None
    confidence_threshold: float = 0.4


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


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config from YAML file and optional env overrides."""
    raw: dict[str, Any] = {}
    cfg_path = path or os.environ.get("LIVESTOCK_WEIGHT_CONFIG")
    if cfg_path and Path(cfg_path).is_file():
        with open(cfg_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    cam = {**CameraConfig().__dict__, **(raw.get("camera") or {})}
    inf = {**InferenceConfig().__dict__, **(raw.get("inference") or {})}
    api = {**ApiConfig().__dict__, **(raw.get("api") or {})}

    # Env overrides (no secrets required)
    if v := os.environ.get("LW_CAMERA_BACKEND"):
        cam["backend"] = v
    if v := os.environ.get("LW_INFERENCE_BACKEND"):
        inf["backend"] = v
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
