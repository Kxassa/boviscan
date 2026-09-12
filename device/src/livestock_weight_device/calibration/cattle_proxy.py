"""
Cattle weight proxy (RESEARCH / HEURISTIC — not validated for trade or veterinary use).

Maps projected ground-plane area (m²) and optional withers-height proxy (m) to
approximate live weight in kg using a configurable piecewise table (YAML).
Default table ships in-repo; override via CATTLE_PROXY_YAML or load_cattle_proxy_table().

Label every estimate as a research proxy in product UI and API payloads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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


# Built-in fallback (same anchors as ml/calibration/cattle_proxy.yaml)
_DEFAULT_TABLE: tuple[CattleProxyPoint, ...] = (
    CattleProxyPoint(0.40, 180.0, 0.95, "calf / small"),
    CattleProxyPoint(0.60, 260.0, 1.05, "yearling light"),
    CattleProxyPoint(0.80, 340.0, 1.15, "yearling"),
    CattleProxyPoint(1.00, 420.0, 1.25, "adult light"),
    CattleProxyPoint(1.20, 500.0, 1.35, "adult medium"),
    CattleProxyPoint(1.40, 580.0, 1.40, "adult heavy"),
    CattleProxyPoint(1.60, 660.0, 1.45, "large adult"),
    CattleProxyPoint(1.80, 740.0, 1.50, "very large"),
)

CATTLE_AREA_WEIGHT_TABLE = _DEFAULT_TABLE  # backwards-compatible alias


def _default_yaml_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    # device/src/.../calibration → device/config, repo ml/calibration
    device_root = here.parents[3]  # device/
    repo_root = here.parents[4]  # repo
    return [
        Path(os.environ["CATTLE_PROXY_YAML"]) if os.environ.get("CATTLE_PROXY_YAML") else None,
        device_root / "config" / "cattle_proxy.yaml",
        repo_root / "ml" / "calibration" / "cattle_proxy.yaml",
        Path.cwd() / "ml" / "calibration" / "cattle_proxy.yaml",
        Path.cwd() / "device" / "config" / "cattle_proxy.yaml",
    ]


def load_cattle_proxy_table(path: str | Path | None = None) -> tuple[CattleProxyPoint, ...]:
    """Load anchors from YAML; fall back to built-in table if missing/unreadable."""
    candidates: list[Path] = []
    if path is not None:
        candidates.append(Path(path))
    candidates.extend(p for p in _default_yaml_candidates() if p is not None)

    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            import yaml

            data = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            anchors = data.get("anchors") or []
            points: list[CattleProxyPoint] = []
            for a in anchors:
                points.append(
                    CattleProxyPoint(
                        area_m2=float(a["area_m2"]),
                        weight_kg=float(a["weight_kg"]),
                        height_m=float(a["height_m"]) if a.get("height_m") is not None else None,
                        note=str(a.get("note") or ""),
                    )
                )
            if points:
                points.sort(key=lambda p: p.area_m2)
                return tuple(points)
        except Exception:
            continue
    return _DEFAULT_TABLE


@lru_cache(maxsize=4)
def _cached_table(path_key: str) -> tuple[CattleProxyPoint, ...]:
    return load_cattle_proxy_table(path_key or None)


def get_cattle_table(yaml_path: str | None = None) -> tuple[CattleProxyPoint, ...]:
    key = yaml_path or os.environ.get("CATTLE_PROXY_YAML") or ""
    return _cached_table(key)


def height_blend_fraction(yaml_path: str | None = None) -> float:
    path = yaml_path or os.environ.get("CATTLE_PROXY_YAML")
    candidates = [Path(path)] if path else []
    candidates.extend(p for p in _default_yaml_candidates() if p is not None)
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            import yaml

            data = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            return float(data.get("height_blend", 0.3))
        except Exception:
            continue
    return 0.3


def estimate_cattle_weight_kg(
    area_m2: float,
    height_m: float | None = None,
    *,
    yaml_path: str | None = None,
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

    table = get_cattle_table(yaml_path)
    blend = height_blend_fraction(yaml_path)

    if area_m2 <= table[0].area_m2:
        w = table[0].weight_kg * (area_m2 / table[0].area_m2)
        lo, hi = table[0], table[0]
    elif area_m2 >= table[-1].area_m2:
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

    if height_m is not None and height_m > 0 and lo.height_m and hi.height_m:
        t_h = 0.0
        if hi.height_m != lo.height_m:
            t_h = (height_m - lo.height_m) / (hi.height_m - lo.height_m)
            t_h = max(0.0, min(1.0, t_h))
        w_h = lo.weight_kg + t_h * (hi.weight_kg - lo.weight_kg)
        w = (1.0 - blend) * w + blend * w_h

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
