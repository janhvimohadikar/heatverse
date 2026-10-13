"""Heatwave-event detection using the documented project definition (see core/heat_config.py)."""
from __future__ import annotations

from typing import Any, Sequence

from app.core import heat_config as cfg
from app.core.heat_scoring import hot_day_threshold


def detect_events(city_name: str, series: Sequence[tuple[str, float]], monthly_normal: dict[int, float]) -> list[dict[str, Any]]:
    """
    series: [(iso_date, tmax_c)] sorted by date, one row per day.
    monthly_normal: {month_number: mean Tmax}.
    Returns events with start/end dates, length, peak, mean departure and severity.
    """
    hw = cfg.HEATWAVE
    threshold = hot_day_threshold(city_name)
    events: list[dict[str, Any]] = []
    current: list[tuple[str, float, float]] = []  # (date, tmax, departure)

    def flush():
        if len(current) >= hw["min_consecutive_days"]:
            tmaxs = [t for _, t, _ in current]
            deps = [d for _, _, d in current]
            severe = any(d >= hw["severe_departure_c"] or t >= hw["severe_absolute_tmax_c"] for _, t, d in current)
            events.append({
                "start": current[0][0], "end": current[-1][0], "days": len(current),
                "peak_tmax_c": round(max(tmaxs), 1), "mean_tmax_c": round(sum(tmaxs) / len(tmaxs), 1),
                "max_departure_c": round(max(deps), 1), "severity": "Severe" if severe else "Heatwave",
            })

    prev_date = None
    for iso, tmax in series:
        month = int(iso[5:7])
        normal = monthly_normal.get(month)
        dep = (tmax - normal) if normal is not None else 0.0
        is_hw = tmax >= threshold and (dep >= hw["min_departure_c"] or tmax >= hw["absolute_tmax_c"])
        contiguous = prev_date is not None and _next_day(prev_date) == iso
        if is_hw:
            if current and not contiguous:
                flush()
                current = []
            current.append((iso, tmax, dep))
        else:
            flush()
            current = []
        prev_date = iso
    flush()
    return events


def _next_day(iso: str) -> str:
    from datetime import date, timedelta

    return (date.fromisoformat(iso) + timedelta(days=1)).isoformat()
