"""Camera capture interface (picamera2 / libcamera friendly)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Frame:
    """Single captured frame."""

    image: np.ndarray  # HxWxC uint8 RGB
    timestamp_ns: int
    width: int
    height: int
    meta: dict[str, Any] | None = None


class Camera(ABC):
    """Abstract capture interface."""

    @abstractmethod
    def open(self) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @abstractmethod
    def capture(self) -> Frame:
        ...

    def __enter__(self) -> Camera:
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
