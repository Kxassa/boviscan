# Model card — BoviScan

> Fill with **measured** results only. Leave sections blank rather than inventing numbers.
> Use `python ml/eval/eval_proxy_mae.py <csv>` and copy the printed MAE into the table below.

## Model details

- Name / version: cattle research proxy table `cattle_area_height_table_v0` (YAML-configurable)
- Task: body-size proxy → weight (kg); detection still mock/CPU until HEF
- Architecture: piecewise area (± height) interpolation — see `ml/calibration/cattle_proxy.yaml`
- Framework + export targets (ONNX / HEF): not yet (see `ml/notes/hailo_hef_export.md`)
- Intended hardware: Raspberry Pi 5 + Hailo-8 (~26 TOPS) / CPU fallback

## Intended use

- Estimate approximate live weight from a fixed overhead camera (~3 m)
- Species: cattle (sheep/goat placeholders in `ml/datasets/`)
- Out of scope: certified trade / veterinary diagnosis

## Training data

- Sources / farms: _(fill after consented collection)_
- Species mix: cattle primary
- License / consent: _(fill)_
- Camera height & FOV distribution: target 3.0 m / ~66° Cam Module 3

## Evaluation

How to fill:

1. Build a CSV with columns `scale_kg` and `proxy_kg` (or `area_m2` + `--area-col`).
2. Run `python ml/eval/eval_proxy_mae.py path/to.csv`.
3. Copy the printed `MAE_kg` and `n` into this table. Leave blank until then.

| Split | n | MAE (kg) | MAPE | Notes |
|-------|---|----------|------|-------|
| holdout |  |  |  |  |
| sample_proxy_vs_scale.csv (wiring only) |  |  |  | Do not treat sample CSV as field performance |

## Ethical / farm considerations

- Animal welfare during capture
- Data retention on edge vs Firestore (`boviscan-c2430`)

## Caveats

- Visual weight requires species-specific calibration
- Early versions use body-size proxies only; labeled **research_proxy** in API/UI
