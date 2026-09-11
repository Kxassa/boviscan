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

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${BASE}${path}`);
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchEvents(): Promise<WeightEvent[]> {
  return (await getJson<WeightEvent[]>("/events")) ?? [];
}

export async function fetchStatus(): Promise<DeviceStatus[]> {
  return (await getJson<DeviceStatus[]>("/status")) ?? [];
}
