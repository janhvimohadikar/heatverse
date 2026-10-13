import { useEffect, useState } from "react";
import { CitySelect } from "../../components/CitySelect";
import { Card, ErrorState, Notice, PageHeader, Spinner } from "../../components/ui";
import { useAsync } from "../../hooks/useAsync";
import { useCities } from "../../hooks/useCities";
import { api } from "../../services/endpoints";

interface Hospital { name: string; phone?: string | null; address?: string | null; distance_km: number; latitude: number; longitude: number; }

const list = (items: string[]) => <ul className="list-disc space-y-1 pl-5 text-sm">{items.map((i) => <li key={i}>{i}</li>)}</ul>;

export default function SafetyView() {
  const g = useAsync(() => api.guidance(), []);
  const { cities } = useCities();
  const [cityId, setCityId] = useState<number | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [geoMsg, setGeoMsg] = useState<string | null>(null);
  const [radius, setRadius] = useState(10);

  useEffect(() => { if (cities.length && cityId === null) setCityId(cities.find((c) => c.name === "Delhi")?.city_id ?? cities[0].city_id); }, [cities, cityId]);

  const hospitals = useAsync(() => api.hospitals(coords ? { lat: coords.lat, lon: coords.lon, city_id: cityId ?? undefined, radius_km: radius } : { city_id: cityId!, radius_km: radius }),
    [cityId, coords?.lat, coords?.lon, radius], cityId !== null);

  function useMyLocation() {
    if (!navigator.geolocation) { setGeoMsg("This browser does not support location. Use the city search instead."); return; }
    setGeoMsg("Waiting for permission…");
    navigator.geolocation.getCurrentPosition(
      (p) => { setCoords({ lat: p.coords.latitude, lon: p.coords.longitude }); setGeoMsg("Using your device location (not stored)."); },
      () => setGeoMsg("Location permission was not granted. Showing results for the selected city instead."),
      { timeout: 10000 });
  }

  if (g.loading) return <Spinner />;
  if (g.error) return <ErrorState message={g.error} onRetry={g.reload} />;
  const d = g.data;
  const osm = hospitals.data?.osm;

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Emergency support" title="Heat safety & nearby hospitals" subtitle="Educational guidance for staying safe in hot weather." />
      <Notice tone="warn"><strong>Emergency?</strong> {d.disclaimer}</Notice>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Recognise heat illness">
          <h3 className="text-sm font-semibold">Heat exhaustion</h3>{list(d.heat_illness.heat_exhaustion.signs)}
          <p className="mt-2 text-sm font-semibold">What to do</p>{list(d.heat_illness.heat_exhaustion.actions)}
          <h3 className="mt-4 text-sm font-semibold text-heat-red">Heatstroke (emergency)</h3>{list(d.heat_illness.heatstroke.signs)}
          <p className="mt-2 text-sm font-semibold">What to do</p>{list(d.heat_illness.heatstroke.actions)}
        </Card>
        <div className="space-y-4">
          <Card title="Hydration and cooling">{list(d.hydration_and_cooling)}</Card>
          <Card title="Vulnerable groups">{list(d.vulnerable_groups)}</Card>
          <Card title="Outdoor work precautions">{list(d.outdoor_work)}</Card>
        </div>
      </div>

      <Card title="Guidance by risk level">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(d.by_category as Record<string, string[]>).map(([cat, tips]) => (<div key={cat}><h3 className="mb-1 text-sm font-semibold">{cat}</h3>{list(tips)}</div>))}
        </div>
      </Card>

      <Card title="Nearby hospitals" subtitle="Live lookup in OpenStreetMap data. Location is requested only when you press the button.">
        <div className="grid gap-3 sm:grid-cols-3">
          <CitySelect cities={cities} value={cityId} onChange={(id) => { setCityId(id); setCoords(null); }} label="Search by city" />
          <div><label className="label" htmlFor="r">Radius: {radius} km</label><input id="r" type="range" min={1} max={50} value={radius} onChange={(e) => setRadius(Number(e.target.value))} className="w-full" /></div>
          <div className="flex items-end"><button className="btn-secondary w-full" onClick={useMyLocation}>⌖ Use my location</button></div>
        </div>
        {geoMsg && <p className="mt-2 text-xs text-slate-500">{geoMsg}</p>}
        {hospitals.loading && <Spinner label="Searching…" />}
        {hospitals.error && <div className="mt-3"><ErrorState message={hospitals.error} onRetry={hospitals.reload} /></div>}
        {hospitals.data && (<div className="mt-3 space-y-3">
          <p className="text-xs text-slate-500">Distances are measured from: {hospitals.data.origin.basis}.</p>
          {hospitals.data.curated.length > 0 && (<div><h3 className="text-sm font-semibold">Entered by the administrator</h3><ul className="mt-1 space-y-2">
            {hospitals.data.curated.map((r: { resource_id: number; name: string; phone?: string; address?: string; source_note: string }) => (
              <li key={r.resource_id} className="rounded border border-slate-200 p-2 text-sm dark:border-navy-700"><strong>{r.name}</strong>{r.phone && <> · {r.phone}</>}{r.address && <><br />{r.address}</>}<br /><span className="text-xs text-slate-500">Source: {r.source_note}</span></li>))}</ul></div>)}
          {osm?.status === "ok" && (osm.items.length === 0 ? <p className="text-sm text-slate-500">No hospitals found in OpenStreetMap within {radius} km. Try a larger radius.</p> : (<div>
            <h3 className="text-sm font-semibold">OpenStreetMap results</h3>
            <ul className="mt-1 space-y-2">{(osm.items as Hospital[]).map((h, i) => (
              <li key={i} className="rounded border border-slate-200 p-2 text-sm dark:border-navy-700"><strong>{h.name}</strong> · {h.distance_km} km{h.phone && <> · {h.phone}</>}{h.address && <><br />{h.address}</>}
                <br /><a className="text-xs text-heat-orange hover:underline" target="_blank" rel="noreferrer" href={`https://www.openstreetmap.org/?mlat=${h.latitude}&mlon=${h.longitude}#map=17/${h.latitude}/${h.longitude}`}>View on OpenStreetMap ↗</a></li>))}</ul>
            <p className="mt-2 text-xs text-slate-500">{osm.attribution}</p></div>))}
          {osm && osm.status !== "ok" && <Notice>{osm.reason ?? "Hospital lookup is unavailable."} No hospital information is shown rather than guessing. In an emergency call your local emergency number.</Notice>}
        </div>)}
      </Card>
    </div>
  );
}
