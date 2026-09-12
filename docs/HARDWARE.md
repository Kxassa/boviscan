# Hardware: BoviScan field device

Engineer docs (EN). Farmer-facing UI remains **pt-BR**.

## Bill of materials (BOM)

| Item | Spec | Notes |
|------|------|-------|
| Compute | Raspberry Pi 5, 8 GB RAM | Official 27 W USB-C PSU |
| Storage | 128 GB+ microSD or NVMe | Prefer industrial / high-endurance |
| Accelerator | Hailo-8 HAT (~26 TOPS) | Not PFLOPS; optional for mock/CPU mode |
| Camera | Raspberry Pi Camera Module 3 | CSI; libcamera / picamera2 |
| Mount | Fixed overhead ~3.0 m AGL | Rigid, low vibration |
| Enclosure | Outdoor-rated as needed | Airflow for Pi + Hailo thermal load |
| Network | Optional Ethernet/Wi‑Fi | Offline-first; LAN UI; WAN → Firestore |

## Step-by-step bring-up (Pi 5 + Cam Module 3)

Canonical checklist script:

```bash
./ops/scripts/pi_bringup.sh
# or: ./device/scripts/pi_bringup.sh
```

### 1. OS

1. Flash **Raspberry Pi OS (64-bit)** Bookworm (or later) to ≥128 GB media.
2. First boot: set locale/timezone, enable SSH if needed.
3. `sudo apt update && sudo apt full-upgrade -y && sudo reboot`

### 2. Camera Module 3

1. Power off; seat the CSI cable firmly (Cam Module 3 → CAM port on Pi 5).
2. Boot; confirm: `libcamera-hello -t 3000` (or `rpicam-hello`).
3. Python: `sudo apt install -y python3-picamera2` **or** `pip install -e '.[pi]'` in the device venv.
4. Capture smoke:

```bash
cd device && source .venv/bin/activate
python scripts/capture_smoke.py --out /tmp/boviscan-still.jpg
# On laptop without CSI: adds --force-mock (or auto-falls back to MockCamera)
```

### 3. Storage layout (128 GB)

Suggested:

| Path | Role |
|------|------|
| `/` | OS + apt packages |
| `/var/lib/boviscan` | SQLite DB, outbox spool, small captures |
| `/mnt/data` (optional NVMe) | Raw frames / datasets (`ml/datasets/.../images`) |

Keep ≥20% free. Point `LW_API_DB_PATH` at `/var/lib/boviscan/companion.db` on the edge companion if co-located.

### 4. Hailo-8 HAT (optional)

1. Install HAT per vendor instructions; reboot.
2. Expect `/dev/hailo0` (or similar) when the driver is loaded.
3. Install HailoRT; `hailortcli fw-control identify`.
4. Until a HEF is deployed, set `inference.backend: cpu_mock` (or `hailo` which **stubs** to CPU — see `device/.../hailo_stub.py`).
5. HEF export path: `ml/notes/hailo_hef_export.md`.

### 5. Device software

```bash
cd device
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[pi,dev]"
cp config/device.example.yaml /etc/livestock-weight/device.yaml
# Edit: camera.backend: picamera2, camera.height_m: 3.0
livestock-weight-health
livestock-weight-device --steps 10
```

### 6. Thermal / power

- Pi 5 + Hailo under continuous inference runs warm — use enclosure vents / small fan.
- Official **27 W** PSU; confirm HAT current draw separately.
- Monitor: `cat /sys/class/thermal/thermal_zone0/temp` (millidegrees) and `vcgencmd get_throttled` (`0x0` = good).
- If throttled under load, improve airflow before trusting long sessions.

## Camera mount & calibration

- **Default height:** 3.0 m above ground plane  
- Nadir or slight tilt; document tilt in calibration  
- FOV covers the passage lane; avoid strong backlight  
- Web checklist (pt-BR): apps/web → Calibração  
- Full checklist also in `ops/scripts/pi_bringup.sh` step 7

## Hailo-8 notes

- ~26 TOPS INT8-class NPU — **not** PFLOPS  
- Models compiled offline to HEF  
- Device includes Hailo backend **stub**; CPU/mock run without hardware  

## Resumo pt-BR (instalação física)

1. Fixe a câmera a **~3,0 m** do chão, olhando para baixo na passagem.  
2. Use fonte oficial do Pi 5; deixe ventilação no gabinete (Pi + Hailo esquentam).  
3. Cartão/NVMe ≥128 GB; reserve espaço para banco e imagens.  
4. No Pi, rode `./ops/scripts/pi_bringup.sh` e `python device/scripts/capture_smoke.py`.  
5. Ajuste altura/FOV na checklist **Calibração** do app (português).  
6. Sem Hailo, o modo `cpu_mock` funciona; peso exibido é **proxy de pesquisa**.
