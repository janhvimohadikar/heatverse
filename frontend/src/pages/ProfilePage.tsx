import { useEffect, useState, type FormEvent } from "react";
import { CitySelect } from "../components/CitySelect";
import { Card, ErrorState, Notice, PageHeader, Spinner } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { useCities } from "../hooks/useCities";
import { useTheme } from "../hooks/useTheme";
import { api } from "../services/endpoints";
import type { Profile } from "../types";

export default function ProfilePage() {
  const { cities } = useCities();
  const q = useAsync(() => api.getProfile(), []);
  const { setTheme } = useTheme();
  const [form, setForm] = useState<Profile | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (q.data) setForm(q.data); }, [q.data]);
  if (q.loading && !form) return <Spinner />;
  if (q.error && !form) return <ErrorState message={q.error} onRetry={q.reload} />;
  if (!form) return null;
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setForm({ ...form, [k]: v });

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setMsg(null);
    try { const saved = await api.saveProfile(form!); setForm(saved); setTheme(saved.theme); setMsg({ ok: true, text: "Profile saved." }); }
    catch (err) { setMsg({ ok: false, text: err instanceof Error ? err.message : "Could not save." }); } finally { setBusy(false); }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <PageHeader eyebrow="Personal settings" title="Your profile" subtitle="These details personalise heat-risk guidance. They never change the weather database." />
      <Card>
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2"><span className="label">Email</span><p className="text-sm">{form.email}</p></div>
          <div><label className="label" htmlFor="fn">Name</label><input id="fn" className="input" value={form.full_name ?? ""} onChange={(e) => set("full_name", e.target.value || null)} /></div>
          <div><label className="label" htmlFor="age">Age</label><input id="age" type="number" min={0} max={120} className="input" value={form.age ?? ""} onChange={(e) => set("age", e.target.value === "" ? null : Number(e.target.value))} /></div>
          <CitySelect cities={cities} value={form.home_city_id} onChange={(id) => set("home_city_id", id)} label="Home city" id="home" />
          <div><label className="label" htmlFor="occ">Occupation</label><input id="occ" className="input" value={form.occupation ?? ""} onChange={(e) => set("occupation", e.target.value || null)} /></div>
          <div><label className="label" htmlFor="ow">Outdoor worker</label><select id="ow" className="input" value={form.is_outdoor_worker ? "yes" : "no"} onChange={(e) => set("is_outdoor_worker", e.target.value === "yes")}><option value="no">No</option><option value="yes">Yes</option></select></div>
          <div><label className="label" htmlFor="act">Physical activity</label><select id="act" className="input" value={form.activity_level} onChange={(e) => set("activity_level", e.target.value as Profile["activity_level"])}><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option></select></div>
          <div><label className="label" htmlFor="ec">Emergency contact</label><input id="ec" className="input" value={form.emergency_contact ?? ""} onChange={(e) => set("emergency_contact", e.target.value || null)} /></div>
          <div><label className="label" htmlFor="th">Theme</label><select id="th" className="input" value={form.theme} onChange={(e) => set("theme", e.target.value as Profile["theme"])}><option value="system">Match my device</option><option value="light">Light</option><option value="dark">Dark</option></select></div>
          <div className="sm:col-span-2 flex items-center gap-3"><button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
            {msg && <span className={`text-sm ${msg.ok ? "text-heat-green" : "text-heat-red"}`}>{msg.text}</span>}</div>
        </form>
      </Card>
      <Notice>Your emergency contact is stored in the database for your own reference; HEATVERSE does not contact anyone automatically.</Notice>
    </div>
  );
}
