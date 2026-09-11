import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = {
  kg: number | null;
  locale: Locale;
  fromApi: boolean;
  confidence?: number | null;
};

export function LiveWeight({ kg, locale, fromApi, confidence }: Props) {
  return (
    <div className="card">
      <h2>{t("live.heading", locale)}</h2>
      <div className="live-weight">
        {kg != null ? kg.toFixed(1) : "—"}{" "}
        <span style={{ fontSize: "1rem" }}>{t("live.kg", locale)}</span>
      </div>
      <p className="muted">{t("live.disclaimer", locale)}</p>
      <p className="muted">
        {fromApi ? t("live.sourceApi", locale) : t("live.sourceWaiting", locale)}
        {confidence != null ? ` · conf ${confidence.toFixed(2)}` : ""}
      </p>
    </div>
  );
}
