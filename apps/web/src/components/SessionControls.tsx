import type { WeighingSession } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = {
  locale: Locale;
  active: WeighingSession | null;
  busy: boolean;
  onStart: () => void;
  onStop: () => void;
};

export function SessionControls({ locale, active, busy, onStart, onStop }: Props) {
  return (
    <div className="card">
      <h2>{t("session.heading", locale)}</h2>
      {active ? (
        <>
          <p>
            <span className="pill">{t("session.active", locale)}</span>{" "}
            <code className="muted">{active.id.slice(0, 8)}…</code>
          </p>
          <p className="muted">
            {t("session.events", locale)}: {active.event_count} · {active.status}
          </p>
          <button type="button" disabled={busy} onClick={onStop}>
            {t("session.stop", locale)}
          </button>
        </>
      ) : (
        <>
          <p className="muted">{t("session.idle", locale)}</p>
          <button type="button" disabled={busy} onClick={onStart}>
            {t("session.start", locale)}
          </button>
        </>
      )}
    </div>
  );
}
