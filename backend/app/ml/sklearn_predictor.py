"""
Adapter for a user-supplied trained model (scikit-learn style, loaded with joblib).

NOTE FOR THE PROJECT AUTHOR: no trained model was supplied when this project was generated, so this adapter
has NOT been tested against a real model. Treat it as the integration point described in the README.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.errors import ValidationFailed
from app.core.heat_scoring import categorize, hot_day_threshold
from app.ml import feature_spec
from app.ml.base import PredictionResult


class SklearnPredictor:
    is_demo = False

    def __init__(self, model, name: str = "user-supplied-model", version: str = "1"):
        self.model, self.name, self.version = model, name, version

    def _features(self, db, city: dict[str, Any]) -> tuple[dict[str, float], str]:
        last = db.rows("SELECT MAX(obs_date) AS d FROM weather_observation WHERE city_id = :c", {"c": city["city_id"]})[0]["d"]
        start = (date.fromisoformat(last) - timedelta(days=6)).isoformat()
        rows = db.rows("SELECT * FROM weather_observation WHERE city_id = :c AND obs_date >= :s AND obs_date <= :e ORDER BY obs_date",
                       {"c": city["city_id"], "s": start, "e": last})
        if len(rows) < 7:
            raise ValidationFailed("Fewer than 7 recent observations are available, so the model features cannot be built.")
        today = rows[-1]
        thr = hot_day_threshold(city["name"])
        streak = 0
        for r in reversed(rows):
            if r["temp_max_c"] is not None and r["temp_max_c"] >= thr:
                streak += 1
            else:
                break
        feats = {
            "temp_max_c": today["temp_max_c"], "temp_min_c": today["temp_min_c"], "apparent_max_c": today["apparent_max_c"],
            "temp_max_mean_3d": sum(r["temp_max_c"] for r in rows[-3:]) / 3,
            "temp_max_mean_7d": sum(r["temp_max_c"] for r in rows) / 7,
            "precipitation_sum_7d_mm": sum(r["precipitation_sum_mm"] or 0 for r in rows),
            "wind_speed_max_kmh": today["wind_speed_max_kmh"], "month": int(last[5:7]), "hot_day_streak": streak,
        }
        for k in feature_spec.FEATURE_ORDER:
            v = feats.get(k)
            lo, hi = feature_spec.VALID_RANGES[k]
            if v is None or not lo <= v <= hi:
                raise ValidationFailed(f"Model input '{k}' is missing or outside the valid range ({lo}..{hi}).")
        return feats, last

    def predict(self, db, city: dict[str, Any], target_date: date, horizon_days: int) -> PredictionResult:
        feats, as_of = self._features(db, city)
        X = [[feats[k] for k in feature_spec.FEATURE_ORDER]]
        prob = float(self.model.predict_proba(X)[0][1])
        score = int(round(prob * 100))
        return PredictionResult(
            model_name=self.name, model_version=self.version, is_demo=False, target_date=target_date.isoformat(),
            horizon_days=horizon_days, score=score, expected={}, heatwave_probability=round(prob, 4),
            confidence=None, as_of_date=as_of, context={"features": feats, "score_meaning": "model probability x 100"},
            notes=[f"Prediction uses the most recent observations in the database (as of {as_of}). "
                   "The probability is the model's raw output; its calibration is not verified by this application."])
