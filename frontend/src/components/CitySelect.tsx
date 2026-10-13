import type { City } from "../types";

export function CitySelect({ cities, value, onChange, label = "City", id = "city-select" }: {
  cities: City[]; value: number | null; onChange: (id: number) => void; label?: string; id?: string;
}) {
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <select id={id} className="input" value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
        {value === null && <option value="">Select a city…</option>}
        {cities.map((c) => <option key={c.city_id} value={c.city_id}>{c.name}</option>)}
      </select>
    </div>
  );
}
