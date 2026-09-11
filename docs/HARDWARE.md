# Hardware: livestock-weight field device

## Bill of materials (BOM)

| Item | Spec | Notes |
|------|------|-------|
| Compute | Raspberry Pi 5, 8 GB RAM | Official power supply recommended |
| Storage | 128 GB+ microSD or NVMe (HAT-dependent) | Prefer industrial/high-endurance cards |
| Accelerator | Hailo-8 HAT (~26 TOPS) | Not PFLOPS; optional for mock/CPU mode |
| Camera | Raspberry Pi Camera Module 3 | CSI; libcamera / picamera2 |
| Mount | Fixed overhead mount ~3.0 m AGL | Rigid, vibration-minimized |
| Enclosure | Outdoor-rated as needed | Ventilation for Pi + Hailo thermal load |
| Network | Optional Ethernet/Wi‑Fi | Offline-first; LAN for companion UI; WAN for Firestore sync |

## Camera mount

- **Default height:** 3.0 m above ground plane
- Point camera downward (nadir or slight tilt); document tilt in calibration
- Ensure FOV covers the animal passage lane without excessive occlusion
- Avoid strong backlight and specular wet-floor reflections when possible

## Hailo-8 notes

- Peak performance class: ~26 TOPS (INT8-class NPU), **not** PFLOPS
- Models must be compiled to Hailo Executable Format (HEF) offline
- Device software includes a Hailo backend **stub**; CPU/mock backends run without hardware
- See `ml/notes/hailo_hef_export.md` for the documented export path (no binaries in-repo)

## Calibration checklist

Use before trusting weight events:

1. [ ] Confirm camera height with tape/laser; set `camera.height_m` (default `3.0`)
2. [ ] Measure / confirm horizontal FOV or use datasheet + lens; set `camera.fov_horizontal_deg`
3. [ ] Place a reference object of known size on the ground plane in view; record dimensions
4. [ ] Capture ground-plane homography / scale factors (see device calibration module)
5. [ ] Select species profile and load calibration curve / table (placeholder in v0)
6. [ ] Run health checks: camera open, inference backend ready, disk/temp OK
7. [ ] Walk a known animal or dummy through the lane; compare proxy output to expected range
8. [ ] Document date, operator, and config snapshot on device

## Thermal / power

- Hailo + Pi 5 under continuous inference can run warm; ensure airflow
- Use official 27 W USB-C PSU for Pi 5; verify HAT power requirements separately

## Bring-up pointers

See `device/README.md` for Pi OS, camera enablement, and laptop mock mode.
