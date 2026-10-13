"""Heat-risk scoring service (pure Python, no web framework needed)."""
from __future__ import annotations

from typing import Any, Optional

from app.core import heat_config as cfg


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def categorize(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    s = int(round(score))
    for lo, hi, label in cfg.CATEGORIES:
        if lo <= s <= hi:
            return label
    return cfg.CATEGORIES[-1][2] if s > 100 else cfg.CATEGORIES[0][2]


def hot_day_threshold(city_name: str | None) -> float:
    if city_name in cfg.COASTAL_CITIES:
        return cfg.COASTAL_HOT_DAY_THRESHOLD_C
    return cfg.HOT_DAY_THRESHOLD_C


def compute_score(values: dict[str, Optional[float]]) -> dict[str, Any]:
    """
    values: any of temp_max_c, apparent_max_c, temp_min_c, hot_day_streak (None / absent = missing).
    Returns the score, category, per-component breakdown and the list of missing inputs.
    """
    available = {}
    missing = []
    for key in cfg.COMPONENTS:
        v = values.get(key)
        if v is None:
            missing.append(key)
        else:
            available[key] = float(v)

    if not available:
        return {"score": None, "category": None, "components": [], "missing": missing,
                "scoring_version": cfg.SCORING_VERSION}

    total_weight = sum(cfg.COMPONENTS[k]["weight"] for k in available)
    components = []
    score = 0.0
    for key, v in available.items():
        c = cfg.COMPONENTS[key]
        sub = clamp01((v - c["low"]) / (c["high"] - c["low"])) * 100.0
        weight_used = c["weight"] / total_weight
        points = sub * weight_used
        score += points
        components.append({
            "key": key, "label": c["label"], "value": round(v, 1), "unit": c["unit"],
            "sub_score": round(sub, 1), "weight": round(weight_used, 3), "points": round(points, 1),
        })
    final = int(round(max(0.0, min(100.0, score))))
    components.sort(key=lambda x: x["points"], reverse=True)
    return {"score": final, "category": categorize(final), "components": components,
            "missing": missing, "scoring_version": cfg.SCORING_VERSION}


def explain(result: dict[str, Any]) -> list[str]:
    """Plain-language, rule-based explanation (exact arithmetic from the scoring formula; not SHAP)."""
    if result.get("score") is None:
        return ["Not enough data to calculate a score."]
    lines = []
    for c in result["components"]:
        if c["points"] <= 0:
            continue
        val = int(c["value"]) if c["unit"] == "days" else c["value"]
        lines.append(f'{c["label"]} of {val} {c["unit"]} contributes {c["points"]} of the {result["score"]} points.')
    if not lines:
        lines.append("All inputs are below the thresholds where the score starts to rise.")
    if result.get("missing"):
        lines.append("Not available for this score: " + ", ".join(result["missing"]) + " (weights were redistributed).")
    return lines


def personalize(score: Optional[int], profile: dict[str, Any] | None) -> dict[str, Any]:
    """Apply the documented personal-factor adjustments. Returns base score, personal score and reasons."""
    if score is None:
        return {"base_score": None, "personal_score": None, "personal_category": None, "adjustments": []}
    adjustments = []
    p = profile or {}
    adj = cfg.PERSONAL_ADJUSTMENTS
    age = p.get("age")
    if age is not None and (age >= 60 or age <= 5):
        adjustments.append({"label": adj["age_vulnerable"]["label"], "points": adj["age_vulnerable"]["points"]})
    if p.get("is_outdoor_worker"):
        adjustments.append({"label": adj["outdoor_worker"]["label"], "points": adj["outdoor_worker"]["points"]})
    level = p.get("activity_level")
    if level == "high":
        adjustments.append({"label": adj["high_activity"]["label"], "points": adj["high_activity"]["points"]})
    elif level == "moderate":
        adjustments.append({"label": adj["moderate_activity"]["label"], "points": adj["moderate_activity"]["points"]})
    # Personal factors only matter when there is some heat to amplify.
    extra = sum(a["points"] for a in adjustments) if score >= 10 else 0
    personal = max(0, min(100, score + extra))
    return {"base_score": score, "personal_score": personal, "personal_category": categorize(personal),
            "adjustments": adjustments if score >= 10 else []}
