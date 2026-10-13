export type RiskCategory = "Low" | "Moderate" | "High" | "Extreme";
export type MapMode = "historical" | "demo_prediction";

export interface User { user_id: number; email: string; role: "user" | "admin"; is_active: boolean; created_at: string; }
export interface TokenResponse { access_token: string; token_type: string; user: User; }

export interface City {
  city_id: number; name: string; state: string | null; latitude: number | null; longitude: number | null;
  is_coastal: number; first_date: string | null; last_date: string | null; observations: number;
}

export interface Profile {
  full_name: string | null; age: number | null; home_city_id: number | null; occupation: string | null;
  is_outdoor_worker: boolean; activity_level: "low" | "moderate" | "high"; emergency_contact: string | null;
  theme: "light" | "dark" | "system"; email?: string | null;
}

export interface LayerInfo {
  key: string; label: string; unit: string; kind: string; modes: MapMode[]; description: string;
  domain: [number, number]; available: boolean; reason: string | null;
}

export interface MapFeature {
  city_id: number; name: string; state: string | null; latitude: number; longitude: number;
  missing: boolean; missing_reason?: string; observation_date?: string | null;
  values: {
    temp_max_c?: number | null; temp_min_c?: number | null; apparent_max_c?: number | null;
    wind_speed_max_kmh?: number | null; precipitation_sum_mm?: number | null; temp_anomaly_c?: number | null;
  };
  hot_day_streak: number | null;
  risk: { score: number | null; category: RiskCategory | null };
  layer_value: number | null; layer_note?: string;
}

export interface MapRiskResponse {
  mode: MapMode; data_type: string; data_type_note: string; date: string; layer: LayerInfo; features: MapFeature[];
  counts: Record<string, number>; value_range: { min: number; max: number } | null;
  scoring: { version: string; categories: { min: number; max: number; label: RiskCategory }[]; colors: Record<RiskCategory, string>; disclaimer: string };
  horizon_days?: number; model?: { name: string; version: string; is_demo: boolean };
}

export interface MapDates { first_date: string; last_date: string; cities: number; dates_with_incomplete_city_coverage: string[]; }

export interface SurfaceResponse {
  available: boolean; reason?: string; date: string; layer: LayerInfo; cells: { lat: number; lon: number; value: number }[];
  cell_size_deg?: number; warning?: string; method?: { name: string; power: number; max_distance_km: number; input_points: number };
}

export interface ContributingFactor { key: string; label: string; value: number; unit: string; sub_score: number; weight: number; points: number; }

export interface CityDetail {
  data_type: string; source: string; date: string; city: City; feature: MapFeature;
  trend_30d: { obs_date: string; temp_max_c: number | null; temp_min_c: number | null; apparent_max_c: number | null }[];
  weekly_tmax_change_c: number | null; contributing_factors: ContributingFactor[]; explanation: string[];
  recommendations: string[]; disclaimer: string;
}

export interface LiveWeather {
  status: "ok" | "unavailable" | "disabled"; reason?: string; source?: string; observation_time?: string;
  temperature_c?: number | null; apparent_temperature_c?: number | null; humidity_pct?: number | null;
  wind_speed_kmh?: number | null; pressure_hpa?: number | null; precipitation_mm?: number | null; condition?: string | null;
}

export interface PredictionResult {
  prediction_id?: number; created_at?: string;
  city: { city_id: number; name: string; state: string | null };
  target_date: string; horizon_days: number; as_of_date: string | null;
  model: { name: string; version: string; is_demo: boolean; label: string };
  risk: { score: number | null; category: RiskCategory | null };
  personal: { base_score: number | null; personal_score: number | null; personal_category: RiskCategory | null; adjustments: { label: string; points: number }[] };
  expected: { temp_max_c?: number | null; temp_min_c?: number | null; apparent_max_c?: number | null };
  heatwave_probability: number | null; confidence: number | null;
  context: Record<string, unknown>; notes: string[];
  explanation: { kind: string; lines: string[]; components: ContributingFactor[] };
  recommendations: string[]; disclaimer: string;
}

export interface PredictionHistoryItem {
  prediction_id: number; created_at: string; city: string; city_id: number; target_date: string; horizon_days: number;
  risk_score: number | null; risk_category: RiskCategory | null; personal_score: number | null; personal_category: RiskCategory | null;
  model_name: string; model_version: string; is_demo: boolean; expected_temp_max_c: number | null; recommendation: string | null;
}

export interface Paged<T> { page: number; page_size: number; total: number; items: T[]; }
export interface ModelStatus { mode: "demo" | "trained"; model_name: string; model_version: string; message: string; confidence_available: boolean; }
export interface AlertItem { alert_id: number; city_id: number | null; level: "info" | "advisory" | "warning"; title: string; message: string; starts_on: string | null; ends_on: string | null; is_active?: boolean; }
