"""Orchestrates: city + horizon -> predictor -> risk assessment -> personalisation -> explanation -> guidance."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.errors import ValidationFailed
from app.core.heat_scoring import categorize, explain, personalize
from app.services import cities as city_service, safety_content


def run_prediction(db, predictor, city_id: int, horizon_days: int, profile: dict[str, Any] | None,
                   today: date | None = None) -> dict[str, Any]:
    if not 0 <= horizon_days <= 14:
        raise ValidationFailed("horizon_days must be between 0 and 14.")
    city = city_service.get_city(db, city_id)
    target = (today or date.today()) + timedelta(days=horizon_days)
    res = predictor.predict(db, city, target, horizon_days)
    category = categorize(res.score)
    personal = personalize(res.score, profile)
    if res.is_demo:
        explanation = explain({"score": res.score, "components": res.score_components, "missing": res.missing_inputs})
        explanation_kind = "Rule-based breakdown of the scoring formula applied to the demo baseline values."
    else:
        explanation = ["The score is the trained model's heatwave probability multiplied by 100.",
                       "This application does not compute feature attributions (e.g. SHAP) for the model."]
        explanation_kind = "Model-level summary only; no feature attributions are available."
    return {
        "city": {"city_id": city["city_id"], "name": city["name"], "state": city["state"]},
        "target_date": res.target_date, "horizon_days": horizon_days, "as_of_date": res.as_of_date,
        "model": {"name": res.model_name, "version": res.model_version, "is_demo": res.is_demo,
                  "label": "DEMO PREDICTION (not a trained model)" if res.is_demo else "Trained model output"},
        "risk": {"score": res.score, "category": category},
        "personal": personal,
        "expected": res.expected, "heatwave_probability": res.heatwave_probability, "confidence": res.confidence,
        "context": res.context, "notes": res.notes,
        "explanation": {"kind": explanation_kind, "lines": explanation, "components": res.score_components},
        "recommendations": safety_content.recommendations_for(personal["personal_category"] or category, profile),
        "disclaimer": "Informational project metric - not an official heat warning or medical advice.",
    }
