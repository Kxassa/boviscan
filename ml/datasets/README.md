# Dataset layout conventions

```
ml/datasets/
  raw/                 # immutable captures (gitignored large files)
    <site>/<yyyy-mm-dd>/
      frames/          # images or video shards
      annotations/     # boxes / tracks / scale readings
  interim/             # cleaned joins
  processed/           # train/val/test splits
    cattle/
    pig/
  manifests/
    dataset_card.yaml  # provenance, license, PII notes
```

## Required annotation fields (minimum)

- `species`, `bbox` or mask, optional `scale_weight_kg` (ground truth from physical scale)
- `camera_height_m`, `calibration_id`, capture timestamp

Do not publish farm-identifying GPS without consent. Keep raw weights out of public forks.
