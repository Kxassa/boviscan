"""frame → detect → track → weight estimate → event → optional API POST."""

from __future__ import annotations

from typing import Any, Callable

import httpx

from ..calibration.geometry import Calibration
from ..camera.base import Camera
from ..inference.base import InferenceBackend
from .tracker import SimpleTracker
from .types import WeightEvent

# Re-export for tests that imported SimpleTracker from runner
__all__ = ["Pipeline", "SimpleTracker"]


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
        min_hits: int = 3,
    ) -> None:
        self.camera = camera
        self.backend = backend
        self.calibration = calibration
        self.device_id = device_id
        self.species = species
        self.api_base_url = api_base_url
        self.session_id = session_id
        self.on_event = on_event
        self.min_hits = min_hits
        self.tracker = SimpleTracker()
        self.events: list[WeightEvent] = []
        self._emitted_tracks: set[str] = set()
        self._post_errors: list[str] = []

    def step(self) -> WeightEvent | None:
        frame = self.camera.capture()
        detections = self.backend.predict(frame.image)
        tracks = self.tracker.update(detections)
        if not tracks:
            return None

        emitted: WeightEvent | None = None
        for track in tracks:
            if track.hits < self.min_hits:
                continue
            if track.track_id in self._emitted_tracks:
                continue  # one estimate per track (one animal ≈ one session estimate)

            geom = self.calibration.bbox_to_ground_size(track.x1, track.y1, track.x2, track.y2)
            weight, proxy_meta = self.calibration.estimate_weight_kg(
                geom["area_m2"],
                height_m=geom.get("height_proxy_m"),
            )
            proxy_metrics: dict[str, Any] = {
                **geom,
                "area_px": (track.x2 - track.x1) * (track.y2 - track.y1),
                "bbox": geom.get("bbox"),
                "size_proxy": {
                    "area_m2": geom["area_m2"],
                    "length_m": geom["length_m"],
                    "width_m": geom["width_m"],
                    "height_proxy_m": geom.get("height_proxy_m"),
                },
                "weight_proxy": proxy_meta,
                "research_proxy": True,
            }
            event = WeightEvent.create(
                device_id=self.device_id,
                track_id=track.track_id,
                species=self.species,
                estimated_weight_kg=weight,
                confidence=track.confidence,
                proxy_metrics=proxy_metrics,
                calibration_id=f"cal-h{self.calibration.camera_height_m}-{self.species}",
                session_id=self.session_id,
            )
            self.events.append(event)
            self._emitted_tracks.add(track.track_id)
            if self.on_event:
                self.on_event(event)
            if self.api_base_url:
                self._post_event(event)
            emitted = event
        return emitted

    def _post_event(self, event: WeightEvent) -> bool:
        """POST weight event to companion API. Returns True on success."""
        url = f"{self.api_base_url.rstrip('/')}/events"
        try:
            r = httpx.post(url, json=event.to_dict(), timeout=5.0)
            r.raise_for_status()
            return True
        except Exception as exc:  # Offline-first: swallow network errors
            self._post_errors.append(str(exc))
            return False

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
