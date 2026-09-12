# Roadmap: BoviScan

Phased plan. Accuracy claims only after validated field studies. Farmer UI: **pt-BR only** for v1.

## Phase 0 — Greenfield skeleton

- [x] Monorepo layout: docs, device, api, apps/web, ml, ops
- [x] Mock camera + mock/CPU inference backends
- [x] Pipeline interfaces: frame → detect → track → estimate → event
- [x] Local FastAPI + SQLite + sync outbox
- [x] Firestore sync **stubs** (no credentials in-repo)
- [x] Web skeleton; default locale **pt-BR**
- [x] Docker Compose + CI smoke for mocks

## Phase 1 — Field bring-up + mock E2E

- [x] Device pipeline POSTs weight events to companion API (configurable base URL)
- [x] Cattle calibration table (height/area → kg) labeled heuristic/research proxy
- [x] Simple track IDs across frames (one animal ≈ one session estimate)
- [x] Session lifecycle API: start / stop / list / get + CSV export
- [x] Outbox retry for Firestore; clear disabled / stub / firestore modes
- [x] GOOGLE_CLOUD_PROJECT / FIREBASE_PROJECT_ID default examples `boviscan-c2430`
- [x] Web weighing console (pt-BR): start session, live API feed, history, device status
- [x] Calibration checklist page (3 m height, FOV, reference object) in pt-BR
- [x] `ops/scripts/run_demo.sh` mock E2E
- [x] Smoke tests for sessions + pipeline→API posting
- [x] Pi bring-up script + HARDWARE.md step-by-step + capture smoke (mock fallback)
- [x] CPU detection improved (motion/blob; optional OpenCV); Hailo stub retained
- [x] Firebase Auth wired for companion login (optional via env + pt-BR login screen)
- [ ] Pi 5 + Cam Module 3 capture verified on real hardware (field)

## Phase 2 — Cloud sync + species calibration (in progress)

- [x] Firestore sync hardened: backoff retries, richer `/sync/status`, documented collections
- [x] Optional Firestore emulator docker-compose profile
- [x] Integration/dry-run tests proving sync path without real GCP
- [x] Datasets layout cattle + sheep/goat placeholders; CSV schema
- [x] Cattle proxy curves as configurable YAML; research labels kept
- [x] Eval script: proxy vs scale_kg → MAE (MODEL_CARD describes how to fill; no fabricated metrics)
- [x] Docs: Auth + Firestore emulator + Pi bring-up in README
- [ ] Production Firestore soak with real credentials on boviscan-c2430
- [ ] Collect labeled field datasets per species
- [ ] Holdout eval on real scale weights; fill MODEL_CARD with measured MAE only

## Phase 3 — Hailo acceleration

- [ ] Export detection/pose/proxy models to HEF (documented path)
- [ ] Production Hailo backend replacing stub
- [ ] Thermal/power soak tests on enclosed Pi 5 + HAT

## Phase 4 — Product hardening

- [ ] Multi-device LAN discovery
- [ ] OTA update channel (signed)
- [ ] Optional additional locales (only after pt-BR is solid)
- [ ] Richer farm reports beyond CSV

## Explicit non-goals (near term)

- Claiming veterinary or trade-settlement accuracy
- Requiring cloud connectivity for weighing
- Shipping en/es as farmer-facing languages in v1
- Committing cloud credentials
