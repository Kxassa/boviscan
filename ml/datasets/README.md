# Dataset layout — BoviScan

```
ml/datasets/
  cattle/
    labels.csv           # schema below (sample rows are synthetic placeholders)
    manifests/
      dataset_card.yaml
    images/              # gitignored large files — put captures here locally
  sheep/                 # placeholder species
    labels.csv           # header only until data exists
    README.md
  goat/                  # placeholder species
    labels.csv
    README.md
  raw/                   # immutable captures (gitignored)
  interim/
  processed/
```

## CSV schema (all species)

| Column | Type | Notes |
|--------|------|-------|
| `image_id` | string | Stable id; matches `images/{image_id}.jpg` when present |
| `scale_kg` | float | Ground-truth live weight from physical scale |
| `bbox` | string | `x1,y1,x2,y2` in pixels (axis-aligned) |
| `date` | string | ISO date `YYYY-MM-DD` |
| `farm_id` | string | Pseudonymous farm id (consent required) |

Optional future columns: `species`, `camera_height_m`, `calibration_id`, `track_id`, `proxy_kg`.

Do not publish farm-identifying GPS without consent. Keep raw weights out of public forks when farms request it.
