import { useEffect, useMemo, useRef, useState } from "react";
import type { GeoJsonObject } from "geojson";
import { DataBadge, ErrorState, Notice, RiskBadge, Spinner, fmt, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { api } from "../../services/endpoints";
import type { MapFeature, MapMode, RiskCategory } from "../../types";
import CityPanel from "./CityPanel";
import { CATEGORIES, RISK_COLORS, formatLayerValue, geoStateName, normState } from "./colors";
import Legend from "./Legend";
import MapCanvas from "./MapCanvas";

const DAY = 86_400_000;
const toDay = (iso: string) => Math.round(Date.parse(iso + "T00:00:00Z") / DAY);
const fromDay = (n: number) => new Date(n * DAY).toISOString().slice(0, 10);
const clampDate = (iso: string, lo: string, hi: string) => (iso < lo ? lo : iso > hi ? hi : iso);

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export default function MapView() {
  const layersQ = useAsync(() => api.mapLayers().then((r) => r.items), []);
  const datesQ = useAsync(() => api.mapDates(), []);

  const [mode, setMode] = useState<MapMode>("historical");
  const [layerKey, setLayerKey] = useState("risk");
  const [date, setDate] = useState<string>("");
  const [horizon, setHorizon] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [resetSignal, setResetSignal] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // filters
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [cats, setCats] = useState<Set<RiskCategory>>(new Set(CATEGORIES));
  const [tMin, setTMin] = useState("");
  const [tMax, setTMax] = useState("");

  // layers on the map
  const [showSurface, setShowSurface] = useState(false);
  const [showBoundaries, setShowBoundaries] = useState(false);
  const [boundaries, setBoundaries] = useState<GeoJsonObject | null>(null);
  const [boundaryError, setBoundaryError] = useState<string | null>(null);

  // timeline / compare
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(1);
  const [playEnd, setPlayEnd] = useState("");
  const [compare, setCompare] = useState(false);
  const [dateB, setDateB] = useState("");

  const first = datesQ.data?.first_date ?? "2000-01-01";
  const last = datesQ.data?.last_date ?? "2024-12-31";
  useEffect(() => { if (datesQ.data && !date) { setDate(datesQ.data.last_date); setDateB(datesQ.data.first_date); setPlayEnd(datesQ.data.last_date); } }, [datesQ.data, date]);

  const debouncedDate = useDebounced(date, 200);
  const layers = layersQ.data ?? [];
  const layer = layers.find((l) => l.key === layerKey) ?? layers[0];
  const effectiveLayerKey = layer && layer.modes.includes(mode) ? layer.key : "risk";

  const risk = useAsync(
    () => api.mapRisk({ mode, layer: effectiveLayerKey, date: mode === "historical" ? debouncedDate : undefined, horizon_days: horizon }),
    [mode, effectiveLayerKey, debouncedDate, horizon], mode === "demo_prediction" || !!debouncedDate);
  const riskB = useAsync(() => api.mapRisk({ mode: "historical", layer: effectiveLayerKey, date: dateB }), [effectiveLayerKey, dateB],
    compare && mode === "historical" && !!dateB);
  const surface = useAsync(() => api.mapSurface(effectiveLayerKey, debouncedDate), [effectiveLayerKey, debouncedDate],
    showSurface && mode === "historical" && !!debouncedDate);

  // optional state boundaries (file is not shipped - see docs/map-data-sources.md)
  useEffect(() => {
    if (!showBoundaries || boundaries || boundaryError) return;
    fetch("/geo/india_states.geojson")
      .then((r) => { if (!r.ok) throw new Error("not found"); return r.json(); })
      .then((g) => setBoundaries(g as GeoJsonObject))
      .catch(() => setBoundaryError("State boundary file not installed. Add frontend/public/geo/india_states.geojson (see docs/map-data-sources.md)."));
  }, [showBoundaries, boundaries, boundaryError]);

  // playback: advance only after the previous frame has loaded
  useEffect(() => {
    if (!playing || mode !== "historical" || risk.loading) return;
    const t = setTimeout(() => {
      const next = fromDay(toDay(date) + step);
      if (next > (playEnd || last)) { setPlaying(false); return; }
      setDate(next);
    }, 700);
    return () => clearTimeout(t);
  }, [playing, risk.loading, date, step, playEnd, last, mode]);

  // full screen
  useEffect(() => {
    const h = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", h);
    return () => document.removeEventListener("fullscreenchange", h);
  }, []);
  function toggleFullscreen() {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void wrapRef.current?.requestFullscreen?.().catch(() => undefined);
  }

  const data = risk.data;
  const all: MapFeature[] = data?.features ?? [];
  const states = useMemo(() => Array.from(new Set(all.map((f) => f.state).filter(Boolean) as string[])).sort(), [all]);

  const visible = useMemo(() => all.filter((f) => {
    if (search && !f.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (stateFilter && f.state !== stateFilter) return false;
    if (!f.missing && f.risk.category && !cats.has(f.risk.category)) return false;
    const t = f.values.temp_max_c;
    if (tMin !== "" && (t === null || t === undefined || t < Number(tMin))) return false;
    if (tMax !== "" && (t === null || t === undefined || t > Number(tMax))) return false;
    return true;
  }), [all, search, stateFilter, cats, tMin, tMax]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { Low: 0, Moderate: 0, High: 0, Extreme: 0, "No data": 0 };
    visible.forEach((f) => { c[f.missing || !f.risk.category ? "No data" : f.risk.category] += 1; });
    return c;
  }, [visible]);

  // state choropleth colours: the highest-scoring city in each state
  const stateColors = useMemo(() => {
    const best: Record<string, MapFeature> = {};
    visible.forEach((f) => {
      const k = normState(f.state);
      if (!f.missing && f.risk.score !== null && (!best[k] || (best[k].risk.score ?? 0) < f.risk.score)) best[k] = f;
    });
    const out: Record<string, string> = {};
    Object.entries(best).forEach(([k, f]) => { if (f.risk.category) out[k] = RISK_COLORS[f.risk.category]; });
    return out;
  }, [visible]);
  const unmatchedStates = useMemo(() => {
    if (!boundaries || !("features" in boundaries)) return [];
    const names = new Set((boundaries as unknown as { features: { properties: Record<string, unknown> }[] }).features.map((f) => geoStateName(f.properties)));
    return Array.from(new Set(all.map((f) => f.state).filter((s): s is string => !!s))).filter((s) => !names.has(normState(s)));
  }, [boundaries, all]);

  const selected = all.find((f) => f.city_id === selectedId) ?? null;
  const dayIndex = date ? toDay(date) - toDay(first) : 0;
  const totalDays = toDay(last) - toDay(first);

  function select(id: number) {
    setSelectedId(id);
    setTimeout(() => panelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
  }
  function toggleCat(c: RiskCategory) {
    setCats((prev) => { const n = new Set(prev); if (n.has(c)) n.delete(c); else n.add(c); return n; });
  }
  const shiftDate = (days: number) => setDate((d) => clampDate(fromDay(toDay(d) + days), first, last));

  if (layersQ.loading || datesQ.loading) return <Spinner label="Loading map configuration…" />;
  if (layersQ.error || datesQ.error) return <ErrorState message={layersQ.error ?? datesQ.error ?? "Failed to load."} onRetry={() => { layersQ.reload(); datesQ.reload(); }} />;
  if (!layer) return <ErrorState message="The API returned no map layers." />;

  const unavailableReason = (l: typeof layers[number]) => (!l.available ? l.reason : !l.modes.includes(mode) ? "Not supported in demo-prediction mode: the underlying data does not exist for it." : null);

  return (
    <div ref={wrapRef} className={`grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)] ${fullscreen ? "h-screen overflow-auto bg-slate-50 p-3 dark:bg-navy-950" : ""}`}>
      {/* ---------------- controls ---------------- */}
      <div className="space-y-4">
        <div className="card space-y-3">
          <div>
            <span className="label">Data mode</span>
            <div className="grid grid-cols-2 gap-1" role="group" aria-label="Data mode">
              {(["historical", "demo_prediction"] as MapMode[]).map((m) => (
                <button key={m} className={mode === m ? "btn-primary" : "btn-secondary"} aria-pressed={mode === m}
                  onClick={() => { setMode(m); setPlaying(false); }}>{m === "historical" ? "Historical" : "Demo prediction"}</button>
              ))}
            </div>
            {mode === "demo_prediction" && (
              <div className="mt-2 space-y-2">
                <Notice tone="demo">DEMO: climatology baseline, not a trained model.</Notice>
                <label className="label" htmlFor="horizon">Days ahead: {horizon}</label>
                <input id="horizon" type="range" min={0} max={14} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="w-full" />
              </div>
            )}
          </div>

          <div>
            <label className="label" htmlFor="layer">Layer</label>
            <select id="layer" className="input" value={effectiveLayerKey} onChange={(e) => setLayerKey(e.target.value)}>
              {layers.map((l) => {
                const why = unavailableReason(l);
                return <option key={l.key} value={l.key} disabled={!!why}>{l.label}{why ? " (unavailable)" : ""}</option>;
              })}
            </select>
            <p className="mt-1 text-xs text-slate-500">{layer.description}</p>
            {layers.filter((l) => unavailableReason(l)).map((l) => (
              <p key={l.key} className="mt-1 text-xs text-slate-500"><strong>{l.label}:</strong> {unavailableReason(l)}</p>
            ))}
          </div>

          <div className="space-y-1 text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={showSurface} disabled={mode !== "historical"} onChange={(e) => setShowSurface(e.target.checked)} /> Interpolated heat surface <DataBadge type="interpolated" /></label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={showBoundaries} onChange={(e) => setShowBoundaries(e.target.checked)} /> State boundaries (choropleth)</label>
            {showBoundaries && boundaryError && <p className="text-xs text-red-700 dark:text-red-300">{boundaryError}</p>}
            {showBoundaries && boundaries && unmatchedStates.length > 0 && <p className="text-xs text-slate-500">No matching boundary name for: {unmatchedStates.join(", ")}.</p>}
          </div>
        </div>

        <div className="card space-y-3">
          <h2 className="text-sm font-semibold">Filters</h2>
          <div><label className="label" htmlFor="search">City search</label><input id="search" className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="e.g. Delhi" /></div>
          <div><label className="label" htmlFor="state">State / region</label>
            <select id="state" className="input" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
              <option value="">All states</option>{states.map((s) => <option key={s}>{s}</option>)}
            </select></div>
          <fieldset><legend className="label">Risk category</legend>
            <div className="flex flex-wrap gap-2">{CATEGORIES.map((c) => (
              <label key={c} className="flex items-center gap-1 text-sm"><input type="checkbox" checked={cats.has(c)} onChange={() => toggleCat(c)} />
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: RISK_COLORS[c] }} />{c}</label>))}</div></fieldset>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="label" htmlFor="tmin">Tmax ≥ (°C)</label><input id="tmin" type="number" className="input" value={tMin} onChange={(e) => setTMin(e.target.value)} /></div>
            <div><label className="label" htmlFor="tmax">Tmax ≤ (°C)</label><input id="tmax" type="number" className="input" value={tMax} onChange={(e) => setTMax(e.target.value)} /></div>
          </div>
          <button className="btn-secondary w-full" onClick={() => { setSearch(""); setStateFilter(""); setCats(new Set(CATEGORIES)); setTMin(""); setTMax(""); }}>Clear filters</button>
        </div>

        <div className="card">
          <h2 className="mb-2 text-sm font-semibold">Locations by risk ({visible.length} of {all.length} shown)</h2>
          <ul className="grid grid-cols-2 gap-2 text-sm">
            {[...CATEGORIES, "No data" as const].map((c) => (
              <li key={c} className="flex items-center justify-between rounded border border-slate-200 px-2 py-1 dark:border-navy-700">
                <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: c === "No data" ? "#94A3B8" : RISK_COLORS[c] }} />{c}</span><strong>{counts[c]}</strong>
              </li>))}
          </ul>
        </div>

        <Legend layer={layer} interpolated={showSurface && !!surface.data?.available} />
      </div>

      {/* ---------------- map + details ---------------- */}
      <div className="min-w-0 space-y-4">
        <div className="card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <strong>{mode === "historical" ? fmtDate(data?.date ?? date) : `Demo prediction for ${fmtDate(data?.date)}`}</strong>
              {data && <DataBadge type={data.data_type} />}
              {risk.loading && <span className="text-xs text-slate-500">updating…</span>}
            </div>
            <div className="flex gap-2">
              <button className="btn-secondary" onClick={() => setResetSignal((n) => n + 1)} title="Fit the whole of India in view">Fit India</button>
              <button className="btn-secondary" onClick={() => { setSelectedId(null); setResetSignal((n) => n + 1); }}>Reset view</button>
              <button className="btn-secondary" onClick={toggleFullscreen}>{fullscreen ? "Exit full screen" : "Full screen"}</button>
            </div>
          </div>
          {data && <p className="mt-1 text-xs text-slate-500">{data.data_type_note} {data.scoring.disclaimer}</p>}
        </div>

        {risk.error && <ErrorState message={risk.error} onRetry={risk.reload} />}
        {surface.data && !surface.data.available && showSurface && <Notice>{surface.data.reason}</Notice>}
        {surface.data?.available && showSurface && <Notice tone="demo">{surface.data.warning}</Notice>}
        {surface.error && <ErrorState message={surface.error} />}

        <div className={`overflow-hidden rounded-lg border border-slate-200 dark:border-navy-700 ${fullscreen ? "h-[65vh]" : "h-[420px] sm:h-[520px]"}`}>
          {data ? (
            <MapCanvas features={visible} layer={data.layer} selectedId={selectedId} onSelect={select}
              surface={showSurface && mode === "historical" ? surface.data : null}
              boundaries={boundaries} stateColors={stateColors} showBoundaries={showBoundaries && !!boundaries} resetSignal={resetSignal} />
          ) : (risk.loading ? <Spinner label="Loading map data…" /> : <p className="p-4 text-sm text-slate-500">No data to display.</p>)}
        </div>
        {data && visible.length === 0 && <Notice>No locations match the current filters.</Notice>}

        {/* timeline */}
        {mode === "historical" && (
          <div className="card space-y-3">
            <h2 className="text-sm font-semibold">Timeline <span className="font-normal text-slate-500">({fmtDate(first)} – {fmtDate(last)})</span></h2>
            <input type="range" min={0} max={totalDays} value={Math.max(0, Math.min(totalDays, dayIndex))} className="w-full"
              aria-label="Select date" onChange={(e) => setDate(fromDay(toDay(first) + Number(e.target.value)))} />
            <div className="flex flex-wrap items-end gap-2">
              <div><label className="label" htmlFor="date">Date</label>
                <input id="date" type="date" className="input" min={first} max={last} value={date} onChange={(e) => e.target.value && setDate(clampDate(e.target.value, first, last))} /></div>
              <button className="btn-secondary" onClick={() => shiftDate(-step)} aria-label="Step backward">◀ Back</button>
              <button className={playing ? "btn-danger" : "btn-primary"} onClick={() => setPlaying((p) => !p)}>{playing ? "❚❚ Pause" : "▶ Play"}</button>
              <button className="btn-secondary" onClick={() => shiftDate(step)} aria-label="Step forward">Forward ▶</button>
              <div><label className="label" htmlFor="step">Step</label>
                <select id="step" className="input" value={step} onChange={(e) => setStep(Number(e.target.value))}>
                  <option value={1}>1 day</option><option value={7}>7 days</option><option value={30}>30 days</option><option value={365}>1 year</option></select></div>
              <div><label className="label" htmlFor="pend">Play until</label>
                <input id="pend" type="date" className="input" min={first} max={last} value={playEnd} onChange={(e) => e.target.value && setPlayEnd(clampDate(e.target.value, first, last))} /></div>
            </div>
            <div className="flex flex-wrap items-end gap-3 border-t border-slate-200 pt-3 dark:border-navy-700">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} /> Compare with another date</label>
              {compare && <div><label className="label" htmlFor="dateb">Compare date (B)</label>
                <input id="dateb" type="date" className="input" min={first} max={last} value={dateB} onChange={(e) => e.target.value && setDateB(clampDate(e.target.value, first, last))} /></div>}
            </div>
            {compare && (
              <div className="overflow-x-auto">
                {riskB.loading && <Spinner label="Loading comparison…" />}
                {riskB.error && <ErrorState message={riskB.error} />}
                {riskB.data && data && (
                  <table className="min-w-full text-sm">
                    <thead><tr><th className="th">City</th><th className="th">{fmtDate(date)} (A)</th><th className="th">{fmtDate(dateB)} (B)</th><th className="th">B − A</th></tr></thead>
                    <tbody>{visible.map((f) => {
                      const b = riskB.data!.features.find((x) => x.city_id === f.city_id);
                      const d = f.layer_value !== null && b && b.layer_value !== null ? b.layer_value - f.layer_value : null;
                      return (<tr key={f.city_id} className="border-t border-slate-100 dark:border-navy-800">
                        <td className="td font-medium">{f.name}</td><td className="td">{formatLayerValue(data.layer, f)}</td>
                        <td className="td">{b ? formatLayerValue(data.layer, b) : "No data"}</td><td className="td">{d === null ? "—" : `${d > 0 ? "+" : ""}${d.toFixed(1)}`}</td></tr>);
                    })}</tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        )}

        {/* accessible list (keyboard / screen-reader alternative to the map markers) */}
        <div className="card">
          <h2 className="mb-2 text-sm font-semibold">Locations</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr><th className="th">City</th><th className="th">State</th><th className="th">Tmax</th><th className="th">Risk</th><th className="th"><span className="sr-only">Details</span></th></tr></thead>
              <tbody>{visible.map((f) => (
                <tr key={f.city_id} className={`border-t border-slate-100 dark:border-navy-800 ${f.city_id === selectedId ? "bg-orange-50 dark:bg-navy-800" : ""}`}>
                  <td className="td font-medium">{f.name}</td><td className="td">{f.state ?? "—"}</td>
                  <td className="td">{fmt(f.values.temp_max_c, 1, " °C")}</td>
                  <td className="td"><RiskBadge category={f.missing ? null : f.risk.category} score={f.risk.score} /></td>
                  <td className="td"><button className="btn-secondary" onClick={() => select(f.city_id)}>Details</button></td></tr>))}</tbody>
            </table>
          </div>
        </div>

        <div ref={panelRef}>
          {selected ? <CityPanel feature={selected} date={data?.date ?? date} mode={mode} onClose={() => setSelectedId(null)} />
            : <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-navy-600">Click a city marker or a table row to see its details.</p>}
        </div>
      </div>
    </div>
  );
}
