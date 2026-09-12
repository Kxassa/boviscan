# Evaluation

```bash
# From repo root (device package on PYTHONPATH or installed):
python ml/eval/eval_proxy_mae.py ml/eval/sample_proxy_vs_scale.csv

# Or compute cattle research proxy from area_m2:
python ml/eval/eval_proxy_mae.py ml/eval/sample_proxy_vs_scale.csv --area-col area_m2
```

Prints MAE only. Paste **measured** numbers into `ml/MODEL_CARD.md` — never fabricate.
