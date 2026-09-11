from __future__ import annotations

from ..config import CameraConfig
from .base import Camera
from .mock import MockCamera


def create_camera(cfg: CameraConfig) -> Camera:
    backend = (cfg.backend or "mock").lower()
    if backend == "mock":
        return MockCamera(width=cfg.width, height=cfg.height)
    if backend in ("picamera2", "libcamera", "pi"):
        from .picamera2_backend import PiCamera2Camera

        return PiCamera2Camera(width=cfg.width, height=cfg.height, fps=cfg.fps)
    raise ValueError(f"Unknown camera backend: {cfg.backend}")
