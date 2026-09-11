import type { WeightEvent } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { events: WeightEvent[]; locale: Locale };

function speciesLabel(sp: string, locale: Locale) {
  const key = `species.${sp}` as const;
  const translated = t(key, locale);
  return translated === key ? sp : translated;
}

export function SessionHistory({ events, locale }: Props) {
  return (
    <div className="card">
      <h2>{t("history.heading", locale)}</h2>
      {events.length === 0 ? (
        <p className="muted">{t("history.empty", locale)}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("history.time", locale)}</th>
              <th>{t("history.species", locale)}</th>
              <th>{t("history.weight", locale)}</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.timestamp).toLocaleString("pt-BR")}</td>
                <td>{speciesLabel(e.species, locale)}</td>
                <td>
                  {e.estimated_weight_kg != null ? `${e.estimated_weight_kg.toFixed(1)} kg` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
