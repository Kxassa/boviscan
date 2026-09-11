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

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${BASE}${path}`);
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
      headers: { "Content-Type": "application/json" },
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

export async function fetchHealth(): Promise<{ ok: boolean } | null> {
  return getJson("/health");
}
