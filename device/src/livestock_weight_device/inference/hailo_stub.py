"""Hailo-8 backend stub — interface only; no HEF binaries or SDK calls required."""

from __future__ import annotations

import numpy as np

from .base import Detection, InferenceBackend
from .mock import CPUMockBackend


class HailoBackend(InferenceBackend):
    """
    Placeholder for Hailo Runtime + HEF models (~26 TOPS HAT).

    Until the HailoRT SDK and a compiled HEF are present on the device,
    this stub delegates to CPUMockBackend so the pipeline keeps running.
    See ml/notes/hailo_hef_export.md for the documented export path.
    """

    name = "hailo"

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self._fallback = CPUMockBackend()
        self._hailo_ready = False

    def load(self) -> None:
        # Real implementation would: load HEF via hailo_platform / HailoRT.
        # We intentionally do not import proprietary SDKs here.
        if self.model_path:
            # Path recorded for future use; file presence does not enable fake accuracy.
            self._hailo_ready = False
        self._fallback.load()

    def predict(self, image: np.ndarray) -> list[Detection]:
        if self._hailo_ready:
            raise NotImplementedError("Hailo Runtime path not wired in this skeleton")
        return self._fallback.predict(image)

    def close(self) -> None:
        self._fallback.close()
