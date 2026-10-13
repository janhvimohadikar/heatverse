import { useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DataBadge, ErrorState, Notice, RiskBadge, ScoreBar, Spinner, fmt, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { api } from "../../services/endpoints";
import type { LiveWeather, MapFeature, MapMode } from "../../types";

export default function CityPanel({ feature, date, mode, onClose }: { feature: MapFeature; date: string; mode: MapMode; onClose: () => void }) {
  // In demo-prediction mode the date is in the future, so the historical detail shows the latest observed date instead.
  const detail = useAsync(() => api.cityDetail(feature.city_id, mode === "historical" ? date : undefined), [feature.city_id, date, mode]);
  const [live, setLive] = useState<LiveWeather | null>(null);
  const [liveBusy, setLiveBusy] = useState(false);

  async function loadLive() {
    setLiveBusy(true);
    try { setLive(await api.liveWeather(feature.city_id)); }
    catch (e) { setLive({ status: "unavailable", reason: e instanceof Error ? e.message : "Failed." }); }
    finally { setLiveBusy(false); }
  }

  const v = feature.values;
  return (
    <section className="card" aria-live="polite">
      <header className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold">{feature.name}</h2>
          <p className="text-xs text-slate-500">{feature.state ?? "—"}</p>
        </div>
        <button className="btn-secondary" onClick={onClose} aria-label="Close city details">✕</button>
      </header>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <RiskBadge category={feature.risk.category} score={feature.risk.score} />
        <DataBadge type={mode === "historical" ? "observed" : "demo"} />
        {mode === "historical" && <DataBadge type="derived" />}
      </div>
      {feature.risk.score !== null && <div className="mt-2"><ScoreBar score={feature.risk.score} category={feature.risk.category} /></div>}

      {feature.missing ? (
        <p className="mt-3 text-sm text-slate-500">{feature.missing_reason ?? "No data for this city on this date."}</p>
      ) : (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-slate-500">{mode === "historical" ? "Observation date" : "Prediction for"}</dt><dd>{fmtDate(feature.observation_date ?? date)}</dd>
          <dt className="text-slate-500">Max temperature</dt><dd>{fmt(v.temp_max_c, 1, " °C")}</dd>
          <dt className="text-slate-500">Min temperature</dt><dd>{fmt(v.temp_min_c, 1, " °C")}</dd>
          <dt className="text-slate-500">Apparent (max)</dt><dd>{fmt(v.apparent_max_c, 1, " °C")}</dd>
          {mode === "historical" && (<>
            <dt className="text-slate-500">Departure from monthly normal</dt><dd>{fmt(v.temp_anomaly_c, 1, " °C")}</dd>
            <dt className="text-slate-500">Hot-day streak</dt><dd>{feature.hot_day_streak ?? "—"} day(s)</dd>
            <dt className="text-slate-500">Wind (max)</dt><dd>{fmt(v.wind_speed_max_kmh, 1, " km/h")}</dd>
            <dt className="text-slate-500">Precipitation</dt><dd>{fmt(v.precipitation_sum_mm, 1, " mm")}</dd>
          </>)}
        </dl>
      )}

      {mode === "demo_prediction" && <div className="mt-3"><Notice tone="demo">DEMO values: a climatology baseline for the selected future date, not a trained forecast. Trend chart below shows the latest observed 30 days.</Notice></div>}

      {detail.loading && !detail.data && <Spinner label="Loading city details…" />}
      {detail.error && <div className="mt-3"><ErrorState message={detail.error} onRetry={detail.reload} /></div>}
      {detail.data && (
        <>
          <h3 className="mb-1 mt-4 text-sm font-semibold">30-day temperature trend <span className="font-normal text-slate-500">(to {fmtDate(detail.data.date)}, observed)</span></h3>
          <div className="h-44" role="img" aria-label="Line chart of the last 30 days of temperature">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={detail.data.trend_30d} margin={{ top: 5, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="obs_date" tickFormatter={(d: string) => d.slice(5)} fontSize={10} minTickGap={20} />
                <YAxis fontSize={10} unit="°" domain={["auto", "auto"]} />
                <Tooltip formatter={(val: number) => `${val} °C`} labelFormatter={(l: string) => fmtDate(l)} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="temp_max_c" name="Max" stroke="#C53030" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="apparent_max_c" name="Apparent max" stroke="#EA580C" dot={false} strokeDasharray="4 3" />
                <Line type="monotone" dataKey="temp_min_c" name="Min" stroke="#2A4D80" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {detail.data.weekly_tmax_change_c !== null && (
            <p className="text-xs text-slate-500">Last 7 days average Tmax vs the 7 days before: {detail.data.weekly_tmax_change_c > 0 ? "+" : ""}{detail.data.weekly_tmax_change_c} °C</p>
          )}

          {mode === "historical" && detail.data.explanation.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold">Why this score?</h3>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{detail.data.explanation.map((l, i) => <li key={i}>{l}</li>)}</ul>
              <p className="mt-1 text-xs text-slate-500">Rule-based breakdown of the scoring formula (not a machine-learning attribution).</p>
            </div>
          )}
          {mode === "historical" && detail.data.recommendations.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold">Safety recommendations</h3>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{detail.data.recommendations.map((l, i) => <li key={i}>{l}</li>)}</ul>
            </div>
          )}
        </>
      )}

      <div className="mt-4 border-t border-slate-200 pt-3 dark:border-navy-700">
        <h3 className="text-sm font-semibold">Current weather <DataBadge type="live" /></h3>
        {!live && <button className="btn-secondary mt-2" onClick={loadLive} disabled={liveBusy}>{liveBusy ? "Loading…" : "Load live weather"}</button>}
        {live?.status === "ok" && (
          <p className="mt-1 text-sm">
            {fmt(live.temperature_c, 1, " °C")} (feels {fmt(live.apparent_temperature_c, 1, " °C")}), humidity {fmt(live.humidity_pct, 0, "%")}, wind {fmt(live.wind_speed_kmh, 1, " km/h")}
            {live.condition ? `, ${live.condition}` : ""}. <span className="text-xs text-slate-500">{live.source} · {live.observation_time}</span>
          </p>
        )}
        {live && live.status !== "ok" && <p className="mt-1 text-sm text-slate-500">{live.reason ?? "Live weather is unavailable."} Historical values above are never shown as current weather.</p>}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link className="btn-secondary" to={`/trends?city=${feature.city_id}`}>Historical trends →</Link>
        <Link className="btn-secondary" to={`/predictions?city=${feature.city_id}`}>Prediction details →</Link>
      </div>
      <p className="mt-3 text-xs text-slate-500">Informational project metric — not an official heat warning.</p>
    </section>
  );
}
