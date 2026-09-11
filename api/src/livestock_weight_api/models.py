from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WeightEventIn(BaseModel):
    id: str
    device_id: str
    track_id: str
    timestamp: str
    species: str = "cattle"
    estimated_weight_kg: float | None = None
    confidence: float = Field(ge=0, le=1)
    proxy_metrics: dict[str, Any] = Field(default_factory=dict)
    calibration_id: str | None = None
    session_id: str | None = None
    frame_refs: list[str] = Field(default_factory=list)


class WeightEventOut(WeightEventIn):
    synced_at: str | None = None


class DeviceStatusIn(BaseModel):
    device_id: str
    online: bool = True
    camera_ok: bool = True
    inference_backend: str | None = "cpu_mock"
    pipeline_state: str | None = "idle"
    cpu_temp_c: float | None = None
    disk_free_gb: float | None = None
    last_heartbeat: str
    version: str | None = "0.1.0"


class DeviceStatusOut(DeviceStatusIn):
    synced_at: str | None = None


class SessionStartIn(BaseModel):
    device_id: str
    notes: str | None = None
    id: str | None = None  # optional client-supplied id


class SessionStopIn(BaseModel):
    notes: str | None = None


class WeighingSessionOut(BaseModel):
    id: str
    device_id: str
    started_at: str
    ended_at: str | None = None
    event_count: int = 0
    notes: str | None = None
    sync_state: str = "pending"
    status: str = "active"  # active | stopped


class SyncResult(BaseModel):
    ok: bool
    mode: str
    pushed_sessions: int = 0
    pushed_health: int = 0
    retried: int = 0
    failed: int = 0
    message: str
