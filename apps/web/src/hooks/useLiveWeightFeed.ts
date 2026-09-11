import { useEffect, useState } from "react";
import { fetchEvents, type WeightEvent } from "../api/client";

/** Poll companion API for latest weight events (live feed). Falls back to null when empty. */
export function useLiveWeightFeed(sessionId: string | null, intervalMs = 2000) {
  const [events, setEvents] = useState<WeightEvent[]>([]);
  const [latestKg, setLatestKg] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const ev = await fetchEvents(sessionId);
      if (cancelled) return;
      if (ev.length === 0 && !sessionId) {
        // still try global feed
      }
      setEvents(ev);
      setError(false);
      const withKg = ev.find((e) => e.estimated_weight_kg != null);
      setLatestKg(withKg?.estimated_weight_kg ?? null);
    };
    tick().catch(() => {
      if (!cancelled) setError(true);
    });
    const id = setInterval(() => {
      tick().catch(() => {
        if (!cancelled) setError(true);
      });
    }, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [sessionId, intervalMs]);

  return { events, latestKg, error };
}
