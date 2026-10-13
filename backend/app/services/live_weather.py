"""Live weather adapter (Open-Meteo). Failures never crash the app; they return status='unavailable'."""
from __future__ import annotations

from typing import Any

from app.core import cache, heat_config as cfg


def fetch_current(settings, city: dict[str, Any]) -> dict[str, Any]:
    base = {"data_type": "live", "city": {"city_id": city["city_id"], "name": city["name"]}}
    if not settings.live_weather_enabled:
        return {**base, "status": "disabled", "reason": "Live weather is disabled (LIVE_WEATHER_ENABLED=false)."}
    if city.get("latitude") is None or city.get("longitude") is None:
        return {**base, "status": "unavailable", "reason": "This city has no coordinates."}

    def call() -> dict[str, Any]:
        import httpx

        params = {
            "latitude": city["latitude"], "longitude": city["longitude"], "timezone": "auto",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,"
                       "surface_pressure,wind_speed_10m",
        }
        try:
            r = httpx.get(settings.open_meteo_url, params=params, timeout=settings.external_timeout_seconds)
            r.raise_for_status()
            cur = r.json()["current"]
            return {
                **base, "status": "ok", "source": "Open-Meteo (open-meteo.com) - model-based current conditions",
                "observation_time": cur.get("time"), "temperature_c": cur.get("temperature_2m"),
                "apparent_temperature_c": cur.get("apparent_temperature"), "humidity_pct": cur.get("relative_humidity_2m"),
                "wind_speed_kmh": cur.get("wind_speed_10m"), "pressure_hpa": cur.get("surface_pressure"),
                "precipitation_mm": cur.get("precipitation"), "weather_code": cur.get("weather_code"),
                "condition": cfg.WMO_WEATHER_CODES.get(cur.get("weather_code"), None),
            }
        except Exception as exc:  # timeouts, DNS errors, bad JSON ...
            return {**base, "status": "unavailable", "reason": f"Live weather service could not be reached ({type(exc).__name__})."}

    result = cache.cached(f"live:{city['city_id']}", 600, call)
    if result.get("status") != "ok":
        cache._store.pop(f"live:{city['city_id']}", None)  # do not cache failures
    return result
