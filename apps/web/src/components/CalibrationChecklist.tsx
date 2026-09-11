import { useState } from "react";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { locale: Locale };

const ITEMS = [
  "cal.item.height",
  "cal.item.fov",
  "cal.item.reference",
  "cal.item.level",
  "cal.item.lighting",
  "cal.item.species",
] as const;

export function CalibrationChecklist({ locale }: Props) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const toggle = (key: string) => setChecked((c) => ({ ...c, [key]: !c[key] }));
  const done = ITEMS.filter((k) => checked[k]).length;

  return (
    <div className="card">
      <h2>{t("cal.heading", locale)}</h2>
      <p className="muted">{t("cal.intro", locale)}</p>
      <ul className="checklist">
        {ITEMS.map((key) => (
          <li key={key}>
            <label>
              <input
                type="checkbox"
                checked={!!checked[key]}
                onChange={() => toggle(key)}
              />{" "}
              {t(key, locale)}
            </label>
          </li>
        ))}
      </ul>
      <p className="muted">
        {done}/{ITEMS.length} {t("cal.progress", locale)}
      </p>
      <p className="muted">{t("cal.disclaimer", locale)}</p>
    </div>
  );
}
