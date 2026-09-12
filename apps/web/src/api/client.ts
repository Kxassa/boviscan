import { authEnabled } from "../auth/config";
import { getIdToken } from "../auth/session";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type WeightEvent = {
  id: string;
  device_id: string;
  track_id: string;
  timestamp: string;
  species: string;
  estimated_weight_kg: number | null;
  confidence: number;
  proxy_metrics: Record<string, unknown>;
  session_id?: string | null;
  calibration_id?: string | null;
};

export type DeviceStatus = {
  device_id: string;
  online: boolean;
  camera_ok: boolean;
  inference_backend: string | null;
  pipeline_state: string | null;
  last_heartbeat: string;
  version?: string | null;
};

export type WeighingSession = {
  id: string;
  device_id: string;
  started_at: string;
  ended_at: string | null;
  event_count: number;
  notes: string | null;
  sync_state: string;
  status: string;
};

function authHeaders(): HeadersInit {
  const headers: Record<string, string> = {};
  if (authEnabled()) {
    const token = getIdToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${BASE}${path}`, { headers: { ...authHeaders() } });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

async function sendJson<T>(path: string, method: string, body?: unknown): Promise<T | null> {
  try {
    const r = await fetch(`${BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchEvents(sessionId?: string | null): Promise<WeightEvent[]> {
  const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}&limit=100` : "?limit=50";
  return (await getJson<WeightEvent[]>(`/events${q}`)) ?? [];
}

export async function fetchStatus(): Promise<DeviceStatus[]> {
  return (await getJson<DeviceStatus[]>("/status")) ?? [];
}

export async function fetchSessions(): Promise<WeighingSession[]> {
  return (await getJson<WeighingSession[]>("/sessions")) ?? [];
}

export async function startSession(deviceId = "device-local-01"): Promise<WeighingSession | null> {
  return sendJson<WeighingSession>("/sessions/start", "POST", {
    device_id: deviceId,
    notes: "console-web",
  });
}

export async function stopSession(sessionId: string): Promise<WeighingSession | null> {
  return sendJson<WeighingSession>(`/sessions/${sessionId}/stop`, "POST", {});
}

export function sessionCsvUrl(sessionId: string): string {
  return `${BASE}/sessions/${sessionId}/export.csv`;
}

export async function fetchHealth(): Promise<{ ok: boolean; auth_enabled?: boolean } | null> {
  return getJson("/health");
}

export async function fetchAuthStatus(): Promise<{ enabled: boolean } | null> {
  return getJson("/auth/status");
}


export type FarmReport = {
  from_ts: string | null;
  to_ts: string | null;
  species_filter: string | null;
  event_count: number;
  with_weight_count: number;
  avg_kg: number | null;
  min_kg: number | null;
  max_kg: number | null;
  by_species: {
    species: string;
    count: number;
    avg_kg: number | null;
    min_kg: number | null;
    max_kg: number | null;
  }[];
  disclaimer: string;
  research_proxy: boolean;
};

export type KnownDevice = {
  device_id: string;
  display_name: string | null;
  host: string | null;
  port: number | null;
  api_base: string | null;
  version: string | null;
  source: string;
  online: boolean;
  last_seen: string;
  health: Record<string, unknown>;
  registered_at?: string | null;
};

export async function fetchFarmReport(opts: {
  dateFrom?: string;
  dateTo?: string;
  species?: string;
} = {}): Promise<FarmReport | null> {
  const q = new URLSearchParams();
  if (opts.dateFrom) q.set("date_from", opts.dateFrom);
  if (opts.dateTo) q.set("date_to", opts.dateTo);
  if (opts.species) q.set("species", opts.species);
  const qs = q.toString();
  return getJson<FarmReport>(`/reports/farm${qs ? `?${qs}` : ""}`);
}

export function farmReportCsvUrl(opts: {
  dateFrom?: string;
  dateTo?: string;
  species?: string;
} = {}): string {
  const q = new URLSearchParams();
  if (opts.dateFrom) q.set("date_from", opts.dateFrom);
  if (opts.dateTo) q.set("date_to", opts.dateTo);
  if (opts.species) q.set("species", opts.species);
  const qs = q.toString();
  return `${BASE}/reports/farm/export.csv${qs ? `?${qs}` : ""}`;
}

export async function fetchDevices(): Promise<KnownDevice[]> {
  return (await getJson<KnownDevice[]>("/devices")) ?? [];
}
