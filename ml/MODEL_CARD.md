# Model card template — livestock-weight

> Fill with **measured** results only. Leave sections blank rather than inventing numbers.

## Model details

- Name / version:
- Task: livestock detection / body-size proxy / weight regression (specify)
- Architecture:
- Framework + export targets (ONNX / HEF):
- Intended hardware: Raspberry Pi 5 + Hailo-8 (~26 TOPS) / CPU fallback

## Intended use

- Estimate approximate live weight from a fixed overhead camera (~3 m)
- Species:
- Out of scope: certified trade / veterinary diagnosis

## Training data

- Sources / farms:
- Species mix:
- License / consent:
- Camera height & FOV distribution:

## Evaluation

| Split | n | MAE (kg) | MAPE | Notes |
|-------|---|----------|------|-------|
| holdout |  |  |  |  |

## Ethical / farm considerations

- Animal welfare during capture
- Data retention on edge vs Firestore

## Caveats

- Visual weight requires species-specific calibration
- Early versions may use body-size proxies only
