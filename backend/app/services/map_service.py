"""Data for the heat-risk map: per-city values, risk scores, layers, interpolation surface and city details."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core import cache, heat_config as cfg
from app.core.errors import NotFoundError, ValidationFailed
from app.core.heat_scoring import categorize, compute_score, explain, hot_day_threshold
from app.services import analytics, geo, historical, safety_content

HIST, DEMO = "historical", "demo_prediction"

LAYERS = [
    {"key": "risk", "label": "Heatwave Risk", "unit": "category", "kind": "derived", "modes": [HIST, DEMO],
     "description": "Risk category (Low/Moderate/High/Extreme) from the HEATVERSE heat-risk score.", "domain": [0, 100]},
    {"key": "severity", "label": "Heatwave Severity Index", "unit": "0-100", "kind": "derived", "modes": [HIST, DEMO],
     "description": "The numeric heat-risk score (0-100). A project metric, not an official warning.", "domain": [0, 100]},
    {"key": "temp_max", "label": "Maximum Temperature", "unit": "°C", "kind": "observed", "modes": [HIST, DEMO],
     "description": "Daily maximum 2 m air temperature.", "domain": [15, 47]},
    {"key": "temp_min", "label": "Minimum Temperature", "unit": "°C", "kind": "observed", "modes": [HIST, DEMO],
     "description": "Daily minimum 2 m air temperature.", "domain": [0, 35]},
    {"key": "apparent_max", "label": "Apparent Temperature", "unit": "°C", "kind": "observed", "modes": [HIST, DEMO],
     "description": "Daily maximum apparent (feels-like) temperature.", "domain": [10, 50]},
    {"key": "temp_anomaly", "label": "Historical Temperature (departure)", "unit": "°C", "kind": "derived", "modes": [HIST],
     "description": "Maximum temperature minus the 2000-2024 mean maximum for the same calendar month.", "domain": [-8, 8]},
    {"key": "wind", "label": "Wind Speed", "unit": "km/h", "kind": "observed", "modes": [HIST],
     "description": "Daily maximum wind speed at 10 m.", "domain": [0, 40]},
    {"key": "precipitation", "label": "Precipitation", "unit": "mm", "kind": "observed", "modes": [HIST],
     "description": "Daily precipitation total.", "domain": [0, 100]},
    {"key": "confidence", "label": "Prediction Confidence", "unit": "", "kind": "model", "modes": [],
     "description": "Model confidence.", "domain": [0, 1]},
]
LAYER_BY_KEY = {l["key"]: l for l in LAYERS}

DATA_TYPE_LABEL = {HIST: "observed", DEMO: "demo"}


def list_layers(model_status: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for l in LAYERS:
        item = dict(l)
        item["available"] = True
        item["reason"] = None
        if l["key"] == "confidence":
            item["available"] = False
            item["reason"] = ("No trained model with a meaningful confidence measure is connected. "
                              "Demo predictions do not produce a confidence value, so none is shown.")
        out.append(item)
    return out


def available_dates(db) -> dict[str, Any]:
    cov = historical.date_coverage(db)
    gaps = db.rows(
        "SELECT obs_date, COUNT(*) AS n FROM weather_observation GROUP BY obs_date "
        "HAVING n < (SELECT COUNT(*) FROM city) ORDER BY obs_date LIMIT 500")
    return {"first_date": cov["first_date"], "last_date": cov["last_date"], "cities": cov["cities"],
            "dates_with_incomplete_city_coverage": [g["obs_date"] for g in gaps]}


def _resolve_date(db, value: str | None) -> str:
    cov = historical.date_coverage(db)
    if value is None:
        return cov["last_date"]
    value = historical.parse_date(value, "date")
    if not cov["first_date"] <= value <= cov["last_date"]:
        raise NotFoundError(f"No observations for {value}. Available range: {cov['first_date']} to {cov['last_date']}.")
    return value


def _historical_rows(db, day: str) -> dict[int, dict[str, Any]]:
    """Rows for `day` and the 6 days before it, grouped by city (needed for the hot-day streak)."""
    start = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
    rows = db.rows(
        """SELECT city_id, obs_date, temp_max_c, temp_min_c, apparent_max_c, wind_speed_max_kmh, precipitation_sum_mm
           FROM weather_observation WHERE obs_date >= :start AND obs_date <= :day ORDER BY city_id, obs_date""",
        {"start": start, "day": day})
    grouped: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r["city_id"], []).append(r)
    return grouped


def _streak(days: list[dict[str, Any]], day: str, threshold: float) -> int:
    by_date = {r["obs_date"]: r["temp_max_c"] for r in days}
    n, cur = 0, date.fromisoformat(day)
    while True:
        t = by_date.get(cur.isoformat())
        if t is None or t < threshold:
            return n
        n += 1
        cur -= timedelta(days=1)


def _layer_value(layer: str, values: dict[str, Any], score: int | None) -> float | None:
    if layer in ("risk", "severity"):
        return score
    key = {"temp_max": "temp_max_c", "temp_min": "temp_min_c", "apparent_max": "apparent_max_c",
           "temp_anomaly": "temp_anomaly_c", "wind": "wind_speed_max_kmh", "precipitation": "precipitation_sum_mm"}[layer]
    return values.get(key)


def risk_map(db, mode: str = HIST, layer: str = "risk", day: str | None = None, horizon_days: int = 1,
             predictor=None, today: date | None = None) -> dict[str, Any]:
    if layer not in LAYER_BY_KEY:
        raise ValidationFailed(f"Unknown layer '{layer}'. Choose one of: {', '.join(LAYER_BY_KEY)}.")
    if mode not in (HIST, DEMO):
        raise ValidationFailed("mode must be 'historical' or 'demo_prediction'.")
    meta = LAYER_BY_KEY[layer]
    if layer == "confidence":
        raise ValidationFailed("The Prediction Confidence layer is unavailable: no model with a meaningful confidence measure is connected.")
    if mode not in meta["modes"]:
        raise ValidationFailed(f"The '{meta['label']}' layer is not available in {mode} mode because the underlying data does not exist for it.")

    cities = db.rows("SELECT * FROM city WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY name")
    features: list[dict[str, Any]] = []
    out_date: str
    extra: dict[str, Any] = {}

    if mode == HIST:
        out_date = _resolve_date(db, day)
        grouped = _historical_rows(db, out_date)
        for c in cities:
            rows = grouped.get(c["city_id"], [])
            today_row = next((r for r in rows if r["obs_date"] == out_date), None)
            f = _base_feature(c)
            if today_row is None:
                f.update({"missing": True, "missing_reason": "No observation for this city on this date."})
            else:
                normals = analytics.monthly_normals(db, c["city_id"])
                normal = normals.get(int(out_date[5:7]))
                streak = _streak(rows, out_date, hot_day_threshold(c["name"]))
                values = {
                    "temp_max_c": today_row["temp_max_c"], "temp_min_c": today_row["temp_min_c"],
                    "apparent_max_c": today_row["apparent_max_c"], "wind_speed_max_kmh": today_row["wind_speed_max_kmh"],
                    "precipitation_sum_mm": today_row["precipitation_sum_mm"],
                    "temp_anomaly_c": round(today_row["temp_max_c"] - normal, 1) if normal is not None and today_row["temp_max_c"] is not None else None,
                }
                res = compute_score({"temp_max_c": values["temp_max_c"], "apparent_max_c": values["apparent_max_c"],
                                     "temp_min_c": values["temp_min_c"], "hot_day_streak": streak})
                f.update({"missing": False, "observation_date": out_date, "values": values, "hot_day_streak": streak,
                          "risk": {"score": res["score"], "category": res["category"]}})
            features.append(f)
    else:
        if predictor is None:
            raise ValidationFailed("No predictor is available.")
        horizon_days = max(0, min(int(horizon_days), 14))
        base = today or date.today()
        out_date = (base + timedelta(days=horizon_days)).isoformat()
        extra = {"horizon_days": horizon_days, "prediction_generated_for": out_date,
                 "model": {"name": predictor.name, "version": predictor.version, "is_demo": predictor.is_demo}}
        for c in cities:
            f = _base_feature(c)
            pr = predictor.predict(db, c, date.fromisoformat(out_date), horizon_days)
            f.update({"missing": False, "observation_date": None, "values": {
                "temp_max_c": pr.expected.get("temp_max_c"), "temp_min_c": pr.expected.get("temp_min_c"),
                "apparent_max_c": pr.expected.get("apparent_max_c")},
                "hot_day_streak": None, "risk": {"score": pr.score, "category": categorize(pr.score)}})
            features.append(f)

    counts = {"Low": 0, "Moderate": 0, "High": 0, "Extreme": 0, "No data": 0}
    for f in features:
        if f["missing"] or f["risk"]["category"] is None:
            counts["No data"] += 1
            f["layer_value"] = None
        else:
            counts[f["risk"]["category"]] += 1
            f["layer_value"] = _layer_value(layer, f["values"], f["risk"]["score"])
            if f["layer_value"] is None:
                f["layer_note"] = "This variable is not available for this location/date."
    vals = [f["layer_value"] for f in features if f["layer_value"] is not None]
    return {
        "mode": mode, "data_type": DATA_TYPE_LABEL[mode],
        "data_type_note": ("Observed historical values from the supplied dataset; risk scores are derived from them."
                           if mode == HIST else
                           "DEMO: climatology-based baseline, not a trained forecast model."),
        "date": out_date, "layer": meta, "features": features, "counts": counts,
        "value_range": {"min": min(vals), "max": max(vals)} if vals else None,
        "scoring": {"version": cfg.SCORING_VERSION, "categories": [{"min": a, "max": b, "label": l} for a, b, l in cfg.CATEGORIES],
                    "colors": cfg.CATEGORY_COLORS,
                    "disclaimer": "Informational project metric - not an official government heat warning."},
        **extra,
    }


def _base_feature(c: dict[str, Any]) -> dict[str, Any]:
    return {"city_id": c["city_id"], "name": c["name"], "state": c["state"], "latitude": c["latitude"],
            "longitude": c["longitude"], "missing": False, "values": {}, "risk": {"score": None, "category": None}}


def surface(db, layer: str, day: str | None, max_km: float = 300.0, step_deg: float = 0.75) -> dict[str, Any]:
    """Optional interpolated surface of one layer (historical mode only)."""
    if not 50 <= max_km <= 600:
        raise ValidationFailed("max_km must be between 50 and 600.")
    if not 0.25 <= step_deg <= 2.0:
        raise ValidationFailed("step_deg must be between 0.25 and 2.0.")
    data = risk_map(db, HIST, layer, day)
    pts = [(f["latitude"], f["longitude"], f["layer_value"]) for f in data["features"] if f["layer_value"] is not None]
    if len(pts) < 2:
        return {"available": False, "reason": "Fewer than two locations have data for this layer/date, so no surface can be interpolated.",
                "cells": [], "date": data["date"], "layer": data["layer"]}
    cells = cache.cached(f"idw:{layer}:{data['date']}:{max_km}:{step_deg}", 600,
                         lambda: geo.idw_grid(pts, step_deg=step_deg, max_km=max_km))
    return {"available": True, "date": data["date"], "layer": data["layer"], "cells": cells, "cell_size_deg": step_deg,
            "data_type": "interpolated",
            "method": {"name": "Inverse distance weighting (IDW)", "power": 2, "max_distance_km": max_km,
                       "input_points": len(pts)},
            "warning": ("INTERPOLATED surface estimated from only %d city points. It is NOT a set of measurements; "
                        "cells farther than %d km from any city are left blank." % (len(pts), int(max_km)))}


def city_detail(db, city_id: int, day: str | None) -> dict[str, Any]:
    from app.services import cities as city_service

    city = city_service.get_city(db, city_id)
    out_date = _resolve_date(db, day)
    data = risk_map(db, HIST, "risk", out_date)
    feature = next((f for f in data["features"] if f["city_id"] == city_id), None)
    if feature is None:
        raise NotFoundError("This city has no map coordinates, so it cannot be shown on the map.")
    start = (date.fromisoformat(out_date) - timedelta(days=29)).isoformat()
    trend = db.rows(
        "SELECT obs_date, temp_max_c, temp_min_c, apparent_max_c FROM weather_observation "
        "WHERE city_id = :c AND obs_date >= :s AND obs_date <= :e ORDER BY obs_date", {"c": city_id, "s": start, "e": out_date})
    week = [r["temp_max_c"] for r in trend[-7:] if r["temp_max_c"] is not None]
    prev = [r["temp_max_c"] for r in trend[-14:-7] if r["temp_max_c"] is not None]
    delta = round(sum(week) / len(week) - sum(prev) / len(prev), 1) if week and prev else None
    contributing, explanation = [], []
    if not feature["missing"]:
        v = feature["values"]
        res = compute_score({"temp_max_c": v["temp_max_c"], "apparent_max_c": v["apparent_max_c"],
                             "temp_min_c": v["temp_min_c"], "hot_day_streak": feature["hot_day_streak"]})
        contributing, explanation = res["components"], explain(res)
    return {"data_type": "observed", "source": "Supplied historical dataset (Excel import)", "date": out_date,
            "city": city, "feature": feature, "trend_30d": trend, "weekly_tmax_change_c": delta,
            "contributing_factors": contributing, "explanation": explanation,
            "recommendations": safety_content.recommendations_for(feature["risk"]["category"]),
            "disclaimer": "Informational project metric - not an official government heat warning."}
