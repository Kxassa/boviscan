import { useCallback, useEffect, useState } from "react";
import {
  fetchHealth,
  fetchSessions,
  fetchStatus,
  startSession,
  stopSession,
  type DeviceStatus,
  type WeighingSession,
} from "./api/client";
import { authEnabled, readFirebaseConfig } from "./auth/config";
import { signOutFirebase } from "./auth/firebase";
import { getIdToken, getUserEmail, subscribeAuth } from "./auth/session";
import { CalibrationChecklist } from "./components/CalibrationChecklist";
import { DeviceStatusCard } from "./components/DeviceStatusCard";
import { DevicesPage } from "./components/DevicesPage";
import { FarmReports } from "./components/FarmReports";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { LiveWeight } from "./components/LiveWeight";
import { LoginScreen } from "./components/LoginScreen";
import { SessionControls } from "./components/SessionControls";
import { SessionHistory } from "./components/SessionHistory";
import { useLiveWeightFeed } from "./hooks/useLiveWeightFeed";
import { DEFAULT_LOCALE, type Locale, t } from "./i18n";

type Page = "console" | "calibration" | "reports" | "devices";

export default function App() {
  const [locale, setLocale] = useState<Locale>(DEFAULT_LOCALE);
  const [page, setPage] = useState<Page>("console");
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const [sessions, setSessions] = useState<WeighingSession[]>([]);
  const [active, setActive] = useState<WeighingSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [apiOk, setApiOk] = useState(false);
  const [authTick, setAuthTick] = useState(0);

  const needLogin = authEnabled() && !!readFirebaseConfig() && !getIdToken();

  useEffect(() => subscribeAuth(() => setAuthTick((n) => n + 1)), []);

  const sessionId = active?.id ?? null;
  const { events, latestKg } = useLiveWeightFeed(sessionId);

  const refreshMeta = useCallback(async () => {
    const [st, sess, health] = await Promise.all([
      fetchStatus(),
      fetchSessions(),
      fetchHealth(),
    ]);
    setApiOk(!!health?.ok);
    if (st.length) setStatus(st[0]);
    setSessions(sess);
    const open = sess.find((s) => s.status === "active" && !s.ended_at);
    if (open) setActive(open);
  }, [authTick]);

  useEffect(() => {
    if (needLogin) return;
    refreshMeta();
    const id = setInterval(refreshMeta, 5000);
    return () => clearInterval(id);
  }, [refreshMeta, needLogin]);

  const onStart = async () => {
    setBusy(true);
    const s = await startSession(status?.device_id ?? "device-local-01");
    if (s) setActive(s);
    await refreshMeta();
    setBusy(false);
  };

  const onStop = async () => {
    if (!active) return;
    setBusy(true);
    await stopSession(active.id);
    setActive(null);
    await refreshMeta();
    setBusy(false);
  };

  const latestConf =
    events.find((e) => e.estimated_weight_kg != null)?.confidence ?? null;

  if (needLogin) {
    return (
      <div className="app">
        <header>
          <div>
            <h1>{t("app.title", locale)}</h1>
            <div className="muted">{t("app.subtitle", locale)}</div>
          </div>
          <LanguageSwitcher locale={locale} onChange={setLocale} />
        </header>
        <LoginScreen locale={locale} onAuthenticated={() => setAuthTick((n) => n + 1)} />
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>{t("app.title", locale)}</h1>
          <div className="muted">{t("app.subtitle", locale)}</div>
        </div>
        <div className="header-actions">
          <nav className="tabs">
            <button
              type="button"
              className={page === "console" ? "active" : ""}
              onClick={() => setPage("console")}
            >
              {t("nav.console", locale)}
            </button>
            <button
              type="button"
              className={page === "reports" ? "active" : ""}
              onClick={() => setPage("reports")}
            >
              {t("nav.reports", locale)}
            </button>
            <button
              type="button"
              className={page === "devices" ? "active" : ""}
              onClick={() => setPage("devices")}
            >
              {t("nav.devices", locale)}
            </button>
            <button
              type="button"
              className={page === "calibration" ? "active" : ""}
              onClick={() => setPage("calibration")}
            >
              {t("nav.calibration", locale)}
            </button>
          </nav>
          {authEnabled() && getUserEmail() && (
            <span className="pill">{getUserEmail()}</span>
          )}
          {authEnabled() && getIdToken() && (
            <button type="button" onClick={() => signOutFirebase()}>
              {t("auth.signOut", locale)}
            </button>
          )}
          <LanguageSwitcher locale={locale} onChange={setLocale} />
        </div>
      </header>

      {page === "calibration" ? (
        <CalibrationChecklist locale={locale} />
      ) : page === "reports" ? (
        <FarmReports locale={locale} />
      ) : page === "devices" ? (
        <DevicesPage locale={locale} />
      ) : (
        <>
          <div className="grid">
            <LiveWeight
              kg={latestKg}
              locale={locale}
              fromApi={latestKg != null}
              confidence={latestConf}
            />
            <SessionControls
              locale={locale}
              active={active}
              busy={busy}
              onStart={onStart}
              onStop={onStop}
            />
            <DeviceStatusCard status={status} locale={locale} apiOk={apiOk} />
          </div>
          <SessionHistory events={events} sessions={sessions} locale={locale} />
        </>
      )}
    </div>
  );
}
