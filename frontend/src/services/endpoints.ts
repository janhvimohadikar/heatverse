import type {
  AlertItem, City, CityDetail, LayerInfo, LiveWeather, MapDates, MapMode, MapRiskResponse, ModelStatus, Paged,
  PredictionHistoryItem, PredictionResult, Profile, SurfaceResponse, TokenResponse, User,
} from "../types";
import { request } from "./api";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

export const api = {
  // auth & profile
  signup: (email: string, password: string, full_name?: string) =>
    request<TokenResponse>("/api/auth/signup", { method: "POST", body: { email, password, full_name } }),
  login: (email: string, password: string) => request<TokenResponse>("/api/auth/login", { method: "POST", body: { email, password } }),
  me: () => request<User>("/api/auth/me"),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  getProfile: () => request<Profile>("/api/profile"),
  saveProfile: (p: Profile) => request<Profile>("/api/profile", { method: "PUT", body: p }),

  // reference + weather
  health: () => request<Json>("/api/health"),
  cities: () => request<{ items: City[] }>("/api/cities"),
  liveWeather: (city_id: number) => request<LiveWeather>("/api/weather/current", { params: { city_id } }),
  historical: (city_id: number, start?: string, end?: string, page = 1, page_size = 31) =>
    request<Paged<Json>>("/api/weather/historical", { params: { city_id, start, end, page, page_size } }),

  // analytics
  trends: (city_id: number, granularity: "annual" | "monthly" | "seasonal", start?: string, end?: string) =>
    request<Json>("/api/analytics/temperature-trends", { params: { city_id, granularity, start, end } }),
  climatology: (city_id: number) => request<Json>("/api/analytics/climatology", { params: { city_id } }),
  dashboardSummary: (city_id: number, month?: number) => request<Json>("/api/analytics/dashboard-summary", { params: { city_id, month } }),
  comparison: (city_ids: number[], metric: string, start?: string, end?: string) =>
    request<Json>("/api/analytics/city-comparison", { params: { city_ids: city_ids.join(","), metric, start, end } }),
  periodComparison: (city_id: number, a_start: string, a_end: string, b_start: string, b_end: string) =>
    request<Json>("/api/analytics/period-comparison", { params: { city_id, a_start, a_end, b_start, b_end } }),
  heatwaveEvents: (city_id: number, start?: string, end?: string) =>
    request<Json>("/api/analytics/heatwave-events", { params: { city_id, start, end } }),
  dataQuality: () => request<Json>("/api/analytics/data-quality"),

  // map
  mapLayers: () => request<{ items: LayerInfo[] }>("/api/map/layers"),
  mapDates: () => request<MapDates>("/api/map/dates"),
  mapRisk: (p: { mode: MapMode; layer: string; date?: string; horizon_days?: number }, signal?: AbortSignal) =>
    request<MapRiskResponse>("/api/map/risk", { params: p, signal }),
  mapSurface: (layer: string, date?: string, max_km = 300) =>
    request<SurfaceResponse>("/api/map/surface", { params: { layer, date, max_km } }),
  cityDetail: (city_id: number, date?: string) => request<CityDetail>(`/api/map/city/${city_id}`, { params: { date } }),

  // predictions
  modelStatus: () => request<ModelStatus>("/api/predictions/model-status"),
  predict: (city_id: number, horizon_days: number) =>
    request<PredictionResult>("/api/predictions", { method: "POST", body: { city_id, horizon_days } }),
  predictionHistory: (page = 1, page_size = 20) => request<Paged<PredictionHistoryItem>>("/api/predictions/history", { params: { page, page_size } }),
  clearPredictionHistory: () => request<void>("/api/predictions/history", { method: "DELETE" }),

  // safety
  guidance: () => request<Json>("/api/safety/guidance"),
  activeAlerts: (city_id?: number) => request<{ items: AlertItem[]; note: string }>("/api/alerts/active", { params: { city_id } }),
  hospitals: (p: { city_id?: number; lat?: number; lon?: number; radius_km?: number }) => request<Json>("/api/hospitals/nearby", { params: p }),

  // admin
  adminOverview: () => request<Json>("/api/admin/overview"),
  adminImportStatus: () => request<Json>("/api/admin/import-status"),
  adminDataQuality: () => request<Json>("/api/admin/data-quality"),
  adminUsers: (page = 1, q?: string) => request<Json>("/api/admin/users", { params: { page, q } }),
  adminUpdateUser: (id: number, body: { is_active?: boolean; role?: "user" | "admin" }) =>
    request<Json>(`/api/admin/users/${id}`, { method: "PATCH", body }),
  adminPredictions: (page = 1) => request<Json>("/api/admin/predictions", { params: { page } }),
  adminAlerts: () => request<{ items: AlertItem[] }>("/api/admin/alerts"),
  adminCreateAlert: (body: Json) => request<Json>("/api/admin/alerts", { method: "POST", body }),
  adminDeleteAlert: (id: number) => request<void>(`/api/admin/alerts/${id}`, { method: "DELETE" }),
  adminResources: () => request<Json>("/api/admin/safety-resources"),
  adminCreateResource: (body: Json) => request<Json>("/api/admin/safety-resources", { method: "POST", body }),
  adminDeleteResource: (id: number) => request<void>(`/api/admin/safety-resources/${id}`, { method: "DELETE" }),
  adminAudit: () => request<Json>("/api/admin/audit-log"),
};
