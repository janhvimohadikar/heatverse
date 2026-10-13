import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CitySelect } from "../../components/CitySelect";
import { Card, DataBadge, ErrorState, Notice, PageHeader, RiskBadge, ScoreBar, Spinner, StatCard, fmt, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useAuth } from "../../hooks/useAuth";
import { useCities } from "../../hooks/useCities";
import { api } from "../../services/endpoints";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function DashboardView() {
  const { user } = useAuth();
  const { cities, loading: citiesLoading, error: citiesError } = useCities();
  const profile = useAsync(() => api.getProfile(), []);
  const [cityId, setCityId] = useState<number | null>(null);

  useEffect(() => {
    if (cityId === null && cities.length) setCityId(profile.data?.home_city_id ?? cities.find((c) => c.name === "Delhi")?.city_id ?? cities[0].city_id);
  }, [cities, profile.data, cityId]);

  const enabled = cityId !== null;
  const month = new Date().getMonth() + 1;
  const live = useAsync(() => api.liveWeather(cityId!), [cityId], enabled);
  const summary = useAsync(() => api.dashboardSummary(cityId!, month), [cityId], enabled);
  const snapshot = useAsync(() => api.mapRisk({ mode: "historical", layer: "risk" }), []);
  const alerts = useAsync(() => api.activeAlerts(cityId ?? undefined), [cityId], enabled);
  const guidance = useAsync(() => api.guidance(), []);

  if (citiesLoading) return <Spinner />;
  if (citiesError) return <ErrorState message={citiesError} />;

  const feature = snapshot.data?.features.find((f) => f.city_id === cityId);
  const clim = summary.data?.month_climatology;
  const tips: string[] = feature?.risk.category && guidance.data ? guidance.data.by_category[feature.risk.category] ?? [] : [];

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Climate & health" title={`Welcome${profile.data?.full_name ? `, ${profile.data.full_name}` : user ? "" : ""}`}
        subtitle="Heat intelligence from 25 years of daily weather, plus live conditions when the weather service is reachable."
        actions={<div className="w-48"><CitySelect cities={cities} value={cityId} onChange={setCityId} /></div>} />

      {alerts.data?.items.map((a) => (
        <Notice key={a.alert_id} tone={a.level === "warning" ? "warn" : "info"}><strong>{a.title}.</strong> {a.message}
          <span className="ml-2 text-xs opacity-75">(Administrator notice — not an official warning)</span></Notice>
      ))}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Current weather" subtitle="Live conditions" actions={<DataBadge type="live" />}>
          {live.loading && <Spinner />}
          {live.data?.status === "ok" && (
            <div>
              <p className="text-3xl font-bold">{fmt(live.data.temperature_c, 1, " °C")}</p>
              <p className="text-sm text-slate-500">Feels like {fmt(live.data.apparent_temperature_c, 1, " °C")} · {live.data.condition ?? "—"}</p>
              <p className="mt-2 text-sm">Humidity {fmt(live.data.humidity_pct, 0, "%")} · Wind {fmt(live.data.wind_speed_kmh, 1, " km/h")} · Pressure {fmt(live.data.pressure_hpa, 0, " hPa")}</p>
              <p className="mt-1 text-xs text-slate-500">{live.data.source} · {live.data.observation_time}</p>
            </div>
          )}
          {live.data && live.data.status !== "ok" && <p className="text-sm text-slate-500">{live.data.reason} Live weather is optional; the rest of the dashboard uses the historical dataset.</p>}
          {live.error && <ErrorState message={live.error} onRetry={live.reload} />}
        </Card>

        <Card title="Latest dataset snapshot" subtitle={snapshot.data ? `Observed on ${fmtDate(snapshot.data.date)} (most recent date in the dataset — not today)` : undefined}
          actions={<DataBadge type="observed" />}>
          {snapshot.loading && <Spinner />}
          {snapshot.error && <ErrorState message={snapshot.error} onRetry={snapshot.reload} />}
          {feature && !feature.missing && (<div className="space-y-2">
            <div className="flex items-center justify-between"><span className="text-sm">Heat-risk score</span><RiskBadge category={feature.risk.category} score={feature.risk.score} /></div>
            <ScoreBar score={feature.risk.score} category={feature.risk.category} />
            <p className="text-sm">Max {fmt(feature.values.temp_max_c, 1, " °C")} · Min {fmt(feature.values.temp_min_c, 1, " °C")} · Apparent {fmt(feature.values.apparent_max_c, 1, " °C")}</p>
          </div>)}
          <Link to="/map" className="btn-secondary mt-3">Open the heat-risk map</Link>
        </Card>

        <Card title="Today's guidance" subtitle={feature?.risk.category ? `Based on the snapshot category: ${feature.risk.category}` : undefined}>
          {tips.length ? <ul className="list-disc space-y-1 pl-5 text-sm">{tips.map((t) => <li key={t}>{t}</li>)}</ul> : <p className="text-sm text-slate-500">Guidance appears when a risk category is available.</p>}
          <Link to="/predictions" className="btn-primary mt-3">Run a personal prediction</Link>
          <p className="mt-2 text-xs text-slate-500">Educational guidance, not medical advice.</p>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={`Avg max temp (${MONTHS[month - 1]})`} value={fmt(clim?.avg_temp_max_c, 1, " °C")} hint="2000–2024 average" />
        <StatCard label="Avg apparent max" value={fmt(clim?.avg_apparent_max_c, 1, " °C")} hint="Feels-like heat load" />
        <StatCard label="Monthly rainfall" value={fmt(clim?.avg_monthly_precipitation_mm, 1, " mm")} hint="Average monthly total" />
        <StatCard label="Wind (avg max)" value={fmt(clim?.avg_wind_speed_max_kmh, 1, " km/h")} hint="Historical average" />
      </div>

      <Card title="Temperature through the year" subtitle="Average by calendar month, 2000–2024 (observed)">
        {summary.loading && <Spinner />}
        {summary.error && <ErrorState message={summary.error} onRetry={summary.reload} />}
        {summary.data && (
          <div className="h-64" role="img" aria-label="Line chart of average monthly temperatures">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary.data.year_profile.map((r: { month: number }) => ({ ...r, label: MONTHS[r.month - 1] }))} margin={{ left: -10, right: 10, top: 5 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="label" /><YAxis unit="°" domain={["auto", "auto"]} />
                <Tooltip formatter={(v: number) => `${v} °C`} /><Legend />
                <Line dataKey="avg_temp_max_c" name="Avg max" stroke="#C53030" strokeWidth={2} />
                <Line dataKey="avg_apparent_max_c" name="Avg apparent max" stroke="#EA580C" strokeDasharray="4 3" />
                <Line dataKey="avg_temp_min_c" name="Avg min" stroke="#2A4D80" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  );
}
