# OTA updates (BoviScan edge / Pi)

Signed update channel design + **stubs**. No production keys live in this repo.

## Goals

- Deliver device software (pipeline wheel/deb, config templates, optional HEF pointers) to Raspberry Pi 5 units over LAN or HTTPS.
- **Verify** integrity and authenticity before apply.
- Support **rollback** to the previous known-good slot.
- Fail closed: without a configured manifest URL / public key, the device **no-ops** (see `device/.../ota/client.py`).

## High-level flow

```
ops builds artifact → signs manifest (ed25519 or sigstore-style) → publishes
device: check-for-update → fetch manifest → verify signature → download → verify hash
→ apply to inactive A/B slot → reboot into new slot → health gate → mark good / rollback
```

## Manifest (example schema)

See `ops/ota/manifest.schema.json` and `ops/ota/example-manifest.json`.

Required conceptual fields:

| Field | Purpose |
|-------|---------|
| `schema_version` | Manifest format version |
| `product` | `boviscan` |
| `version` | Semver of the release |
| `channel` | `stable` / `beta` / `dev` |
| `created_at` | ISO-8601 UTC |
| `artifacts[]` | `name`, `url`, `sha256`, `size` |
| `min_device_version` | Refuse downgrade / incompatible jumps |
| `rollback` | Previous version id / slot hint |
| `signatures[]` | `alg` (`ed25519` or `sigstore`), `key_id`, `sig` (base64) |

**No real private keys** are committed. Ops example uses placeholder `sig` / `key_id` strings.

## Signing concepts

### Option A — ed25519 detached signature

1. Build release tarball / package; compute SHA-256 of each artifact.
2. Canonicalize JSON manifest (JCS or sorted keys, UTF-8, no insignificant whitespace).
3. Sign canonical bytes with ed25519 **offline** key (HSM or ops laptop).
4. Publish manifest + artifacts to HTTPS (or LAN mirror).
5. Device holds only the **public** key (or keyring by `key_id`).

### Option B — sigstore-style

1. Sign with ephemeral key; record identity (OIDC email / SPIFFE) in Rekor transparency log.
2. Device verifies via sigstore policy (allowed identity + repo).
3. Heavier on the Pi; useful when ed25519 key distribution is painful.

v1 recommendation: **ed25519** + A/B rootfs or two install directories (`/opt/boviscan/current` → symlink).

## Device interfaces (stubs)

```python
from livestock_weight_device.ota import check_for_update, apply_update

status = check_for_update()   # no-op if LW_OTA_MANIFEST_URL unset
apply_update()                # refuses without verified signed manifest
```

Env:

| Variable | Meaning |
|----------|---------|
| `LW_OTA_MANIFEST_URL` | HTTPS URL of signed manifest (optional) |
| `LW_OTA_PUBLIC_KEY` | Path to ed25519 public key (optional) |
| `LW_OTA_CHECK` | If true, CLI prints stub check on start |

## Rollback

1. Keep previous slot (`previous` symlink or inactive partition).
2. After apply, boot new slot; run health probe (camera open, API heartbeat, inference backend load).
3. On failure or missing “mark-good” within N minutes → reboot into previous slot.
4. Manifest `rollback.version` documents the expected previous version for operators.

## Non-goals (near term)

- Auto-downloading unsigned HEF models from arbitrary URLs
- Committing signing private keys or production certs
- Claiming field-proven OTA reliability before soak on real Pi hardware
