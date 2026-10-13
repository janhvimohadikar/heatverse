import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CitySelect } from "../../components/CitySelect";
import { Card, DataBadge, EmptyState, ErrorState, Notice, PageHeader, Spinner, fmt, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useCities } from "../../hooks/useCities";
import { api } from "../../services/endpoints";

const TABS = ["Annual", "Monthly", "Seasonal", "Typical year", "City comparison", "Period comparison", "Heatwave events", "Data quality"] as const;
type Tab = (typeof TABS)[number];
const COLORS = ["#C53030", "#2A4D80", "#EA580C", "#2F855A", "#7C3AED", "#0891B2", "#B45309", "#DB2777", "#475569", "#65A30D"];
const METRICS: Record<string, string> = {
  temp_max_c: "Average maximum temperature (°C)", temp_min_c: "Average minimum temperature (°C)", apparent_max_c: "Average apparent maximum (°C)",
  peak_temp_max_c: "Highest maximum temperature (°C)", precipitation_sum_mm: "Total precipitation (mm)", wind_speed_max_kmh: "Average max wind (km/h)",
};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function TempChart({ data, xKey }: { data: object[]; xKey: string }) {
  return (
    <div className="h-72" role="img" aria-label="Line chart of average and extreme temperatures">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: -10, right: 10, top: 5 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey={xKey} minTickGap={24} /><YAxis unit="°" domain={["auto", "auto"]} />
          <Tooltip formatter={(v: number) => `${v} °C`} /><Legend />
          <Line dataKey="peak_temp_max_c" name="Highest max" stroke="#7F1D1D" dot={false} strokeDasharray="2 3" />
          <Line dataKey="avg_temp_max_c" name="Avg max" stroke="#C53030" dot={false} strokeWidth={2} />
          <Line dataKey="avg_apparent_max_c" name="Avg apparent max" stroke="#EA580C" dot={false} strokeDasharray="4 3" />
          <Line dataKey="avg_temp_min_c" name="Avg min" stroke="#2A4D80" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function BarsChart({ data, xKey, series }: { data: object[]; xKey: string; series: { key: string; name: string; color: string }[] }) {
  return (
    <div className="h-60" role="img" aria-label="Bar chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -10, right: 10, top: 5 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey={xKey} minTickGap={24} /><YAxis /><Tooltip /><Legend />
          {series.map((s) => <Bar key={s.key} dataKey={s.key} name={s.name} fill={s.color} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function TrendsView() {
  const { cities, loading: cl, error: ce } = useCities();
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>("Annual");
  const [cityId, setCityId] = useState<number | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [metric, setMetric] = useState("temp_max_c");
  const [picked, setPicked] = useState<number[]>([]);
  const [pa, setPa] = useState({ s: "2000-04-01", e: "2000-06-30" });
  const [pb, setPb] = useState({ s: "2024-04-01", e: "2024-06-30" });

  useEffect(() => {
    if (!cities.length) return;
    const q = Number(params.get("city"));
    if (cityId === null) setCityId(cities.find((c) => c.city_id === q)?.city_id ?? cities.find((c) => c.name === "Delhi")?.city_id ?? cities[0].city_id);
    if (!picked.length) setPicked(cities.slice(0, 4).map((c) => c.city_id));
  }, [cities]); // eslint-disable-line react-hooks/exhaustive-deps

  const ready = cityId !== null;
  const gran = tab === "Annual" ? "annual" : tab === "Monthly" ? "monthly" : "seasonal";
  const series = useAsync(() => api.trends(cityId!, gran, start || undefined, end || undefined), [cityId, gran, start, end], ready && ["Annual", "Monthly", "Seasonal"].includes(tab));
  const clim = useAsync(() => api.climatology(cityId!), [cityId], ready && tab === "Typical year");
  const cmp = useAsync(() => api.comparison(picked, metric, start || undefined, end || undefined), [picked.join(","), metric, start, end], tab === "City comparison" && picked.length > 0);
  const per = useAsync(() => api.periodComparison(cityId!, pa.s, pa.e, pb.s, pb.e), [cityId, pa.s, pa.e, pb.s, pb.e], ready && tab === "Period comparison");
  const hw = useAsync(() => api.heatwaveEvents(cityId!, start || undefined, end || undefined), [cityId, start, end], ready && tab === "Heatwave events");
  const dq = useAsync(() => api.dataQuality(), [], tab === "Data quality");

  if (cl) return <Spinner />;
  if (ce) return <ErrorState message={ce} />;
  const cityName = cities.find((c) => c.city_id === cityId)?.name ?? "";
  const togglePick = (id: number) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Historical climate" title="Climate trends" subtitle="Aggregations are calculated in the database from the supplied 2000–2024 dataset; the browser never downloads the raw history." />

      <div className="card grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <CitySelect cities={cities} value={cityId} onChange={setCityId} />
        <div><label className="label" htmlFor="s">From</label><input id="s" type="date" className="input" min="2000-01-01" max="2024-12-31" value={start} onChange={(e) => setStart(e.target.value)} /></div>
        <div><label className="label" htmlFor="e">To</label><input id="e" type="date" className="input" min="2000-01-01" max="2024-12-31" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
        <div className="flex items-end"><button className="btn-secondary w-full" onClick={() => { setStart(""); setEnd(""); }}>Clear dates</button></div>
      </div>

      <div className="flex flex-wrap gap-1" role="tablist" aria-label="Analysis type">
        {TABS.map((t) => (<button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "btn-primary" : "btn-secondary"} onClick={() => setTab(t)}>{t}</button>))}
      </div>

      {tab === "Annual" && <Card title={`${cityName}: annual temperature`} actions={<DataBadge type="observed" />}>
        {series.loading && <Spinner />}{series.error && <ErrorState message={series.error} onRetry={series.reload} />}
        {series.data && (series.data.items.length ? (<>
          <TempChart data={series.data.items} xKey="period" />
          <h3 className="mb-1 mt-4 text-sm font-semibold">Hot days (max ≥ {series.data.hot_day_threshold_c} °C) and total precipitation</h3>
          <BarsChart data={series.data.items} xKey="period" series={[{ key: "hot_days", name: "Hot days", color: "#C53030" }, { key: "total_precipitation_mm", name: "Precipitation (mm)", color: "#2A4D80" }]} />
        </>) : <EmptyState>No observations in this range.</EmptyState>)}</Card>}

      {tab === "Monthly" && <Card title={`${cityName}: monthly temperature`} subtitle="Choose a date range above to focus on fewer months." actions={<DataBadge type="observed" />}>
        {series.loading && <Spinner />}{series.error && <ErrorState message={series.error} onRetry={series.reload} />}
        {series.data && (series.data.items.length ? <TempChart data={series.data.items} xKey="period" /> : <EmptyState>No observations in this range.</EmptyState>)}</Card>}

      {tab === "Seasonal" && <Card title={`${cityName}: seasonal comparison`} subtitle="Indian seasons: Winter (Dec–Feb), Summer (Mar–May), Monsoon (Jun–Sep), Post-monsoon (Oct–Nov). Dec is counted with the following winter. First/last seasons may be partial." actions={<DataBadge type="observed" />}>
        {series.loading && <Spinner />}{series.error && <ErrorState message={series.error} onRetry={series.reload} />}
        {series.data && (() => {
          const seasons = ["Winter", "Summer", "Monsoon", "Post-monsoon"];
          const rows = series.data.items.filter((r: { days: number }) => r.days >= 60);
          const years = Array.from(new Set<number>(rows.map((r: { period: number }) => r.period))).sort();
          const pivot = years.map((y) => ({ year: y, ...Object.fromEntries(seasons.map((s) => [s, rows.find((r: { period: number; season: string }) => r.period === y && r.season === s)?.avg_temp_max_c ?? null])) }));
          return pivot.length ? (<div className="h-72" role="img" aria-label="Seasonal average maximum temperature by year"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={pivot} margin={{ left: -10, right: 10 }}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="year" /><YAxis unit="°" domain={["auto", "auto"]} /><Tooltip formatter={(v: number) => `${v} °C`} /><Legend />
              {seasons.map((s, i) => <Line key={s} dataKey={s} stroke={COLORS[i]} dot={false} strokeWidth={2} connectNulls />)}</LineChart></ResponsiveContainer></div>) : <EmptyState>No complete seasons in this range.</EmptyState>;
        })()}</Card>}

      {tab === "Typical year" && <Card title={`${cityName}: typical year (2000–2024 monthly averages)`} actions={<DataBadge type="observed" />}>
        {clim.loading && <Spinner />}{clim.error && <ErrorState message={clim.error} />}
        {clim.data && <TempChart data={clim.data.items.map((r: { month: number }) => ({ ...r, label: MONTHS[r.month - 1] }))} xKey="label" />}</Card>}

      {tab === "City comparison" && (<Card title="Compare cities" actions={<DataBadge type="observed" />}>
        <div className="mb-3 grid gap-3 sm:grid-cols-2">
          <div><label className="label" htmlFor="metric">Metric</label><select id="metric" className="input" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {Object.entries(METRICS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
          <fieldset><legend className="label">Cities</legend><div className="flex flex-wrap gap-2">{cities.map((c) => (
            <label key={c.city_id} className="flex items-center gap-1 text-sm"><input type="checkbox" checked={picked.includes(c.city_id)} onChange={() => togglePick(c.city_id)} />{c.name}</label>))}</div></fieldset>
        </div>
        {cmp.loading && <Spinner />}{cmp.error && <ErrorState message={cmp.error} onRetry={cmp.reload} />}
        {picked.length === 0 && <EmptyState>Select at least one city.</EmptyState>}
        {cmp.data && picked.length > 0 && (<>
          <div className="h-72" role="img" aria-label="Line chart comparing cities by year"><ResponsiveContainer width="100%" height="100%">
            <LineChart data={cmp.data.yearly} margin={{ left: -10, right: 10 }}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="year" /><YAxis domain={["auto", "auto"]} unit={" " + cmp.data.metric.unit} /><Tooltip /><Legend />
              {cmp.data.cities.map((c: { city_id: number; name: string }, i: number) => <Line key={c.city_id} dataKey={String(c.city_id)} name={c.name} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} connectNulls />)}</LineChart></ResponsiveContainer></div>
          <div className="mt-4 overflow-x-auto"><table className="min-w-full text-sm"><thead><tr>{["City", "Avg max", "Avg min", "Peak max", "Hot days", "Precip. (mm)"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>{cmp.data.summaries.map((s: Record<string, number | string>) => (<tr key={s.city_id} className="border-t border-slate-100 dark:border-navy-800">
              <td className="td font-medium">{s.name}</td><td className="td">{fmt(s.avg_temp_max_c as number, 1, " °C")}</td><td className="td">{fmt(s.avg_temp_min_c as number, 1, " °C")}</td>
              <td className="td">{fmt(s.peak_temp_max_c as number, 1, " °C")}</td><td className="td">{s.hot_days}</td><td className="td">{fmt(s.total_precipitation_mm as number, 0)}</td></tr>))}</tbody></table></div>
        </>)}</Card>)}

      {tab === "Period comparison" && (<Card title={`${cityName}: compare two periods`} actions={<DataBadge type="observed" />}>
        <div className="mb-3 grid gap-3 sm:grid-cols-2">
          {[["Period A", pa, setPa], ["Period B", pb, setPb]].map(([label, val, set]) => {
            const v = val as { s: string; e: string }; const setter = set as typeof setPa;
            return (<div key={label as string} className="grid grid-cols-2 gap-2"><p className="col-span-2 text-sm font-semibold">{label as string}</p>
              <input aria-label={`${label} start`} type="date" className="input" min="2000-01-01" max="2024-12-31" value={v.s} onChange={(e) => setter({ ...v, s: e.target.value })} />
              <input aria-label={`${label} end`} type="date" className="input" min="2000-01-01" max="2024-12-31" value={v.e} onChange={(e) => setter({ ...v, e: e.target.value })} /></div>);
          })}
        </div>
        {per.loading && <Spinner />}{per.error && <ErrorState message={per.error} onRetry={per.reload} />}
        {per.data && (<table className="min-w-full text-sm"><thead><tr><th className="th">Measure</th><th className="th">A: {fmtDate(per.data.period_a.start)} – {fmtDate(per.data.period_a.end)}</th><th className="th">B: {fmtDate(per.data.period_b.start)} – {fmtDate(per.data.period_b.end)}</th><th className="th">B − A</th></tr></thead><tbody>
          {([["Average max (°C)", "avg_temp_max_c"], ["Average min (°C)", "avg_temp_min_c"], ["Average apparent max (°C)", "avg_apparent_max_c"], ["Total precipitation (mm)", "total_precipitation_mm"], ["Average max wind (km/h)", "avg_wind_speed_max_kmh"], [`Hot days (≥ ${per.data.hot_day_threshold_c} °C)`, "hot_days"]] as [string, string][]).map(([label, key]) => (
            <tr key={key} className="border-t border-slate-100 dark:border-navy-800"><td className="td font-medium">{label}</td><td className="td">{per.data.period_a[key]}</td><td className="td">{per.data.period_b[key]}</td>
              <td className="td">{per.data.delta_b_minus_a[key] === null ? "—" : `${per.data.delta_b_minus_a[key] > 0 ? "+" : ""}${per.data.delta_b_minus_a[key]}`}</td></tr>))}</tbody></table>)}</Card>)}

      {tab === "Heatwave events" && (<Card title={`${cityName}: heatwave events`} actions={<DataBadge type="derived" />}>
        {hw.loading && <Spinner />}{hw.error && <ErrorState message={hw.error} onRetry={hw.reload} />}
        {hw.data && (<>
          <Notice>
            <strong>Definition used:</strong> a heatwave day has max temperature ≥ {hw.data.definition.hot_day_threshold_c} °C and either ≥ {hw.data.definition.min_departure_c} °C above the {hw.data.definition.normal}, or ≥ {hw.data.definition.absolute_tmax_c} °C. An event needs ≥ {hw.data.definition.min_consecutive_days} consecutive days; “Severe” if departure ≥ {hw.data.definition.severe_departure_c} °C or max ≥ {hw.data.definition.severe_absolute_tmax_c} °C. {hw.data.definition.note}
          </Notice>
          <p className="my-3 text-sm"><strong>{hw.data.total_events}</strong> event(s) found.</p>
          {hw.data.total_events === 0 ? <EmptyState>No events meet this definition for the selected city and dates.</EmptyState> : (<>
            <BarsChart data={hw.data.events_per_year} xKey="year" series={[{ key: "events", name: "Events per year", color: "#C53030" }]} />
            <div className="mt-4 max-h-96 overflow-auto"><table className="min-w-full text-sm"><thead><tr>{["Start", "End", "Days", "Peak max", "Mean max", "Max departure", "Severity"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
              {hw.data.events.map((e: { start: string; end: string; days: number; peak_tmax_c: number; mean_tmax_c: number; max_departure_c: number; severity: string }) => (
                <tr key={e.start} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{fmtDate(e.start)}</td><td className="td">{fmtDate(e.end)}</td><td className="td">{e.days}</td>
                  <td className="td">{e.peak_tmax_c} °C</td><td className="td">{e.mean_tmax_c} °C</td><td className="td">+{e.max_departure_c} °C</td><td className="td">{e.severity}</td></tr>))}</tbody></table></div>
          </>)}
        </>)}</Card>)}

      {tab === "Data quality" && (<Card title="Dataset data-quality summary">
        {dq.loading && <Spinner />}{dq.error && <ErrorState message={dq.error} onRetry={dq.reload} />}
        {dq.data && (<div className="space-y-3">
          <p className="text-sm">{dq.data.total_rows.toLocaleString()} rows checked. {dq.data.all_checks_passed ? "All checks passed." : "Some checks reported issues."}</p>
          <table className="min-w-full text-sm"><tbody>{dq.data.checks.map((c: { check: string; issues: number }) => (
            <tr key={c.check} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{c.check}</td><td className="td font-semibold">{c.issues}</td></tr>))}</tbody></table>
          {dq.data.notes.map((n: string) => <Notice key={n}>{n}</Notice>)}
          <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr>{["City", "First date", "Last date", "Days observed", "Missing days"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
            {dq.data.coverage.map((r: { city: string; first_date: string; last_date: string; observed_days: number; missing_days: number }) => (
              <tr key={r.city} className="border-t border-slate-100 dark:border-navy-800"><td className="td font-medium">{r.city}</td><td className="td">{r.first_date}</td><td className="td">{r.last_date}</td><td className="td">{r.observed_days}</td><td className="td">{r.missing_days}</td></tr>))}</tbody></table></div>
        </div>)}</Card>)}
    </div>
  );
}
