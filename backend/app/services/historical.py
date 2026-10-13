"""Queries against the historical observation table (read-only)."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.core import heat_config as cfg
from app.core.errors import NotFoundError, ValidationFailed

OBS_FIELDS = [
    "obs_date", "temp_max_c", "temp_min_c", "temp_mean_c", "apparent_max_c", "apparent_min_c", "apparent_mean_c",
    "precipitation_sum_mm", "rain_sum_mm", "weather_code", "wind_speed_max_kmh", "wind_gusts_max_kmh",
    "wind_direction_deg", "precipitation_hours_h",
]


def parse_date(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValidationFailed(f"'{name}' must be an ISO date (YYYY-MM-DD); got '{value}'.")


def date_coverage(db) -> dict[str, Any]:
    r = db.rows("SELECT MIN(obs_date) AS first_date, MAX(obs_date) AS last_date, COUNT(*) AS observations, "
                "COUNT(DISTINCT city_id) AS cities FROM weather_observation")[0]
    if not r["observations"]:
        raise NotFoundError("The historical database is empty. Run scripts/import_excel.py first.")
    return r


def describe_weather_code(code: int | None) -> str | None:
    if code is None:
        return None
    return cfg.WMO_WEATHER_CODES.get(int(code), f"WMO code {int(code)}")


def get_observations(db, city_id: int, start: str | None, end: str | None, page: int, page_size: int) -> dict[str, Any]:
    start, end = parse_date(start, "start"), parse_date(end, "end")
    if start and end and start > end:
        raise ValidationFailed("'start' must not be later than 'end'.")
    page_size = max(1, min(page_size, 200))
    page = max(1, page)
    where = "city_id = :city_id"
    params: dict[str, Any] = {"city_id": city_id}
    if start:
        where += " AND obs_date >= :start"
        params["start"] = start
    if end:
        where += " AND obs_date <= :end"
        params["end"] = end
    total = db.rows(f"SELECT COUNT(*) AS n FROM weather_observation WHERE {where}", params)[0]["n"]
    rows = db.rows(
        f"SELECT {', '.join(OBS_FIELDS)} FROM weather_observation WHERE {where} "
        "ORDER BY obs_date LIMIT :limit OFFSET :offset",
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    for r in rows:
        r["weather_description"] = describe_weather_code(r["weather_code"])
    return {"data_type": "observed", "source": "Supplied historical dataset (Excel import)", "page": page,
            "page_size": page_size, "total": total, "items": rows}
