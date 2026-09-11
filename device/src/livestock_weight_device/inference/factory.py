from __future__ import annotations

from ..config import InferenceConfig
from .base import InferenceBackend
from .hailo_stub import HailoBackend
from .mock import CPUMockBackend, MockBackend


def create_inference_backend(cfg: InferenceConfig) -> InferenceBackend:
    backend = (cfg.backend or "cpu_mock").lower()
    if backend == "mock":
        return MockBackend()
    if backend == "cpu_mock":
        return CPUMockBackend()
    if backend == "hailo":
        return HailoBackend(model_path=cfg.model_path)
    raise ValueError(f"Unknown inference backend: {cfg.backend}")
