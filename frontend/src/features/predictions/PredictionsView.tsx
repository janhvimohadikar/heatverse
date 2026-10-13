import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CitySelect } from "../../components/CitySelect";
import { Card, DataBadge, ErrorState, Notice, PageHeader, RiskBadge, ScoreBar, Spinner, fmt, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useCities } from "../../hooks/useCities";
import { api } from "../../services/endpoints";
import type { PredictionResult } from "../../types";

export default function PredictionsView() {
  const { cities, loading, error } = useCities();
  const [params] = useSearchParams();
  const [cityId, setCityId] = useState<number | null>(null);
  const [horizon, setHorizon] = useState(1);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const status = useAsync(() => api.modelStatus(), []);
  const history = useAsync(() => api.predictionHistory(1, 20), []);
  const profile = useAsync(() => api.getProfile(), []);

  useEffect(() => {
    if (!cities.length || cityId !== null) return;
    const q = Number(params.get("city"));
    setCityId(cities.find((c) => c.city_id === q)?.city_id ?? profile.data?.home_city_id ?? cities[0].city_id);
  }, [cities, profile.data]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run() {
    if (cityId === null) return;
    setBusy(true); setErr(null);
    try { setResult(await api.predict(cityId, horizon)); history.reload(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Prediction failed."); } finally { setBusy(false); }
  }
  async function clear() {
    if (!window.confirm("Delete your saved prediction history?")) return;
    await api.clearPredictionHistory(); history.reload();
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Risk assessment" title="Heatwave prediction" subtitle="Estimate heat risk for a city and day, personalised with the age, activity and work details in your profile." />
      {status.data && <Notice tone={status.data.mode === "demo" ? "demo" : "info"}><strong>{status.data.mode === "demo" ? "DEMO MODE." : "Trained model connected."}</strong> {status.data.message}</Notice>}

      <Card title="New prediction">
        <div className="grid gap-3 sm:grid-cols-3">
          <CitySelect cities={cities} value={cityId} onChange={setCityId} />
          <div><label className="label" htmlFor="h">Days ahead: {horizon}</label><input id="h" type="range" min={0} max={14} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="w-full" /></div>
          <div className="flex items-end"><button className="btn-primary w-full" onClick={run} disabled={busy || cityId === null}>{busy ? "Calculating…" : "Run prediction"}</button></div>
        </div>
        {err && <div className="mt-3"><ErrorState message={err} /></div>}
      </Card>

      {result && (
        <Card title={`${result.city.name}: ${fmtDate(result.target_date)} (${result.horizon_days} day${result.horizon_days === 1 ? "" : "s"} ahead)`}
          actions={<DataBadge type={result.model.is_demo ? "demo" : "predicted"} />}>
          {result.model.is_demo && <Notice tone="demo"><strong>{result.model.label}.</strong> {result.notes[0]}</Notice>}
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between"><span className="text-sm font-medium">Heat-risk score</span><RiskBadge category={result.risk.category} score={result.risk.score} /></div>
              <ScoreBar score={result.risk.score} category={result.risk.category} />
              <div className="flex items-center justify-between pt-2"><span className="text-sm font-medium">Personal score</span><RiskBadge category={result.personal.personal_category} score={result.personal.personal_score} /></div>
              <ScoreBar score={result.personal.personal_score} category={result.personal.personal_category} />
              {result.personal.adjustments.length > 0
                ? <ul className="list-disc pl-5 text-xs text-slate-500">{result.personal.adjustments.map((a) => <li key={a.label}>+{a.points}: {a.label}</li>)}</ul>
                : <p className="text-xs text-slate-500">No personal adjustments apply (add age/work/activity in your profile).</p>}
            </div>
            <div className="space-y-1 text-sm">
              <p><span className="text-slate-500">Expected max:</span> {fmt(result.expected.temp_max_c, 1, " °C")}</p>
              <p><span className="text-slate-500">Expected min:</span> {fmt(result.expected.temp_min_c, 1, " °C")}</p>
              <p><span className="text-slate-500">Expected apparent max:</span> {fmt(result.expected.apparent_max_c, 1, " °C")}</p>
              <p><span className="text-slate-500">Model confidence:</span> {result.confidence === null ? "Not available (no model confidence measure exists)" : result.confidence}</p>
              {result.heatwave_probability !== null && <p><span className="text-slate-500">Model heatwave probability:</span> {(result.heatwave_probability * 100).toFixed(0)}%</p>}
              {"years_with_at_least_one_hot_day" in result.context && (
                <p className="pt-1 text-xs text-slate-500">Historical context: in {String(result.context.years_with_at_least_one_hot_day)} of {String(result.context.years_in_record)} years this time of year had at least one day ≥ {String(result.context.hot_day_threshold_c)} °C. This is a historical frequency, not a forecast probability.</p>
              )}
            </div>
          </div>
          <h3 className="mt-4 text-sm font-semibold">Why this score?</h3>
          <p className="text-xs text-slate-500">{result.explanation.kind}</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{result.explanation.lines.map((l, i) => <li key={i}>{l}</li>)}</ul>
          <h3 className="mt-4 text-sm font-semibold">Personalised recommendations</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{result.recommendations.map((l, i) => <li key={i}>{l}</li>)}</ul>
          <p className="mt-3 text-xs text-slate-500">{result.disclaimer}</p>
        </Card>
      )}

      <Card title="Prediction history" subtitle="Saved on the server for your account" actions={<button className="btn-secondary" onClick={clear}>Clear history</button>}>
        {history.loading && <Spinner />}{history.error && <ErrorState message={history.error} onRetry={history.reload} />}
        {history.data && (history.data.items.length === 0 ? <p className="text-sm text-slate-500">No predictions yet. Run one above.</p> : (
          <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr>{["Created", "City", "For date", "Score", "Personal", "Type", "Recommendation"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
            {history.data.items.map((p) => (<tr key={p.prediction_id} className="border-t border-slate-100 dark:border-navy-800">
              <td className="td">{fmtDate(p.created_at)}</td><td className="td font-medium">{p.city}</td><td className="td">{fmtDate(p.target_date)}</td>
              <td className="td"><RiskBadge category={p.risk_category} score={p.risk_score} /></td><td className="td"><RiskBadge category={p.personal_category} score={p.personal_score} /></td>
              <td className="td">{p.is_demo ? <DataBadge type="demo" /> : <DataBadge type="predicted" />}</td><td className="td max-w-xs truncate" title={p.recommendation ?? ""}>{p.recommendation ?? "—"}</td></tr>))}</tbody></table></div>))}
      </Card>
    </div>
  );
}
