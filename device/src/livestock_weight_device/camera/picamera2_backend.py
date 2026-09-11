"""Raspberry Pi Camera Module 3 backend via picamera2 (optional dependency)."""

from __future__ import annotations

import time

import numpy as np

from .base import Camera, Frame


class PiCamera2Camera(Camera):
    """libcamera-friendly capture using picamera2 when installed on Pi OS."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 15) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self._cam = None

    def open(self) -> None:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "picamera2 is not installed. Use camera.backend=mock on laptops "
                "or pip install with the 'pi' extra on Raspberry Pi OS."
            ) from e
        cam = Picamera2()
        config = cam.create_preview_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        cam.configure(config)
        cam.start()
        self._cam = cam

    def close(self) -> None:
        if self._cam is not None:
            self._cam.stop()
            self._cam.close()
            self._cam = None

    def capture(self) -> Frame:
        if self._cam is None:
            raise RuntimeError("PiCamera2Camera is not open")
        arr = self._cam.capture_array()
        if not isinstance(arr, np.ndarray):
            arr = np.asarray(arr)
        h, w = arr.shape[:2]
        return Frame(
            image=arr,
            timestamp_ns=time.time_ns(),
            width=w,
            height=h,
            meta={"source": "picamera2"},
        )
