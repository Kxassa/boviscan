"""Camera height, FOV, ground-plane / reference-object calibration helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .cattle_proxy import PROXY_DISCLAIMER, PROXY_METHOD, estimate_cattle_weight_kg


@dataclass
class ReferenceObject:
    width_m: float
    height_m: float
    width_px: float | None = None
    height_px: float | None = None
    label: str = "reference"


@dataclass
class Calibration:
    camera_height_m: float = 3.0
    fov_horizontal_deg: float = 66.0
    image_width_px: int = 1280
    image_height_px: int = 720
    reference: ReferenceObject | None = None
    ground_plane: dict[str, Any] = field(default_factory=dict)
    species: str = "cattle"
    # Fallback linear map for non-cattle species (NOT validated — research only)
    proxy_scale: float = 400.0
    proxy_bias: float = 50.0

    def meters_per_pixel_at_ground(self) -> float:
        """Approximate ground sampling assuming nadir camera at camera_height_m."""
        fov_rad = math.radians(self.fov_horizontal_deg)
        ground_width_m = 2.0 * self.camera_height_m * math.tan(fov_rad / 2.0)
        return ground_width_m / max(self.image_width_px, 1)

    def bbox_to_ground_size(self, x1: float, y1: float, x2: float, y2: float) -> dict[str, float]:
        mpp = self.meters_per_pixel_at_ground()
        length_m = abs(x2 - x1) * mpp
        width_m = abs(y2 - y1) * mpp
        area_m2 = length_m * width_m
        # Rough withers-height proxy from bbox height at known camera height (heuristic)
        height_proxy_m = width_m  # bbox vertical extent on ground plane as stand-in
        return {
            "length_m": length_m,
            "width_m": width_m,
            "area_m2": area_m2,
            "height_proxy_m": height_proxy_m,
            "mpp": mpp,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        }

    def estimate_weight_kg(
        self, area_m2: float, height_m: float | None = None
    ) -> tuple[float | None, dict[str, Any]]:
        """
        Species-aware size→kg proxy.

        Cattle uses the labeled research table in cattle_proxy.
        Other species fall back to a linear placeholder.
        Returns (weight_kg, proxy_meta).
        """
        if area_m2 <= 0:
            return None, {
                "method": "none",
                "research_proxy": True,
                "disclaimer": PROXY_DISCLAIMER,
            }

        if self.species == "cattle":
            result = estimate_cattle_weight_kg(area_m2, height_m=height_m)
            return result["weight_kg"], result

        # Generic linear fallback — clearly marked research
        w = max(0.0, self.proxy_scale * area_m2 + self.proxy_bias)
        return round(w, 1), {
            "weight_kg": round(w, 1),
            "method": "linear_fallback_v0",
            "disclaimer": PROXY_DISCLAIMER,
            "species": self.species,
            "research_proxy": True,
            "proxy_scale": self.proxy_scale,
            "proxy_bias": self.proxy_bias,
        }

    def with_reference_pixels(self, width_px: float, height_px: float) -> Calibration:
        if self.reference is None:
            return self
        self.reference.width_px = width_px
        self.reference.height_px = height_px
        if width_px > 0:
            mpp = self.reference.width_m / width_px
            self.ground_plane["meters_per_pixel_ref"] = mpp
        return self


def default_calibration(
    height_m: float = 3.0,
    fov_horizontal_deg: float = 66.0,
    width: int = 1280,
    height: int = 720,
    species: str = "cattle",
) -> Calibration:
    return Calibration(
        camera_height_m=height_m,
        fov_horizontal_deg=fov_horizontal_deg,
        image_width_px=width,
        image_height_px=height,
        species=species,
        reference=ReferenceObject(width_m=1.0, height_m=0.2, label="ground_bar_1m"),
    )


__all__ = [
    "ReferenceObject",
    "Calibration",
    "default_calibration",
    "PROXY_METHOD",
    "PROXY_DISCLAIMER",
]
