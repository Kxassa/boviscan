"""CPU / deterministic mock inference backends (no Hailo required)."""

from __future__ import annotations

import numpy as np

from .base import Detection, InferenceBackend


class MockBackend(InferenceBackend):
    """Fixed synthetic detection for CI smoke tests."""

    name = "mock"

    def __init__(self, confidence: float = 0.9) -> None:
        self.confidence = confidence
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def predict(self, image: np.ndarray) -> list[Detection]:
        if not self._loaded:
            raise RuntimeError("MockBackend not loaded")
        h, w = image.shape[:2]
        return [
            Detection(
                label="livestock",
                confidence=self.confidence,
                x1=w * 0.35,
                y1=h * 0.35,
                x2=w * 0.65,
                y2=h * 0.65,
            )
        ]


class CPUMockBackend(InferenceBackend):
    """Heuristic blob detector on RGB frames — laptop stand-in for real models."""

    name = "cpu_mock"

    def __init__(self, threshold: int = 120, min_area: int = 5000) -> None:
        self.threshold = threshold
        self.min_area = min_area
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def predict(self, image: np.ndarray) -> list[Detection]:
        if not self._loaded:
            raise RuntimeError("CPUMockBackend not loaded")
        gray = image.mean(axis=2) if image.ndim == 3 else image
        mask = gray > self.threshold
        if not mask.any():
            return []
        ys, xs = np.where(mask)
        x1, x2 = float(xs.min()), float(xs.max())
        y1, y2 = float(ys.min()), float(ys.max())
        area = (x2 - x1) * (y2 - y1)
        if area < self.min_area:
            return []
        return [
            Detection(
                label="livestock",
                confidence=min(0.95, 0.5 + area / (image.shape[0] * image.shape[1])),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )
        ]
