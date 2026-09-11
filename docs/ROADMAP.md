# Roadmap: livestock-weight

Phased plan. Accuracy claims only after validated field studies. Farmer UI: **pt-BR only** for v1.

## Phase 0 — Greenfield skeleton (current)

- [x] Monorepo layout: docs, device, api, apps/web, ml, ops
- [x] Mock camera + mock/CPU inference backends
- [x] Pipeline interfaces: frame → detect → track → estimate → event
- [x] Local FastAPI + SQLite + sync outbox
- [x] Firestore sync **stubs** (no credentials in-repo)
- [x] Web skeleton; default locale **pt-BR**
- [x] Docker Compose + CI smoke for mocks

## Phase 1 — Field bring-up

- [ ] Pi 5 + Cam Module 3 capture verified with picamera2
- [ ] Calibration UX / checklist (height 3 m, FOV, reference object) in pt-BR
- [ ] Persistent event buffer + outbox retry
- [ ] Basic detection model on CPU; optional Hailo HEF when available
- [ ] Firebase Auth wired for companion login

## Phase 2 — Cloud sync + species calibration

- [ ] Production Firestore sync for sessions + device health
- [ ] Collect labeled datasets per species (see `ml/datasets/`)
- [ ] Body-size proxy → weight curves with holdout eval
- [ ] MODEL_CARD.md filled with real metrics (no fabrication)

## Phase 3 — Hailo acceleration

- [ ] Export detection/pose/proxy models to HEF (documented path)
- [ ] Production Hailo backend replacing stub
- [ ] Thermal/power soak tests on enclosed Pi 5 + HAT

## Phase 4 — Product hardening

- [ ] Multi-device LAN discovery
- [ ] Export reports (CSV) for farm records
- [ ] OTA update channel (signed)
- [ ] Optional additional locales (only after pt-BR is solid)

## Explicit non-goals (near term)

- Claiming veterinary or trade-settlement accuracy
- Requiring cloud connectivity for weighing
- Shipping en/es as farmer-facing languages in v1
- Committing cloud credentials
