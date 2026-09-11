import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { kg: number; locale: Locale };

export function LiveWeight({ kg, locale }: Props) {
  return (
    <div className="card">
      <h2>{t("live.heading", locale)}</h2>
      <div className="live-weight">
        {kg.toFixed(1)} <span style={{ fontSize: "1rem" }}>{t("live.kg", locale)}</span>
      </div>
      <p className="muted">{t("live.disclaimer", locale)}</p>
    </div>
  );
}
