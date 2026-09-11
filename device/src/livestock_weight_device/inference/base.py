from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def area_px(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


class InferenceBackend(ABC):
    name: str = "base"

    @abstractmethod
    def load(self) -> None:
        ...

    @abstractmethod
    def predict(self, image: np.ndarray) -> list[Detection]:
        ...

    def close(self) -> None:
        return None
