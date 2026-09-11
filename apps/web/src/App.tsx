import { useEffect, useState } from "react";
import { fetchEvents, fetchStatus, type DeviceStatus, type WeightEvent } from "./api/client";
import { DeviceStatusCard } from "./components/DeviceStatusCard";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { LiveWeight } from "./components/LiveWeight";
import { SessionHistory } from "./components/SessionHistory";
import { useMockLiveWeight } from "./hooks/useMockLiveWeight";
import { DEFAULT_LOCALE, type Locale, t } from "./i18n";

const DEMO_EVENTS: WeightEvent[] = [
  {
    id: "demo-1",
    device_id: "device-local-01",
    track_id: "trk-1",
    timestamp: new Date().toISOString(),
    species: "cattle",
    estimated_weight_kg: 418.2,
    confidence: 0.72,
    proxy_metrics: {},
  },
];

export default function App() {
  const [locale, setLocale] = useState<Locale>(DEFAULT_LOCALE);
  const [events, setEvents] = useState<WeightEvent[]>(DEMO_EVENTS);
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const liveKg = useMockLiveWeight(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [ev, st] = await Promise.all([fetchEvents(), fetchStatus()]);
      if (cancelled) return;
      if (ev.length) setEvents(ev);
      if (st.length) setStatus(st[0]);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app">
      <header>
        <div>
          <h1>{t("app.title", locale)}</h1>
          <div className="muted">{t("app.subtitle", locale)}</div>
        </div>
        <LanguageSwitcher locale={locale} onChange={setLocale} />
      </header>
      <div className="grid">
        <LiveWeight kg={liveKg} locale={locale} />
        <DeviceStatusCard status={status} locale={locale} />
      </div>
      <SessionHistory events={events} locale={locale} />
    </div>
  );
}
