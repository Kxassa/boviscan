"""BoviScan → LIS HTTP bridge routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..auth import optional_firebase_user
from ..lis_bridge import accept_estimated_weight
from ..models import LisEstimatedWeightIn, LisEstimatedWeightOut

router = APIRouter(prefix="/bridge", tags=["bridge"])


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.post("/lis/estimated-weight", response_model=LisEstimatedWeightOut)
def post_lis_estimated_weight(
    body: LisEstimatedWeightIn,
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> LisEstimatedWeightOut:
    """
    Accept a visual weight estimate and queue/stub outbound to LIS.

    Contract: docs/INTEGRATION_LIS.md — metodo always estimativa_visual.
    animalId optional; unmatched animals are LIS-side pending.
    """
    result = accept_estimated_weight(conn, body.model_dump())
    return LisEstimatedWeightOut(
        ok=result.ok,
        mode=result.mode,
        outbox_id=result.outbox_id,
        farm_id=body.farm_id,
        device_id=body.device_id,
        idempotency_key=body.idempotency_key,
        peso_kg=body.peso_kg,
        animal_id=body.animal_id,
        metodo="estimativa_visual",
        outbound=result.outbound,
        message=result.message,
        http_status=result.http_status,
    )
