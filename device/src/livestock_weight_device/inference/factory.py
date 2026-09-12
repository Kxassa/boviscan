from __future__ import annotations

from ..config import InferenceConfig
from .base import InferenceBackend
from .hailo import HailoBackend
from .mock import CPUMockBackend, MockBackend


def create_inference_backend(cfg: InferenceConfig) -> InferenceBackend:
    backend = (cfg.backend or "cpu_mock").lower()
    if backend == "mock":
        return MockBackend()
    if backend == "cpu_mock":
        return CPUMockBackend()
    if backend == "hailo":
        return HailoBackend(
            model_path=cfg.model_path,
            hef_path=cfg.hef_path,
            batch=cfg.batch,
            input_width=cfg.input_width,
            input_height=cfg.input_height,
            input_channels=cfg.input_channels,
            confidence_threshold=cfg.confidence_threshold,
            postprocess=cfg.postprocess,
            fallback_to_cpu=cfg.fallback_to_cpu,
            labels=list(cfg.labels) if cfg.labels else None,
        )
    raise ValueError(f"Unknown inference backend: {cfg.backend}")
