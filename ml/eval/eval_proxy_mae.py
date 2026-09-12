#!/usr/bin/env python3
"""
Evaluate proxy_kg vs scale_kg from a CSV and print MAE.

Expected columns (minimum):
  scale_kg, proxy_kg
Optional: image_id

If proxy_kg is missing, you may pass --area-col to compute cattle research proxy
from an area_m2 column (still clearly a research heuristic).

Does NOT write fabricated metrics into MODEL_CARD.md — print only.
Fill MODEL_CARD evaluation table manually from these measured numbers.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path


def mae(pairs: list[tuple[float, float]]) -> float:
    if not pairs:
        return float("nan")
    return sum(abs(a - b) for a, b in pairs) / len(pairs)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Proxy vs scale MAE")
    p.add_argument("csv_path", type=Path, help="CSV with scale_kg and proxy_kg (or area_m2)")
    p.add_argument("--area-col", default=None, help="If set, compute cattle proxy from this column")
    p.add_argument("--yaml", default=None, help="Optional cattle_proxy.yaml path")
    args = p.parse_args(argv)

    if not args.csv_path.is_file():
        print(f"error: file not found: {args.csv_path}", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(args.csv_path.open(encoding="utf-8")))
    pairs: list[tuple[float, float]] = []
    skipped = 0

    estimate = None
    if args.area_col:
        # Prefer package if on path; else minimal inline is not needed — require device pkg
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "device" / "src"))
        from livestock_weight_device.calibration.cattle_proxy import estimate_cattle_weight_kg

        def estimate(area: float) -> float | None:
            r = estimate_cattle_weight_kg(area, yaml_path=args.yaml)
            return r.get("weight_kg")

    for row in rows:
        try:
            scale = float(row["scale_kg"])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        proxy: float | None = None
        if args.area_col:
            try:
                area = float(row[args.area_col])
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue
            assert estimate is not None
            proxy = estimate(area)
        else:
            try:
                proxy = float(row["proxy_kg"])
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue
        if proxy is None or math.isnan(proxy):
            skipped += 1
            continue
        pairs.append((scale, proxy))

    err = mae(pairs)
    print(f"n={len(pairs)} skipped={skipped}")
    print(f"MAE_kg={err:.3f}" if pairs else "MAE_kg=n/a (no pairs)")
    if pairs:
        abs_errs = [abs(a - b) for a, b in pairs]
        print(f"min_abs_err={min(abs_errs):.3f} max_abs_err={max(abs_errs):.3f}")
    print(
        "Note: copy measured MAE into ml/MODEL_CARD.md evaluation table manually. "
        "Do not invent metrics."
    )
    return 0 if pairs else 1


if __name__ == "__main__":
    raise SystemExit(main())
