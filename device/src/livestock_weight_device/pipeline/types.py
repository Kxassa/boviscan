from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class Track:
    track_id: str
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    hits: int = 1


@dataclass
class WeightEvent:
    id: str
    device_id: str
    track_id: str
    timestamp: str
    species: str
    estimated_weight_kg: float | None
    confidence: float
    proxy_metrics: dict[str, Any]
    calibration_id: str | None = None
    session_id: str | None = None
    frame_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def create(
        *,
        device_id: str,
        track_id: str,
        species: str,
        estimated_weight_kg: float | None,
        confidence: float,
        proxy_metrics: dict[str, Any],
        calibration_id: str | None = None,
        session_id: str | None = None,
    ) -> WeightEvent:
        return WeightEvent(
            id=str(uuid4()),
            device_id=device_id,
            track_id=track_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            species=species,
            estimated_weight_kg=estimated_weight_kg,
            confidence=confidence,
            proxy_metrics=proxy_metrics,
            calibration_id=calibration_id,
            session_id=session_id,
        )
