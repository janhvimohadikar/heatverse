"""
DEMO predictor - NOT a trained machine-learning model.

For a target date it averages the historical observations in a +/-7 day window around the same
day of the year (a "climatology" baseline) and converts the averages to a heat-risk score with the
same scoring service used everywhere else.  It also reports how often that window contained at least
one hot day in the 2000-2024 record (an empirical frequency, NOT a forecast probability).

It has no accuracy, no confidence value and no skill - it only exists so the full pipeline
(features -> prediction -> score -> explanation -> dashboard/map) can be demonstrated before a real
model is connected.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.core import cache
from app.core.heat_scoring import compute_score, hot_day_threshold
from app.ml.base import PredictionResult

WINDOW_DAYS = 7

_WINDOW = ("city_id = :c AND (ABS(CAST(strftime('%j', obs_date) AS INTEGER) - :doy) <= :w "
           "OR ABS(CAST(strftime('%j', obs_date) AS INTEGER) - :doy) >= 365 - :w)")


class DemoClimatologyPredictor:
    name = "demo-climatology-baseline"
    version = "1.0-demo"
    is_demo = True

    def predict(self, db, city: dict[str, Any], target_date: date, horizon_days: int) -> PredictionResult:
        doy = target_date.timetuple().tm_yday
        params = {"c": city["city_id"], "doy": doy, "w": WINDOW_DAYS}

        def load():
            clim = db.rows(
                f"""SELECT ROUND(AVG(temp_max_c), 2) AS tmax, ROUND(AVG(temp_min_c), 2) AS tmin,
                           ROUND(AVG(apparent_max_c), 2) AS app, COUNT(*) AS n_days,
                           COUNT(DISTINCT strftime('%Y', obs_date)) AS n_years
                    FROM weather_observation WHERE {_WINDOW}""", params)[0]
            hot = hot_day_threshold(city["name"])
            yrs = db.rows(
                f"""SELECT COUNT(*) AS n FROM (SELECT strftime('%Y', obs_date) AS y FROM weather_observation
                    WHERE {_WINDOW} AND temp_max_c >= :hot GROUP BY y)""", {**params, "hot": hot})[0]["n"]
            return clim, yrs, hot

        clim, years_with_hot, hot = cache.cached(f"demo:{city['city_id']}:{doy}", 3600, load)
        if not clim["n_days"]:
            return PredictionResult(self.name, self.version, True, target_date.isoformat(), horizon_days, None,
                                    notes=["No historical observations are available for this city and time of year."])
        expected = {"temp_max_c": clim["tmax"], "temp_min_c": clim["tmin"], "apparent_max_c": clim["app"]}
        res = compute_score(expected)  # no hot-day streak is available from a climatology baseline
        return PredictionResult(
            model_name=self.name, model_version=self.version, is_demo=True, target_date=target_date.isoformat(),
            horizon_days=horizon_days, score=res["score"], expected=expected, heatwave_probability=None, confidence=None,
            as_of_date=None,
            context={
                "method": f"Mean of {clim['n_years']} years of observations within +/-{WINDOW_DAYS} days of the same day of year",
                "years_in_record": clim["n_years"],
                "years_with_at_least_one_hot_day": years_with_hot,
                "hot_day_threshold_c": hot,
                "historical_frequency_note": ("Empirical frequency from the 2000-2024 record. It is NOT a probability forecast."),
            },
            notes=["DEMO prediction: a climatology baseline, not a trained model. Actual weather can be much hotter or cooler than the seasonal average."],
            score_components=res["components"], missing_inputs=res["missing"])
