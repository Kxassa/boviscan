import type { WeightEvent, WeighingSession } from "../api/client";
import { sessionCsvUrl } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = {
  events: WeightEvent[];
  sessions: WeighingSession[];
  locale: Locale;
};

function speciesLabel(sp: string, locale: Locale) {
  const key = `species.${sp}` as const;
  const translated = t(key, locale);
  return translated === key ? sp : translated;
}

export function SessionHistory({ events, sessions, locale }: Props) {
  return (
    <div className="card">
      <h2>{t("history.heading", locale)}</h2>
      {sessions.length > 0 && (
        <div className="session-list">
          <h3 className="muted" style={{ fontSize: "0.95rem" }}>
            {t("history.sessions", locale)}
          </h3>
          <ul>
            {sessions.slice(0, 8).map((s) => (
              <li key={s.id}>
                <span className="pill">{s.status}</span>{" "}
                {new Date(s.started_at).toLocaleString("pt-BR")} · {s.event_count} evt ·{" "}
                <a href={sessionCsvUrl(s.id)}>{t("history.exportCsv", locale)}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
      {events.length === 0 ? (
        <p className="muted">{t("history.empty", locale)}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("history.time", locale)}</th>
              <th>{t("history.species", locale)}</th>
              <th>{t("history.weight", locale)}</th>
              <th>{t("history.track", locale)}</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.timestamp).toLocaleString("pt-BR")}</td>
                <td>{speciesLabel(e.species, locale)}</td>
                <td>
                  {e.estimated_weight_kg != null
                    ? `${e.estimated_weight_kg.toFixed(1)} kg*`
                    : "—"}
                </td>
                <td className="muted">{e.track_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">* {t("live.disclaimer", locale)}</p>
    </div>
  );
}
