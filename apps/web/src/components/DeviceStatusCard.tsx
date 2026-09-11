import type { DeviceStatus } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { status: DeviceStatus | null; locale: Locale; apiOk: boolean };

export function DeviceStatusCard({ status, locale, apiOk }: Props) {
  const s = status;
  return (
    <div className="card">
      <h2>{t("status.heading", locale)}</h2>
      <p>
        <span className={`pill ${apiOk ? "" : "warn"}`}>
          {apiOk ? t("status.apiOk", locale) : t("status.apiDown", locale)}
        </span>
      </p>
      {s ? (
        <>
          <p>
            <span className={`pill ${s.online ? "" : "warn"}`}>
              {s.online ? t("status.online", locale) : t("status.offline", locale)}
            </span>{" "}
            <span className="muted">{s.device_id}</span>
          </p>
          <ul>
            <li>
              {t("status.camera", locale)}: {s.camera_ok ? "OK" : "ERR"}
            </li>
            <li>
              {t("status.backend", locale)}: {s.inference_backend ?? "—"}
            </li>
            <li>
              {t("status.pipeline", locale)}: {s.pipeline_state ?? "—"}
            </li>
          </ul>
        </>
      ) : (
        <p className="muted">{t("status.waiting", locale)}</p>
      )}
    </div>
  );
}
