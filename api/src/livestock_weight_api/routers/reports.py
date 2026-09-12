"""Farm-level weighing reports and CSV export (research proxy weights)."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..auth import optional_firebase_user

router = APIRouter(prefix="/reports", tags=["reports"])

DISCLAIMER = (
    "Estimativas visuais (proxy de pesquisa). Não use como peso certificado ou comercial."
)


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


class SpeciesSummary(BaseModel):
    species: str
    count: int
    avg_kg: float | None = None
    min_kg: float | None = None
    max_kg: float | None = None


class FarmReportOut(BaseModel):
    from_ts: str | None = None
    to_ts: str | None = None
    species_filter: str | None = None
    event_count: int = 0
    with_weight_count: int = 0
    avg_kg: float | None = None
    min_kg: float | None = None
    max_kg: float | None = None
    by_species: list[SpeciesSummary] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    research_proxy: bool = True


def _parse_bounds(
    date_from: str | None, date_to: str | None
) -> tuple[str | None, str | None]:
    """Accept YYYY-MM-DD or full ISO; expand date-only to day bounds (UTC)."""
    from_ts = date_from
    to_ts = date_to
    if date_from and len(date_from) == 10 and "T" not in date_from:
        from_ts = f"{date_from}T00:00:00+00:00"
    if date_to and len(date_to) == 10 and "T" not in date_to:
        to_ts = f"{date_to}T23:59:59.999999+00:00"
    return from_ts, to_ts


def _event_where(
    date_from: str | None,
    date_to: str | None,
    species: str | None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    from_ts, to_ts = _parse_bounds(date_from, date_to)
    if from_ts:
        clauses.append("timestamp >= ?")
        params.append(from_ts)
    if to_ts:
        clauses.append("timestamp <= ?")
        params.append(to_ts)
    if species:
        clauses.append("species = ?")
        params.append(species)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def build_farm_report(
    conn: sqlite3.Connection,
    date_from: str | None = None,
    date_to: str | None = None,
    species: str | None = None,
) -> FarmReportOut:
    where, params = _event_where(date_from, date_to, species)
    overall = conn.execute(
        f"""
        SELECT
          COUNT(*) AS n,
          COUNT(estimated_weight_kg) AS n_w,
          AVG(estimated_weight_kg) AS avg_kg,
          MIN(estimated_weight_kg) AS min_kg,
          MAX(estimated_weight_kg) AS max_kg
        FROM weight_events
        {where}
        """,
        params,
    ).fetchone()
    by_rows = conn.execute(
        f"""
        SELECT
          species,
          COUNT(*) AS n,
          AVG(estimated_weight_kg) AS avg_kg,
          MIN(estimated_weight_kg) AS min_kg,
          MAX(estimated_weight_kg) AS max_kg
        FROM weight_events
        {where}
        GROUP BY species
        ORDER BY species
        """,
        params,
    ).fetchall()
    from_ts, to_ts = _parse_bounds(date_from, date_to)
    return FarmReportOut(
        from_ts=from_ts,
        to_ts=to_ts,
        species_filter=species,
        event_count=int(overall["n"] or 0),
        with_weight_count=int(overall["n_w"] or 0),
        avg_kg=float(overall["avg_kg"]) if overall["avg_kg"] is not None else None,
        min_kg=float(overall["min_kg"]) if overall["min_kg"] is not None else None,
        max_kg=float(overall["max_kg"]) if overall["max_kg"] is not None else None,
        by_species=[
            SpeciesSummary(
                species=r["species"],
                count=int(r["n"] or 0),
                avg_kg=float(r["avg_kg"]) if r["avg_kg"] is not None else None,
                min_kg=float(r["min_kg"]) if r["min_kg"] is not None else None,
                max_kg=float(r["max_kg"]) if r["max_kg"] is not None else None,
            )
            for r in by_rows
        ],
    )


@router.get("/farm", response_model=FarmReportOut)
def farm_report(
    date_from: str | None = Query(None, description="YYYY-MM-DD or ISO start"),
    date_to: str | None = Query(None, description="YYYY-MM-DD or ISO end"),
    species: str | None = Query(None, description="Filter species e.g. cattle"),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> FarmReportOut:
    return build_farm_report(conn, date_from, date_to, species)


@router.get("/farm/export.csv")
def farm_report_csv(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    species: str | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict | None = Depends(optional_firebase_user),
) -> StreamingResponse:
    report = build_farm_report(conn, date_from, date_to, species)
    where, params = _event_where(date_from, date_to, species)
    events = conn.execute(
        f"SELECT * FROM weight_events{where} ORDER BY timestamp ASC",
        params,
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["# BoviScan farm report — research proxy weights"])
    writer.writerow(["# disclaimer", DISCLAIMER])
    writer.writerow(
        [
            "# summary",
            f"from={report.from_ts or ''}",
            f"to={report.to_ts or ''}",
            f"species={report.species_filter or 'all'}",
            f"count={report.event_count}",
            f"avg_kg={report.avg_kg if report.avg_kg is not None else ''}",
            f"min_kg={report.min_kg if report.min_kg is not None else ''}",
            f"max_kg={report.max_kg if report.max_kg is not None else ''}",
        ]
    )
    writer.writerow([])
    writer.writerow(
        [
            "event_id",
            "session_id",
            "device_id",
            "track_id",
            "timestamp",
            "species",
            "estimated_weight_kg",
            "confidence",
            "research_proxy",
            "calibration_id",
        ]
    )
    import json

    for e in events:
        pm = json.loads(e["proxy_metrics"] or "{}")
        writer.writerow(
            [
                e["id"],
                e["session_id"],
                e["device_id"],
                e["track_id"],
                e["timestamp"],
                e["species"],
                e["estimated_weight_kg"],
                e["confidence"],
                pm.get("research_proxy", True),
                e["calibration_id"],
            ]
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    data = buf.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="boviscan-farm-report-{stamp}.csv"'
        },
    )
