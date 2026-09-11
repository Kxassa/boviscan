import type { DeviceStatus } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { status: DeviceStatus | null; locale: Locale };

const mockStatus: DeviceStatus = {
  device_id: "device-local-01",
  online: true,
  camera_ok: true,
  inference_backend: "cpu_mock",
  pipeline_state: "running",
  last_heartbeat: new Date().toISOString(),
  version: "0.1.0",
};

export function DeviceStatusCard({ status, locale }: Props) {
  const s = status ?? mockStatus;
  return (
    <div className="card">
      <h2>{t("status.heading", locale)}</h2>
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
    </div>
  );
}
