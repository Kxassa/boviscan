"""MockCamera for CI and laptop development (no CSI hardware)."""

from __future__ import annotations

import time

import numpy as np

from .base import Camera, Frame


class MockCamera(Camera):
    def __init__(self, width: int = 1280, height: int = 720, seed: int = 42) -> None:
        self.width = width
        self.height = height
        self._rng = np.random.default_rng(seed)
        self._open = False
        self._frame_idx = 0

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def capture(self) -> Frame:
        if not self._open:
            raise RuntimeError("MockCamera is not open")
        # Synthetic RGB noise + a moving blob as a stand-in animal
        img = self._rng.integers(20, 60, size=(self.height, self.width, 3), dtype=np.uint8)
        cx = int((self._frame_idx * 17) % (self.width - 200)) + 100
        cy = self.height // 2
        img[cy - 40 : cy + 40, cx - 80 : cx + 80] = (180, 140, 100)
        self._frame_idx += 1
        return Frame(
            image=img,
            timestamp_ns=time.time_ns(),
            width=self.width,
            height=self.height,
            meta={"source": "mock", "frame_idx": self._frame_idx},
        )
