import { useCallback, useEffect, useState } from "react";
import { fetchDevices, type KnownDevice } from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { locale: Locale };

export function DevicesPage({ locale }: Props) {
  const [devices, setDevices] = useState<KnownDevice[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setDevices(await fetchDevices());
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="card">
      <h2>{t("devices.heading", locale)}</h2>
      <p className="muted">{t("devices.intro", locale)}</p>
      <button type="button" onClick={load} disabled={loading}>
        {t("devices.refresh", locale)}
      </button>

      {devices.length === 0 ? (
        <p className="muted">{t("devices.empty", locale)}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("devices.id", locale)}</th>
              <th>{t("devices.name", locale)}</th>
              <th>{t("devices.host", locale)}</th>
              <th>{t("devices.source", locale)}</th>
              <th>{t("devices.lastSeen", locale)}</th>
              <th>{t("devices.health", locale)}</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => {
              const backend =
                (d.health?.inference_backend as string | undefined) ?? "—";
              const pipeline =
                (d.health?.pipeline_state as string | undefined) ?? "—";
              return (
                <tr key={d.device_id}>
                  <td>
                    <code>{d.device_id}</code>
                    <div>
                      <span className={`pill ${d.online ? "" : "warn"}`}>
                        {d.online
                          ? t("status.online", locale)
                          : t("status.offline", locale)}
                      </span>
                    </div>
                  </td>
                  <td>{d.display_name ?? "—"}</td>
                  <td className="muted">
                    {d.host ?? "—"}
                    {d.api_base ? (
                      <>
                        <br />
                        <small>{d.api_base}</small>
                      </>
                    ) : null}
                  </td>
                  <td>
                    <span className="pill">{d.source}</span>
                    {d.version ? (
                      <>
                        {" "}
                        <span className="muted">v{d.version}</span>
                      </>
                    ) : null}
                  </td>
                  <td>{new Date(d.last_seen).toLocaleString("pt-BR")}</td>
                  <td className="muted">
                    {t("status.backend", locale)}: {backend}
                    <br />
                    {t("status.pipeline", locale)}: {pipeline}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <p className="muted">{t("devices.discoveryNote", locale)}</p>
    </div>
  );
}
