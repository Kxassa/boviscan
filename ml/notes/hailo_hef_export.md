# Hailo HEF export checklist (BoviScan)

No HEF, ONNX, or proprietary Hailo binaries are stored in this repository.
Use a licensed **Hailo AI Software Suite** workstation (x86_64) with the
**Dataflow Compiler (DFC)**. On-device runtime is **HailoRT** on Pi 5 + Hailo-8 HAT (~26 TOPS).

See also: `ml/export/export_hef_placeholder.sh` (documents CLI invocations only).

---

## 0. Prerequisites

| Item | Notes |
|------|--------|
| Model | Detection (preferred) or pose/proxy head exported to **ONNX** |
| Hailo DFC | Matching HailoSW / firmware major version for target Hailo-8 |
| Calibration set | 64–256 farm frames at ~**3.0 m** AGL, typical lighting |
| Target device | Pi 5 + Hailo-8 HAT; PCIe interface |
| Edge config | `inference.backend: hailo`, `inference.hef_path: /opt/.../detect.hef` |

---

## 1. ONNX → Hailo Dataflow Compiler → HEF

Practical sequence (exact flags depend on DFC version — check vendor docs):

1. **Export ONNX** from your training stack (opset commonly 11–17; avoid exotic ops).
   - Detection input NCHW or NHWC as required by export; BoviScan edge defaults to **640×640×3** uint8 after preprocess.
2. **Parse** the ONNX into a Hailo HAR / intermediate graph:
   ```bash
   # Illustrative — adjust to your installed hailo CLI
   hailo parser onnx model.onnx --har-path model.har
   ```
3. **Optimize / quantize** with a calibration set (INT8 typical for Hailo-8):
   ```bash
   hailo optimize model.har \
     --calib-set-path ./calib_images \
     --optimized-har-path model_optimized.har
   ```
4. **Compile** to HEF for Hailo-8:
   ```bash
   hailo compiler model_optimized.har \
     --hw-arch hailo8 \
     --hef-path detect.hef
   ```
5. **Copy HEF to the Pi** (never commit):
   ```bash
   scp detect.hef pi@device:/opt/livestock-weight/models/detect.hef
   ```
6. **Point device config** at the HEF (`device.example.yaml` fields):
   ```yaml
   inference:
     backend: hailo
     hef_path: /opt/livestock-weight/models/detect.hef
     batch: 1
     input_size: [640, 640, 3]
     postprocess: yolo_nms   # or passthrough if NMS is on-chip / external
     fallback_to_cpu: true
   ```
7. **Verify** on device: `hailortcli fw-control identify`, then
   `LW_INFERENCE_BACKEND=hailo livestock-weight-device --steps 5` or
   `./ops/scripts/soak_device.sh 50 hailo`.

---

## 2. Quantization notes

- Prefer **INT8** quantization for throughput/thermals on Hailo-8.
- Calibration images **must** match deployment: Camera Module 3, ~3 m height, farm lighting (dawn/noon/dusk if possible).
- Include empty pens and partial animals so the detector does not overfit bright blobs.
- After compile, compare a small **CPU ONNX vs HEF** box set on the same frames (IoU / score drift) — record measured deltas in MODEL_CARD only when you have them; **do not invent metrics**.
- If accuracy collapses post-quant, try mixed precision / layer exclusions per DFC guides (vendor-specific).

---

## 3. Expected input tensor shapes (detection)

| Stage | Shape | Dtype | Notes |
|-------|-------|-------|-------|
| Camera frame (edge) | `H×W×3` (e.g. 720×1280×3) | uint8 RGB | From picamera2 / mock |
| Hailo preprocess (BoviScan) | `N×640×640×3` (NHWC) | uint8 | `inference.input_size`; `batch` → N |
| Typical YOLO-style ONNX | `1×3×640×640` (NCHW) float | Often normalized 0–1 or ImageNet mean/std — align export + DFC model script |
| HEF input (compiled) | As reported by `hailortcli parse-hef` / DFC | Often uint8 NHWC after compilation | Confirm with HEF info before wiring postprocess |

**Output / postprocess**

- If the HEF includes integrated NMS / decode, set `postprocess: passthrough` and map SDK output tensors → `Detection` in a custom hook later.
- If raw grids / decoded `[x1,y1,x2,y2,score,cls]` arrays are returned, use `postprocess: yolo_nms` (numpy decoder in `device/.../inference/hailo.py`).
- Confidence threshold: `inference.confidence_threshold` (default 0.4).

Coordinate space: decoder assumes either normalized [0,1] or pixel coords in the **input tensor** size; the pipeline still maps boxes against the original frame size in geometry — when wiring a real HEF, scale boxes from input size → capture size explicitly if they differ.

---

## 4. Runtime fallback (CI / no HAT)

`HailoBackend` loads HEF via HailoRT when SDK + file exist. Otherwise it records clear `load_errors` and, with `fallback_to_cpu: true` (default), delegates to `cpu_mock`. Tests: `device/tests/test_hailo_backend.py`.

---

## 5. References

- Hailo Dataflow Compiler user guide (external / licensed)
- HailoRT + `hailortcli` on Raspberry Pi OS 64-bit
- In-repo: `docs/HARDWARE.md`, `device/config/device.example.yaml`, `ml/export/`
