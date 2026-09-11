# Product: livestock-weight

**livestock-weight** estimates livestock body weight from a fixed overhead camera—no physical scale required. It targets farms that need rough weight trends and session events for cattle, pigs, and similar stock. The field device runs offline-first on a Raspberry Pi 5; weighing sessions and device health sync to Google Cloud Firestore when connectivity is available.

## Problem

Physical scales are expensive, slow throughput, and stress animals. Farmers often need approximate weight for feed planning, sale timing, and health monitoring without moving animals onto a platform.

## Solution

A fixed camera (~3 m above ground) captures animals as they pass through a known area. On-device vision estimates body size proxies, applies species-specific calibration, and emits weight events to a local companion API (SQLite queue). When online, the edge syncs sessions and health to **Firestore**. Farmers use a local/companion web UI.

## Locale (v1)

- **Farmer-facing UI and prompts ship in pt-BR only** (Brazilian Portuguese).
- English/Spanish message files may exist as optional stubs for engineering; they are not a v1 product commitment.

## Scope (v0 / early)

| In scope | Out of scope (for now) |
|----------|------------------------|
| Fixed-camera capture on Pi 5 + Cam Module 3 | Mobile phone / handheld weighing |
| Detect → track → size proxy → weight event | Guaranteed veterinary-grade accuracy |
| Local SQLite companion API + sync queue | Cloud-required operation (offline must work) |
| Firestore sync stubs (sessions + device health) | Invented credentials or hardcoded secrets |
| Firebase Auth integration hooks | Full multi-tenant admin console |
| Web UI default locale **pt-BR** | Shipping en/es as first-class farmer languages |
| Mock / CPU backends (no Hailo required for dev) | Fabricated accuracy claims |

## Accuracy posture

Visual weight estimation is **research-stage**. Early versions use body-size proxies (e.g. projected area, length/width ratios) with species-specific calibration tables. **Do not claim kg-level clinical accuracy.** Field validation and per-herd calibration are required before production trust.

## Primary users

- Farmers and ranch hands (field UX in **pt-BR**)
- On-farm technicians (install, calibrate, maintain Pi)
- Vector Trends engineers (pipeline, models, companion apps, cloud sync)

## Hardware target

- Raspberry Pi 5 (8 GB RAM), ≥128 GB storage
- Hailo-8 HAT (~26 TOPS) for accelerated inference when available
- Raspberry Pi Camera Module 3, mounted ~3 m above ground

## Cloud (Google)

- **Firestore** — weighing sessions, device health documents
- **Firebase Auth** — user authentication for companion/cloud access
- Edge remains authoritative while offline; sync is eventual

## Product name

Use **livestock-weight** consistently in repos, packages, and docs.

## Working name

**BoviScan** — Firebase project `boviscan-c2430`.
