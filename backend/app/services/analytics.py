"""Historical climate analytics. All aggregation happens in SQL (the browser never receives raw history)."""
from __future__ import annotations

from typing import Any

from app.core import cache, heat_config as cfg
from app.core.errors import NotFoundError, ValidationFailed
from app.core.heat_scoring import hot_day_threshold
from app.services import cities as city_service
from app.services.heatwave_events import detect_events
from app.services.historical import parse_date

# Whitelist: public metric name -> (SQL column, aggregate, label, unit).  Only these ever reach SQL.
METRICS = {
    "temp_max_c": ("temp_max_c", "AVG", "Average maximum temperature", "°C"),
    "temp_min_c": ("temp_min_c", "AVG", "Average minimum temperature", "°C"),
    "temp_mean_c": ("temp_mean_c", "AVG", "Average mean temperature", "°C"),
    "apparent_max_c": ("apparent_max_c", "AVG", "Average apparent maximum temperature", "°C"),
    "peak_temp_max_c": ("temp_max_c", "MAX", "Highest maximum temperature", "°C"),
    "lowest_temp_min_c": ("temp_min_c", "MIN", "Lowest minimum temperature", "°C"),
    "precipitation_sum_mm": ("precipitation_sum_mm", "SUM", "Total precipitation", "mm"),
    "wind_speed_max_kmh": ("wind_speed_max_kmh", "AVG", "Average maximum wind speed", "km/h"),
}

_SUMMARY_COLS = """
    COUNT(*) AS days,
    ROUND(AVG(temp_max_c), 2) AS avg_temp_max_c, ROUND(AVG(temp_min_c), 2) AS avg_temp_min_c,
    ROUND(AVG(apparent_max_c), 2) AS avg_apparent_max_c,
    MAX(temp_max_c) AS peak_temp_max_c, MIN(temp_min_c) AS lowest_temp_min_c,
    ROUND(SUM(precipitation_sum_mm), 1) AS total_precipitation_mm,
    ROUND(AVG(wind_speed_max_kmh), 2) AS avg_wind_speed_max_kmh,
    SUM(CASE WHEN temp_max_c >= :hot THEN 1 ELSE 0 END) AS hot_days
"""


def _city_range(db, city_id, start, end):
    city = city_service.get_city(db, city_id)
    start, end = parse_date(start, "start"), parse_date(end, "end")
    if start and end and start > end:
        raise ValidationFailed("'start' must not be later than 'end'.")
    return city, start, end


def _where(start, end, params):
    w = "city_id = :city_id"
    if start:
        w += " AND obs_date >= :start"
        params["start"] = start
    if end:
        w += " AND obs_date <= :end"
        params["end"] = end
    return w


def temperature_trends(db, city_id: int, granularity: str, start=None, end=None) -> dict[str, Any]:
    if granularity not in {"annual", "monthly", "seasonal"}:
        raise ValidationFailed("granularity must be one of: annual, monthly, seasonal.")
    city, start, end = _city_range(db, city_id, start, end)
    hot = hot_day_threshold(city["name"])
    params: dict[str, Any] = {"city_id": city_id, "hot": hot}
    where = _where(start, end, params)

    if granularity == "annual":
        sql = f"SELECT CAST(strftime('%Y', obs_date) AS INTEGER) AS period, {_SUMMARY_COLS} " \
              f"FROM weather_observation WHERE {where} GROUP BY period ORDER BY period"
    elif granularity == "monthly":
        sql = f"SELECT strftime('%Y-%m', obs_date) AS period, {_SUMMARY_COLS} " \
              f"FROM weather_observation WHERE {where} GROUP BY period ORDER BY period"
    else:
        # Dec belongs to the following year's winter so each winter is one continuous season.
        season_case = ("CASE CAST(strftime('%m', obs_date) AS INTEGER) WHEN 12 THEN 'Winter' WHEN 1 THEN 'Winter' "
                       "WHEN 2 THEN 'Winter' WHEN 3 THEN 'Summer' WHEN 4 THEN 'Summer' WHEN 5 THEN 'Summer' "
                       "WHEN 6 THEN 'Monsoon' WHEN 7 THEN 'Monsoon' WHEN 8 THEN 'Monsoon' WHEN 9 THEN 'Monsoon' "
                       "ELSE 'Post-monsoon' END")
        sql = (f"SELECT CAST(strftime('%Y', obs_date) AS INTEGER) + (strftime('%m', obs_date) = '12') AS period, "
               f"{season_case} AS season, {_SUMMARY_COLS} FROM weather_observation WHERE {where} "
               f"GROUP BY period, season ORDER BY period, season")
    rows = db.rows(sql, params)
    return {"data_type": "observed", "source": "Supplied historical dataset (Excel import)",
            "city": {"city_id": city["city_id"], "name": city["name"]}, "granularity": granularity,
            "hot_day_threshold_c": hot, "start": start, "end": end, "items": rows}


def climatology(db, city_id: int) -> dict[str, Any]:
    """Mean values for each calendar month over the whole record ('typical year')."""
    city = city_service.get_city(db, city_id)
    rows = cache.cached(f"clim:{city_id}", 3600, lambda: db.rows(
        """SELECT CAST(strftime('%m', obs_date) AS INTEGER) AS month,
                  ROUND(AVG(temp_max_c), 2) AS avg_temp_max_c, ROUND(AVG(temp_min_c), 2) AS avg_temp_min_c,
                  ROUND(AVG(apparent_max_c), 2) AS avg_apparent_max_c,
                  ROUND(SUM(precipitation_sum_mm) / COUNT(DISTINCT strftime('%Y', obs_date)), 1) AS avg_monthly_precipitation_mm,
                  ROUND(AVG(wind_speed_max_kmh), 2) AS avg_wind_speed_max_kmh
           FROM weather_observation WHERE city_id = :city_id GROUP BY month ORDER BY month""",
        {"city_id": city_id}))
    return {"data_type": "observed", "source": "Supplied historical dataset (Excel import)",
            "city": {"city_id": city["city_id"], "name": city["name"]}, "items": rows}


def monthly_normals(db, city_id: int) -> dict[int, float]:
    rows = cache.cached(f"normals:{city_id}", 3600, lambda: db.rows(
        "SELECT CAST(strftime('%m', obs_date) AS INTEGER) AS m, AVG(temp_max_c) AS t "
        "FROM weather_observation WHERE city_id = :c GROUP BY m", {"c": city_id}))
    return {r["m"]: r["t"] for r in rows}


def city_comparison(db, city_ids: list[int], metric: str, start=None, end=None) -> dict[str, Any]:
    if metric not in METRICS:
        raise ValidationFailed(f"metric must be one of: {', '.join(METRICS)}.")
    if not 1 <= len(city_ids) <= 10:
        raise ValidationFailed("Select between 1 and 10 cities.")
    col, agg, label, unit = METRICS[metric]
    start, end = parse_date(start, "start"), parse_date(end, "end")
    if start and end and start > end:
        raise ValidationFailed("'start' must not be later than 'end'.")
    series: dict[int, dict[int, float | None]] = {}
    summaries = []
    for cid in city_ids:
        city = city_service.get_city(db, cid)
        params: dict[str, Any] = {"city_id": cid, "hot": hot_day_threshold(city["name"])}
        where = _where(start, end, params)
        yearly = db.rows(
            f"SELECT CAST(strftime('%Y', obs_date) AS INTEGER) AS year, ROUND({agg}({col}), 2) AS value "
            f"FROM weather_observation WHERE {where} GROUP BY year ORDER BY year", params)
        series[cid] = {r["year"]: r["value"] for r in yearly}
        s = db.rows(f"SELECT {_SUMMARY_COLS} FROM weather_observation WHERE {where}", params)[0]
        s.update({"city_id": cid, "name": city["name"], "state": city["state"]})
        summaries.append(s)
    years = sorted({y for s in series.values() for y in s})
    pivot = [{"year": y, **{str(cid): series[cid].get(y) for cid in city_ids}} for y in years]
    return {"data_type": "observed", "source": "Supplied historical dataset (Excel import)",
            "metric": {"key": metric, "label": label, "unit": unit}, "start": start, "end": end,
            "cities": [{"city_id": s["city_id"], "name": s["name"]} for s in summaries],
            "yearly": pivot, "summaries": summaries}


def period_comparison(db, city_id: int, a_start: str, a_end: str, b_start: str, b_end: str) -> dict[str, Any]:
    city = city_service.get_city(db, city_id)
    hot = hot_day_threshold(city["name"])
    out = {}
    for key, (s, e) in {"period_a": (a_start, a_end), "period_b": (b_start, b_end)}.items():
        s, e = parse_date(s, key + " start"), parse_date(e, key + " end")
        if s > e:
            raise ValidationFailed(f"{key}: start must not be later than end.")
        row = db.rows(f"SELECT {_SUMMARY_COLS} FROM weather_observation WHERE city_id = :city_id "
                      "AND obs_date >= :start AND obs_date <= :end",
                      {"city_id": city_id, "hot": hot, "start": s, "end": e})[0]
        if not row["days"]:
            raise NotFoundError(f"No observations for {key} ({s} to {e}).")
        out[key] = {"start": s, "end": e, **row}
    deltas = {}
    for k in ("avg_temp_max_c", "avg_temp_min_c", "avg_apparent_max_c", "total_precipitation_mm",
              "avg_wind_speed_max_kmh", "hot_days"):
        a, b = out["period_a"][k], out["period_b"][k]
        deltas[k] = round(b - a, 2) if a is not None and b is not None else None
    return {"data_type": "observed", "city": {"city_id": city_id, "name": city["name"]}, "hot_day_threshold_c": hot,
            **out, "delta_b_minus_a": deltas}


def heatwave_events(db, city_id: int, start=None, end=None) -> dict[str, Any]:
    city, start, end = _city_range(db, city_id, start, end)
    params: dict[str, Any] = {"city_id": city_id}
    where = _where(start, end, params)
    series = db.rows(f"SELECT obs_date, temp_max_c FROM weather_observation WHERE {where} ORDER BY obs_date", params)
    events = detect_events(city["name"], [(r["obs_date"], r["temp_max_c"]) for r in series if r["temp_max_c"] is not None],
                           monthly_normals(db, city_id))
    per_year: dict[int, int] = {}
    for ev in events:
        per_year[int(ev["start"][:4])] = per_year.get(int(ev["start"][:4]), 0) + 1
    return {"data_type": "derived", "source": "Computed from the supplied historical dataset",
            "city": {"city_id": city_id, "name": city["name"]},
            "definition": {**cfg.HEATWAVE, "hot_day_threshold_c": hot_day_threshold(city["name"]),
                           "normal": "2000-2024 mean daily maximum for the same calendar month (in-sample)",
                           "note": "Project definition modelled on IMD plains criteria; not an official declaration."},
            "total_events": len(events), "events_per_year": [{"year": y, "events": n} for y, n in sorted(per_year.items())],
            "events": sorted(events, key=lambda e: e["start"], reverse=True)}


def dashboard_summary(db, city_id: int, month: int | None = None) -> dict[str, Any]:
    """Historical averages for the dashboard cards (calendar month climatology)."""
    city = city_service.get_city(db, city_id)
    clim = climatology(db, city_id)["items"]
    if month is not None and not 1 <= month <= 12:
        raise ValidationFailed("month must be between 1 and 12.")
    cur = next((r for r in clim if r["month"] == month), None) if month else None
    return {"data_type": "observed", "city": {"city_id": city_id, "name": city["name"]}, "month": month,
            "month_climatology": cur, "year_profile": clim,
            "note": "Historical averages for 2000-2024 - not today's weather."}


def data_quality(db) -> dict[str, Any]:
    """Data-quality checks on the imported historical table."""
    def build():
        cols = [r["name"] for r in db.rows("SELECT name FROM pragma_table_info('weather_observation')")]
        null_sql = ", ".join(f"SUM(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END) AS {c}" for c in cols)
        nulls = db.rows(f"SELECT {null_sql} FROM weather_observation")[0]
        coverage = db.rows(
            """SELECT c.name AS city, MIN(o.obs_date) AS first_date, MAX(o.obs_date) AS last_date,
                      COUNT(*) AS observed_days,
                      CAST(julianday(MAX(o.obs_date)) - julianday(MIN(o.obs_date)) AS INTEGER) + 1 AS expected_days
               FROM weather_observation o JOIN city c USING (city_id) GROUP BY c.name ORDER BY c.name""")
        for r in coverage:
            r["missing_days"] = r["expected_days"] - r["observed_days"]
        dup = db.rows("SELECT COUNT(*) AS n FROM (SELECT 1 FROM weather_observation GROUP BY city_id, obs_date HAVING COUNT(*) > 1)")[0]["n"]
        bad_temp = db.rows("SELECT COUNT(*) AS n FROM weather_observation WHERE temp_max_c < temp_min_c")[0]["n"]
        bad_range = db.rows("SELECT COUNT(*) AS n FROM weather_observation WHERE temp_max_c > 60 OR temp_min_c < -30")[0]["n"]
        rain_diff = db.rows("SELECT COUNT(*) AS n FROM weather_observation WHERE precipitation_sum_mm IS NOT rain_sum_mm")[0]["n"]
        total = db.rows("SELECT COUNT(*) AS n FROM weather_observation")[0]["n"]
        orphan = db.rows("SELECT COUNT(*) AS n FROM weather_observation o LEFT JOIN city c USING (city_id) WHERE c.city_id IS NULL")[0]["n"]
        no_coords = db.rows("SELECT COUNT(*) AS n FROM city WHERE latitude IS NULL OR longitude IS NULL")[0]["n"]
        checks = [
            {"check": "Duplicate (city, date) pairs", "issues": dup},
            {"check": "Observations without a matching city", "issues": orphan},
            {"check": "Rows where Tmax < Tmin", "issues": bad_temp},
            {"check": "Rows with implausible temperature (Tmax > 60 or Tmin < -30 °C)", "issues": bad_range},
            {"check": "Cities without map coordinates", "issues": no_coords},
            {"check": "Missing calendar days inside each city's date range", "issues": sum(r["missing_days"] for r in coverage)},
            {"check": "Total NULL values across all columns", "issues": sum(int(v or 0) for v in nulls.values())},
        ]
        notes = []
        if rain_diff == 0:
            notes.append("precipitation_sum_mm and rain_sum_mm are identical in every row of the source file (no snowfall in this dataset).")
        return {"total_rows": total, "null_counts": {k: int(v or 0) for k, v in nulls.items()}, "coverage": coverage,
                "checks": checks, "notes": notes, "all_checks_passed": all(c["issues"] == 0 for c in checks)}
    return cache.cached("data_quality", 600, build)
