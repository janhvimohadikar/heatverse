import { useState, type FormEvent } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataBadge, ErrorState, Notice, PageHeader, Spinner, StatCard, fmtDate } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useCities } from "../../hooks/useCities";
import { api } from "../../services/endpoints";

const TABS = ["Overview", "Users", "Dataset & quality", "Alerts", "Safety resources", "Audit log"] as const;
type Tab = (typeof TABS)[number];
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Row = Record<string, any>;

function Overview() {
  const q = useAsync(() => api.adminOverview(), []);
  const h = useAsync(() => api.health(), []);
  if (q.loading) return <Spinner />;
  if (q.error) return <ErrorState message={q.error} onRetry={q.reload} />;
  const o = q.data as Row;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Users" value={o.users.total} hint={`${o.users.admins} admin(s), ${o.users.inactive} inactive`} />
        <StatCard label="Predictions" value={o.predictions.total} hint={`${o.predictions.demo} demo`} />
        <StatCard label="Weather records" value={o.dataset ? o.dataset.observations.toLocaleString() : "—"} hint={o.dataset ? `${o.dataset.cities} cities` : "Not imported"} />
        <StatCard label="Active alerts" value={o.alerts_active} />
      </div>
      <Card title="Application health">
        {h.data && (<ul className="grid gap-1 text-sm sm:grid-cols-2">
          <li>API status: <strong>{h.data.status}</strong></li><li>Database: <strong>{h.data.database}</strong></li>
          <li>Prediction mode: <strong>{h.data.model.mode}</strong> ({h.data.model.model_name})</li>
          <li>Live weather: <strong>{h.data.live_weather_enabled ? "enabled" : "disabled"}</strong></li>
          <li>Hospital lookup: <strong>{h.data.hospital_lookup_enabled ? "enabled" : "disabled"}</strong></li>
          <li>Historical data: <strong>{typeof h.data.historical_data === "string" ? h.data.historical_data : `${h.data.historical_data?.first_date} to ${h.data.historical_data?.last_date}`}</strong></li></ul>)}
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Predictions per day (last 30 days)">
          {o.predictions.per_day_last_30.length === 0 ? <p className="text-sm text-slate-500">No predictions yet.</p> : (
            <div className="h-56" role="img" aria-label="Predictions per day"><ResponsiveContainer width="100%" height="100%"><LineChart data={o.predictions.per_day_last_30}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="date" fontSize={10} /><YAxis allowDecimals={false} /><Tooltip /><Line dataKey="count" stroke="#EA580C" strokeWidth={2} /></LineChart></ResponsiveContainer></div>)}
        </Card>
        <Card title="Predictions by risk category">
          {o.predictions.by_category.length === 0 ? <p className="text-sm text-slate-500">No predictions yet.</p> : (
            <div className="h-56" role="img" aria-label="Predictions by category"><ResponsiveContainer width="100%" height="100%"><BarChart data={o.predictions.by_category}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="category" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#2A4D80" /></BarChart></ResponsiveContainer></div>)}
        </Card>
      </div>
      <Card title="Predictions by city">
        {o.predictions.by_city.length === 0 ? <p className="text-sm text-slate-500">No predictions yet.</p> : <table className="min-w-full text-sm"><tbody>{o.predictions.by_city.map((r: Row) => <tr key={r.city} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{r.city}</td><td className="td font-semibold">{r.count}</td></tr>)}</tbody></table>}
      </Card>
    </div>
  );
}

function Users() {
  const [page, setPage] = useState(1);
  const [term, setTerm] = useState("");
  const q = useAsync(() => api.adminUsers(page, term || undefined), [page, term]);
  const [err, setErr] = useState<string | null>(null);
  async function update(id: number, body: { is_active?: boolean; role?: "user" | "admin" }) {
    setErr(null);
    try { await api.adminUpdateUser(id, body); q.reload(); } catch (e) { setErr(e instanceof Error ? e.message : "Failed."); }
  }
  return (
    <Card title="Users" actions={<input aria-label="Search by email" className="input w-48" placeholder="Search email…" value={term} onChange={(e) => { setTerm(e.target.value); setPage(1); }} />}>
      {err && <ErrorState message={err} />}{q.loading && <Spinner />}{q.error && <ErrorState message={q.error} onRetry={q.reload} />}
      {q.data && (<><div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr>{["Email", "Name", "Role", "Status", "Joined", "Last login", ""].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
        {q.data.items.map((u: Row) => (<tr key={u.user_id} className="border-t border-slate-100 dark:border-navy-800"><td className="td font-medium">{u.email}</td><td className="td">{u.full_name ?? "—"}</td><td className="td">{u.role}</td>
          <td className="td">{u.is_active ? "Active" : "Deactivated"}</td><td className="td">{fmtDate(u.created_at)}</td><td className="td">{u.last_login_at ? fmtDate(u.last_login_at) : "—"}</td>
          <td className="td whitespace-nowrap"><button className="btn-secondary mr-1" onClick={() => update(u.user_id, { is_active: !u.is_active })}>{u.is_active ? "Deactivate" : "Activate"}</button>
            <button className="btn-secondary" onClick={() => update(u.user_id, { role: u.role === "admin" ? "user" : "admin" })}>{u.role === "admin" ? "Make user" : "Make admin"}</button></td></tr>))}</tbody></table></div>
        <div className="mt-3 flex items-center gap-2 text-sm"><button className="btn-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page} · {q.data.total} user(s)</span><button className="btn-secondary" disabled={page * q.data.page_size >= q.data.total} onClick={() => setPage(page + 1)}>Next</button></div></>)}
    </Card>
  );
}

function Dataset() {
  const s = useAsync(() => api.adminImportStatus(), []);
  const dq = useAsync(() => api.adminDataQuality(), []);
  return (
    <div className="space-y-4">
      <Notice>Historical weather records are read-only in the application — there is no API route that edits them. To refresh the data, re-run <code>scripts/import_excel.py</code>.</Notice>
      <Card title="Dataset coverage" actions={<DataBadge type="observed" />}>
        {s.loading && <Spinner />}{s.error && <ErrorState message={s.error} onRetry={s.reload} />}
        {s.data && (<><p className="text-sm">{s.data.coverage.observations.toLocaleString()} observations · {s.data.coverage.cities} cities · {s.data.coverage.first_date} to {s.data.coverage.last_date}</p>
          <h3 className="mt-3 text-sm font-semibold">Import history</h3>
          <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr>{["When (UTC)", "Source file", "Rows read", "Rows inserted", "SHA-256 (first 12)"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
            {s.data.imports.map((r: Row) => <tr key={r.import_id} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{r.imported_at_utc}</td><td className="td">{r.source_file}</td><td className="td">{r.rows_read}</td><td className="td">{r.rows_inserted}</td><td className="td font-mono text-xs">{String(r.source_sha256).slice(0, 12)}</td></tr>)}</tbody></table></div></>)}
      </Card>
      <Card title="Data-quality checks">
        {dq.loading && <Spinner />}{dq.error && <ErrorState message={dq.error} onRetry={dq.reload} />}
        {dq.data && (<><p className="mb-2 text-sm">{dq.data.all_checks_passed ? "All checks passed." : "Some checks reported issues."}</p>
          <table className="min-w-full text-sm"><tbody>{dq.data.checks.map((c: Row) => <tr key={c.check} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{c.check}</td><td className="td font-semibold">{c.issues}</td></tr>)}</tbody></table>
          {dq.data.notes.map((n: string) => <p key={n} className="mt-2 text-xs text-slate-500">{n}</p>)}</>)}
      </Card>
    </div>
  );
}

function Alerts() {
  const { cities } = useCities();
  const q = useAsync(() => api.adminAlerts().then((r) => r.items), []);
  const [f, setF] = useState({ title: "", message: "", level: "info", city_id: "" });
  const [err, setErr] = useState<string | null>(null);
  async function create(e: FormEvent) {
    e.preventDefault(); setErr(null);
    try { await api.adminCreateAlert({ title: f.title, message: f.message, level: f.level, city_id: f.city_id ? Number(f.city_id) : null }); setF({ title: "", message: "", level: "info", city_id: "" }); q.reload(); }
    catch (e2) { setErr(e2 instanceof Error ? e2.message : "Failed."); }
  }
  return (
    <div className="space-y-4">
      <Card title="Create a notice" subtitle="Shown on user dashboards. These are project notices, never presented as official government warnings.">
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
          <div><label className="label" htmlFor="at">Title</label><input id="at" className="input" required minLength={3} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-2"><div><label className="label" htmlFor="al">Level</label><select id="al" className="input" value={f.level} onChange={(e) => setF({ ...f, level: e.target.value })}><option value="info">Info</option><option value="advisory">Advisory</option><option value="warning">Warning</option></select></div>
            <div><label className="label" htmlFor="ac">City</label><select id="ac" className="input" value={f.city_id} onChange={(e) => setF({ ...f, city_id: e.target.value })}><option value="">All cities</option>{cities.map((c) => <option key={c.city_id} value={c.city_id}>{c.name}</option>)}</select></div></div>
          <div className="sm:col-span-2"><label className="label" htmlFor="am">Message</label><textarea id="am" className="input" rows={3} required minLength={3} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></div>
          <div className="sm:col-span-2"><button className="btn-primary">Publish notice</button></div>
        </form>{err && <div className="mt-2"><ErrorState message={err} /></div>}
      </Card>
      <Card title="Existing notices">
        {q.loading && <Spinner />}{q.error && <ErrorState message={q.error} onRetry={q.reload} />}
        {q.data?.length === 0 && <p className="text-sm text-slate-500">No notices.</p>}
        <ul className="space-y-2">{q.data?.map((a) => (<li key={a.alert_id} className="flex items-start justify-between gap-2 rounded border border-slate-200 p-2 text-sm dark:border-navy-700">
          <div><strong>{a.title}</strong> <span className="text-xs text-slate-500">({a.level}{a.city_id ? `, ${cities.find((c) => c.city_id === a.city_id)?.name ?? a.city_id}` : ", all cities"})</span><br />{a.message}</div>
          <button className="btn-danger" onClick={async () => { await api.adminDeleteAlert(a.alert_id); q.reload(); }}>Delete</button></li>))}</ul>
      </Card>
    </div>
  );
}

function Resources() {
  const { cities } = useCities();
  const q = useAsync(() => api.adminResources(), []);
  const [f, setF] = useState({ name: "", phone: "", address: "", source_note: "", city_id: "" });
  const [err, setErr] = useState<string | null>(null);
  async function create(e: FormEvent) {
    e.preventDefault(); setErr(null);
    try { await api.adminCreateResource({ name: f.name, phone: f.phone || null, address: f.address || null, source_note: f.source_note, city_id: f.city_id ? Number(f.city_id) : null, resource_type: "hospital" }); setF({ name: "", phone: "", address: "", source_note: "", city_id: "" }); q.reload(); }
    catch (e2) { setErr(e2 instanceof Error ? e2.message : "Failed."); }
  }
  return (
    <div className="space-y-4">
      <Notice>Only add real, verified facilities. A source note is required so every entry can be traced. The application ships with no hospital entries.</Notice>
      <Card title="Add a hospital / emergency resource">
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
          <div><label className="label" htmlFor="rn">Name</label><input id="rn" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div><label className="label" htmlFor="rc">City</label><select id="rc" className="input" value={f.city_id} onChange={(e) => setF({ ...f, city_id: e.target.value })}><option value="">All cities</option>{cities.map((c) => <option key={c.city_id} value={c.city_id}>{c.name}</option>)}</select></div>
          <div><label className="label" htmlFor="rp">Phone</label><input id="rp" className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
          <div><label className="label" htmlFor="ra">Address</label><input id="ra" className="input" value={f.address} onChange={(e) => setF({ ...f, address: e.target.value })} /></div>
          <div className="sm:col-span-2"><label className="label" htmlFor="rs">Source of this information</label><input id="rs" className="input" required minLength={3} placeholder="e.g. hospital's official website, checked on …" value={f.source_note} onChange={(e) => setF({ ...f, source_note: e.target.value })} /></div>
          <div className="sm:col-span-2"><button className="btn-primary">Add resource</button></div>
        </form>{err && <div className="mt-2"><ErrorState message={err} /></div>}
      </Card>
      <Card title="Entries">{q.loading && <Spinner />}{q.data?.items.length === 0 && <p className="text-sm text-slate-500">None yet.</p>}
        <ul className="space-y-2">{q.data?.items.map((r: Row) => (<li key={r.resource_id} className="flex items-start justify-between gap-2 rounded border border-slate-200 p-2 text-sm dark:border-navy-700">
          <div><strong>{r.name}</strong>{r.phone && ` · ${r.phone}`}<br /><span className="text-xs text-slate-500">Source: {r.source_note}</span></div>
          <button className="btn-danger" onClick={async () => { await api.adminDeleteResource(r.resource_id); q.reload(); }}>Delete</button></li>))}</ul></Card>
    </div>
  );
}

function Audit() {
  const q = useAsync(() => api.adminAudit(), []);
  return (<Card title="Administrative audit log">{q.loading && <Spinner />}{q.error && <ErrorState message={q.error} onRetry={q.reload} />}
    {q.data?.items.length === 0 && <p className="text-sm text-slate-500">No administrative actions recorded yet.</p>}
    {q.data && q.data.items.length > 0 && <table className="min-w-full text-sm"><thead><tr>{["When", "Admin", "Action", "Target"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody>
      {q.data.items.map((a: Row) => <tr key={a.audit_id} className="border-t border-slate-100 dark:border-navy-800"><td className="td">{fmtDate(a.created_at)}</td><td className="td">{a.actor ?? "CLI / system"}</td><td className="td">{a.action}</td><td className="td">{a.target}</td></tr>)}</tbody></table>}</Card>);
}

export default function AdminView() {
  const [tab, setTab] = useState<Tab>("Overview");
  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Administration" title="Admin dashboard" subtitle="Users, dataset status, data quality, notices and reports. Every admin endpoint is also enforced by the backend." />
      <div className="flex flex-wrap gap-1" role="tablist">{TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "btn-primary" : "btn-secondary"} onClick={() => setTab(t)}>{t}</button>)}</div>
      {tab === "Overview" && <Overview />}{tab === "Users" && <Users />}{tab === "Dataset & quality" && <Dataset />}
      {tab === "Alerts" && <Alerts />}{tab === "Safety resources" && <Resources />}{tab === "Audit log" && <Audit />}
    </div>
  );
}
