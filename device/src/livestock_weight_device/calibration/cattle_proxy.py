"""
Cattle weight proxy (RESEARCH / HEURISTIC — not validated for trade or veterinary use).

Maps projected ground-plane area (m²) and optional withers-height proxy (m) to
approximate live weight in kg using a coarse piecewise table. Values are illustrative
placeholders for pipeline wiring and calibration UX — replace after field studies.

Label every estimate as a research proxy in product UI and API payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROXY_METHOD = "cattle_area_height_table_v0"
PROXY_DISCLAIMER = (
    "Heuristic research proxy only — not certified weight. "
    "Requires herd-specific calibration before operational trust."
)


@dataclass(frozen=True)
class CattleProxyPoint:
    """One calibration anchor: area_m2 (+ optional height_m) → kg."""

    area_m2: float
    weight_kg: float
    height_m: float | None = None
    note: str = ""


# Coarse cattle table (adult beef/dairy mix stand-in). Sorted by area_m2.
# height_m is optional withers proxy when geometry can estimate it.
CATTLE_AREA_WEIGHT_TABLE: tuple[CattleProxyPoint, ...] = (
    CattleProxyPoint(0.40, 180.0, 0.95, "calf / small"),
    CattleProxyPoint(0.60, 260.0, 1.05, "yearling light"),
    CattleProxyPoint(0.80, 340.0, 1.15, "yearling"),
    CattleProxyPoint(1.00, 420.0, 1.25, "adult light"),
    CattleProxyPoint(1.20, 500.0, 1.35, "adult medium"),
    CattleProxyPoint(1.40, 580.0, 1.40, "adult heavy"),
    CattleProxyPoint(1.60, 660.0, 1.45, "large adult"),
    CattleProxyPoint(1.80, 740.0, 1.50, "very large"),
)


def estimate_cattle_weight_kg(
    area_m2: float,
    height_m: float | None = None,
) -> dict[str, Any]:
    """
    Interpolate the cattle table by area_m2; optionally blend with height when present.

    Returns dict with weight_kg, method, disclaimer, and table anchors used.
    """
    if area_m2 <= 0:
        return {
            "weight_kg": None,
            "method": PROXY_METHOD,
            "disclaimer": PROXY_DISCLAIMER,
            "species": "cattle",
            "research_proxy": True,
        }

    table = CATTLE_AREA_WEIGHT_TABLE
    if area_m2 <= table[0].area_m2:
        w = table[0].weight_kg * (area_m2 / table[0].area_m2)
        lo, hi = table[0], table[0]
    elif area_m2 >= table[-1].area_m2:
        # Extrapolate gently beyond last anchor
        a0, a1 = table[-2], table[-1]
        slope = (a1.weight_kg - a0.weight_kg) / (a1.area_m2 - a0.area_m2)
        w = a1.weight_kg + slope * (area_m2 - a1.area_m2)
        lo, hi = a0, a1
    else:
        lo = table[0]
        hi = table[-1]
        for i in range(len(table) - 1):
            if table[i].area_m2 <= area_m2 <= table[i + 1].area_m2:
                lo, hi = table[i], table[i + 1]
                break
        t = (area_m2 - lo.area_m2) / max(hi.area_m2 - lo.area_m2, 1e-9)
        w = lo.weight_kg + t * (hi.weight_kg - lo.weight_kg)

    # Optional height blend (30% weight) when both table and observation have height
    if height_m is not None and height_m > 0 and lo.height_m and hi.height_m:
        t_h = 0.0
        if hi.height_m != lo.height_m:
            t_h = (height_m - lo.height_m) / (hi.height_m - lo.height_m)
            t_h = max(0.0, min(1.0, t_h))
        w_h = lo.weight_kg + t_h * (hi.weight_kg - lo.weight_kg)
        w = 0.7 * w + 0.3 * w_h

    return {
        "weight_kg": round(max(0.0, w), 1),
        "method": PROXY_METHOD,
        "disclaimer": PROXY_DISCLAIMER,
        "species": "cattle",
        "research_proxy": True,
        "anchors": {
            "lo_area_m2": lo.area_m2,
            "hi_area_m2": hi.area_m2,
            "lo_kg": lo.weight_kg,
            "hi_kg": hi.weight_kg,
        },
    }
