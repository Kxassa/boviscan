# Hailo HEF export path (documentation only)

No HEF binaries are stored in this repository.

## Overview

1. Train / obtain a model in a supported framework (e.g. ONNX from PyTorch).
2. Use the **Hailo Dataflow Compiler** (Hailo SW suite) on a supported x86 workstation:
   - Parse → optimize (with calibration set) → compile → **HEF**
3. Copy the HEF to the Pi (e.g. `/opt/livestock-weight/models/detect.hef`).
4. Point `inference.model_path` at the HEF and set `inference.backend: hailo`.
5. Runtime uses HailoRT on the Pi 5 + Hailo-8 HAT (~26 TOPS).

## Notes

- Quantization calibration images should match farm lighting and camera height (~3 m).
- Keep CPU/mock backends for CI and laptops without the HAT.
- The in-repo `HailoBackend` is a **stub** until HailoRT is wired.

## References

- Hailo developer documentation for Dataflow Compiler and HailoRT (external).
