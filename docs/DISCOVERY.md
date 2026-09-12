# Multi-device LAN discovery (BoviScan)

Discover edge devices on the farm LAN so the companion API / web UI can list them.

## Options

### 1. UDP beacon (implemented)

- Device broadcasts a small JSON payload to **UDP port 45454** (configurable via `LW_DISCOVERY_PORT`).
- Payload includes `device_id`, `host`, `api_base`, `version`, and a health snippet.
- Device also **HTTP POSTs** the same payload to companion `POST /devices/beacon` when `api_base` is known (reliable for mock/same-host demos without a UDP listener).
- Companion stores devices in SQLite (`/devices` registry) with `last_seen`.

Enable/disable: `LW_DISCOVERY_BEACON=true` (default on in the device CLI). Interval: `LW_DISCOVERY_INTERVAL_S` (default 5s).

### 2. mDNS / DNS-SD (documented, not required)

Advertise `_boviscan._tcp.local` with TXT records (`device_id`, `version`, `path=/health`).

Pros: zero config on many home/farm routers; OS browsers can browse services.  
Cons: needs `zeroconf` (or Avahi) on the Pi; some enterprise Wi‑Fi isolate clients.

If mDNS is needed later, add an optional dependency and announce alongside the UDP beacon; keep the `/devices` registry as the source of truth for the web UI.

## API

| Method | Path | Role |
|--------|------|------|
| `GET` | `/devices` | List known devices + last_seen + health snippet |
| `GET` | `/devices/{id}` | Single device |
| `POST` | `/devices/register` | Manual / ops registration |
| `POST` | `/devices/beacon` | Ingest beacon payload (UDP HTTP fallback) |

Mock mode: API **auto-registers** `device-local-01` on startup (`LW_MOCK_REGISTER_DEVICE=true` by default). Heartbeats to `PUT /status` also upsert the registry.

## Web

pt-BR **Dispositivos** page lists registry entries (online, backend, last seen).
