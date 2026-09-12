"""CPU / deterministic mock inference backends (no Hailo required).

cpu_mock: motion-aware blob detector (laptop-friendly stand-in).
Optional OpenCV path if cv2 is installed — still works with numpy alone.
Hailo stub remains in hailo_stub.py for HEF later.
"""

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


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float32)
    return image.mean(axis=2).astype(np.float32)


def _largest_blob_bbox(
    mask: np.ndarray,
    *,
    min_area: int,
) -> tuple[float, float, float, float, float] | None:
    """
    Find largest connected foreground region via coarse labeling.

    Prefer OpenCV connectedComponents if present; else use a simple
    row/col projection + thresholded bounding box (good enough for mock).
    """
    if not mask.any():
        return None

    try:
        import cv2  # type: ignore

        m = (mask.astype(np.uint8) * 255)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        best = None
        best_area = 0
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < min_area or area <= best_area:
                continue
            x = float(stats[i, cv2.CC_STAT_LEFT])
            y = float(stats[i, cv2.CC_STAT_TOP])
            w = float(stats[i, cv2.CC_STAT_WIDTH])
            h = float(stats[i, cv2.CC_STAT_HEIGHT])
            best = (x, y, x + w, y + h, float(area))
            best_area = area
        return best
    except ImportError:
        pass

    # Numpy fallback: morphological-ish dilation via max pooling then bbox of mask
    ys, xs = np.where(mask)
    x1, x2 = float(xs.min()), float(xs.max())
    y1, y2 = float(ys.min()), float(ys.max())
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    if area < min_area:
        return None
    return (x1, y1, x2, y2, float(area))


class CPUMockBackend(InferenceBackend):
    """
    Motion + intensity blob detector on RGB frames.

    Tracks a previous frame; combines absolute difference (motion) with a
    brightness threshold so stationary bright blobs still register.
    Laptop stand-in for real detection models; Hailo HEF plugs in via HailoBackend.
    """

    name = "cpu_mock"

    def __init__(
        self,
        threshold: int = 120,
        min_area: int = 2500,
        motion_threshold: int = 25,
        motion_weight: float = 0.65,
    ) -> None:
        self.threshold = threshold
        self.min_area = min_area
        self.motion_threshold = motion_threshold
        self.motion_weight = motion_weight
        self._loaded = False
        self._prev_gray: np.ndarray | None = None

    def load(self) -> None:
        self._loaded = True
        self._prev_gray = None

    def predict(self, image: np.ndarray) -> list[Detection]:
        if not self._loaded:
            raise RuntimeError("CPUMockBackend not loaded")
        gray = _to_gray(image)
        bright = gray > self.threshold

        if self._prev_gray is not None and self._prev_gray.shape == gray.shape:
            motion = np.abs(gray - self._prev_gray) > self.motion_threshold
            # Union of motion and bright blobs; motion boosts confidence below
            mask = motion | bright
            used_motion = bool(motion.any())
        else:
            mask = bright
            used_motion = False

        self._prev_gray = gray

        blob = _largest_blob_bbox(mask, min_area=self.min_area)
        if blob is None:
            return []
        x1, y1, x2, y2, area = blob
        frame_area = float(image.shape[0] * image.shape[1])
        conf = min(0.95, 0.45 + area / frame_area)
        if used_motion:
            conf = min(0.98, conf + 0.08 * self.motion_weight)
        return [
            Detection(
                label="livestock",
                confidence=float(conf),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )
        ]

    def close(self) -> None:
        self._prev_gray = None
