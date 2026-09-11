"""frame → detect → track → weight estimate → event."""

from __future__ import annotations

from typing import Any, Callable

import httpx

from ..calibration.geometry import Calibration
from ..camera.base import Camera
from ..inference.base import Detection, InferenceBackend
from .types import Track, WeightEvent


class SimpleTracker:
    """IoU-free single-track placeholder good enough for mock lanes."""

    def __init__(self) -> None:
        self._track: Track | None = None
        self._counter = 0

    def update(self, detections: list[Detection]) -> list[Track]:
        if not detections:
            self._track = None
            return []
        d = max(detections, key=lambda x: x.confidence)
        if self._track is None:
            self._counter += 1
            self._track = Track(
                track_id=f"trk-{self._counter}",
                label=d.label,
                confidence=d.confidence,
                x1=d.x1,
                y1=d.y1,
                x2=d.x2,
                y2=d.y2,
            )
        else:
            self._track.x1, self._track.y1, self._track.x2, self._track.y2 = d.x1, d.y1, d.x2, d.y2
            self._track.confidence = d.confidence
            self._track.hits += 1
        return [self._track]


class Pipeline:
    def __init__(
        self,
        camera: Camera,
        backend: InferenceBackend,
        calibration: Calibration,
        device_id: str,
        species: str = "cattle",
        api_base_url: str | None = None,
        session_id: str | None = None,
        on_event: Callable[[WeightEvent], None] | None = None,
    ) -> None:
        self.camera = camera
        self.backend = backend
        self.calibration = calibration
        self.device_id = device_id
        self.species = species
        self.api_base_url = api_base_url
        self.session_id = session_id
        self.on_event = on_event
        self.tracker = SimpleTracker()
        self.events: list[WeightEvent] = []

    def step(self) -> WeightEvent | None:
        frame = self.camera.capture()
        detections = self.backend.predict(frame.image)
        tracks = self.tracker.update(detections)
        if not tracks:
            return None
        track = tracks[0]
        # Emit after a few hits to simulate a stable passage
        if track.hits < 3:
            return None
        if track.hits > 3 and len(self.events) and self.events[-1].track_id == track.track_id:
            return None  # one event per track in this simple runner

        geom = self.calibration.bbox_to_ground_size(track.x1, track.y1, track.x2, track.y2)
        weight = self.calibration.estimate_weight_kg(geom["area_m2"])
        event = WeightEvent.create(
            device_id=self.device_id,
            track_id=track.track_id,
            species=self.species,
            estimated_weight_kg=weight,
            confidence=track.confidence,
            proxy_metrics={**geom, "area_px": (track.x2 - track.x1) * (track.y2 - track.y1)},
            calibration_id=f"cal-h{self.calibration.camera_height_m}",
            session_id=self.session_id,
        )
        self.events.append(event)
        if self.on_event:
            self.on_event(event)
        if self.api_base_url:
            self._post_event(event)
        return event

    def _post_event(self, event: WeightEvent) -> None:
        try:
            httpx.post(f"{self.api_base_url.rstrip('/')}/events", json=event.to_dict(), timeout=2.0)
        except Exception:
            # Offline-first: swallow network errors in mock/edge runs
            pass

    def run(self, steps: int = 30) -> list[WeightEvent]:
        self.camera.open()
        self.backend.load()
        try:
            for _ in range(steps):
                self.step()
        finally:
            self.backend.close()
            self.camera.close()
        return self.events
