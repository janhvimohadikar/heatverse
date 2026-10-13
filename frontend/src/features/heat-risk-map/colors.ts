import type { LayerInfo, MapFeature, RiskCategory } from "../../types";

export const RISK_COLORS: Record<RiskCategory, string> = { Low: "#2F855A", Moderate: "#D69E2E", High: "#DD6B20", Extreme: "#C53030" };
export const NO_DATA = "#94A3B8";
export const CATEGORIES: RiskCategory[] = ["Low", "Moderate", "High", "Extreme"];
export const CATEGORY_RANGES: Record<RiskCategory, string> = { Low: "0–24", Moderate: "25–49", High: "50–74", Extreme: "75–100" };

const SEQUENTIAL = ["#3B82A0", "#E9D66B", "#F59E0B", "#DD6B20", "#C53030"];
const DIVERGING = ["#2B6CB0", "#E2E8F0", "#C53030"];

function hex(c: string): [number, number, number] {
  return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
}

export function scale(stops: string[], t: number): string {
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  const f = x - i;
  const a = hex(stops[i]);
  const b = hex(stops[i + 1]);
  const m = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${m[0]},${m[1]},${m[2]})`;
}

export function continuousColor(layer: LayerInfo, value: number | null): string {
  if (value === null || value === undefined) return NO_DATA;
  const [lo, hi] = layer.domain;
  const t = (value - lo) / (hi - lo);
  return scale(layer.key === "temp_anomaly" ? DIVERGING : SEQUENTIAL, t);
}

export function featureColor(layer: LayerInfo, f: MapFeature): string {
  if (f.missing) return NO_DATA;
  if (layer.key === "risk") return f.risk.category ? RISK_COLORS[f.risk.category] : NO_DATA;
  return continuousColor(layer, f.layer_value);
}

export function gradientCss(layer: LayerInfo): string {
  const stops = layer.key === "temp_anomaly" ? DIVERGING : SEQUENTIAL;
  return `linear-gradient(to right, ${stops.join(", ")})`;
}

export function formatLayerValue(layer: LayerInfo, f: MapFeature): string {
  if (f.missing || f.layer_value === null || f.layer_value === undefined) return "No data";
  if (layer.key === "risk") return `${f.risk.category} (${f.risk.score})`;
  return `${f.layer_value.toFixed(layer.key === "severity" ? 0 : 1)} ${layer.unit}`.trim();
}

/** Normalise state names so "Delhi (NCT)" matches "NCT of Delhi" / "Delhi" in boundary files. */
export function normState(s: string | null | undefined): string {
  return (s ?? "").toLowerCase().replace(/\(.*?\)/g, "").replace(/\bnct of\b/g, "").replace(/&/g, "and").replace(/[^a-z ]/g, "").replace(/\s+/g, " ").trim();
}

const STATE_KEYS = ["NAME_1", "ST_NM", "state", "STATE", "State", "st_nm", "name", "NAME", "Name"];
export function geoStateName(props: Record<string, unknown> | null | undefined): string {
  if (!props) return "";
  for (const k of STATE_KEYS) if (typeof props[k] === "string") return normState(props[k] as string);
  return "";
}
