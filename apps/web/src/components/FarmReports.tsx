import { useCallback, useEffect, useState } from "react";
import {
  farmReportCsvUrl,
  fetchFarmReport,
  type FarmReport,
} from "../api/client";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = { locale: Locale };

function fmtKg(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(1)} kg*`;
}

export function FarmReports({ locale }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [species, setSpecies] = useState("");
  const [report, setReport] = useState<FarmReport | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await fetchFarmReport({
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      species: species || undefined,
    });
    setReport(r);
    setLoading(false);
  }, [dateFrom, dateTo, species]);

  useEffect(() => {
    load();
  }, [load]);

  const csvHref = farmReportCsvUrl({
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    species: species || undefined,
  });

  return (
    <div className="card">
      <h2>{t("reports.heading", locale)}</h2>
      <p className="muted">{t("reports.intro", locale)}</p>

      <div className="filters">
        <label>
          {t("reports.from", locale)}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </label>
        <label>
          {t("reports.to", locale)}
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </label>
        <label>
          {t("reports.species", locale)}
          <select value={species} onChange={(e) => setSpecies(e.target.value)}>
            <option value="">{t("reports.speciesAll", locale)}</option>
            <option value="cattle">{t("species.cattle", locale)}</option>
            <option value="sheep">{t("species.sheep", locale)}</option>
            <option value="goat">{t("species.goat", locale)}</option>
          </select>
        </label>
        <button type="button" onClick={load} disabled={loading}>
          {t("reports.refresh", locale)}
        </button>
        <a className="button-link" href={csvHref}>
          {t("reports.downloadCsv", locale)}
        </a>
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="muted">{t("reports.count", locale)}</div>
          <div className="summary-value">{report?.event_count ?? "—"}</div>
        </div>
        <div className="summary-card">
          <div className="muted">{t("reports.avg", locale)}</div>
          <div className="summary-value">{fmtKg(report?.avg_kg)}</div>
        </div>
        <div className="summary-card">
          <div className="muted">{t("reports.min", locale)}</div>
          <div className="summary-value">{fmtKg(report?.min_kg)}</div>
        </div>
        <div className="summary-card">
          <div className="muted">{t("reports.max", locale)}</div>
          <div className="summary-value">{fmtKg(report?.max_kg)}</div>
        </div>
      </div>

      {report && report.by_species.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>{t("reports.species", locale)}</th>
              <th>{t("reports.count", locale)}</th>
              <th>{t("reports.avg", locale)}</th>
              <th>{t("reports.min", locale)}</th>
              <th>{t("reports.max", locale)}</th>
            </tr>
          </thead>
          <tbody>
            {report.by_species.map((s) => (
              <tr key={s.species}>
                <td>{s.species}</td>
                <td>{s.count}</td>
                <td>{fmtKg(s.avg_kg)}</td>
                <td>{fmtKg(s.min_kg)}</td>
                <td>{fmtKg(s.max_kg)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="muted">* {t("live.disclaimer", locale)}</p>
    </div>
  );
}
