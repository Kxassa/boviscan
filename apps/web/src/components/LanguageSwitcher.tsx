import type { Locale } from "../i18n";
import { DEFAULT_LOCALE, OPTIONAL_LOCALES, t } from "../i18n";

type Props = {
  locale: Locale;
  onChange: (locale: Locale) => void;
};

export function LanguageSwitcher({ locale, onChange }: Props) {
  return (
    <label className="muted">
      {t("lang.label", locale)}{" "}
      <select
        value={locale}
        onChange={(e) => onChange(e.target.value as Locale)}
        aria-label={t("lang.label", locale)}
      >
        <option value={DEFAULT_LOCALE}>pt-BR</option>
        {OPTIONAL_LOCALES.map((l) => (
          <option key={l} value={l}>
            {l} (stub)
          </option>
        ))}
      </select>
      <div className="muted">{t("lang.note", locale)}</div>
    </label>
  );
}
