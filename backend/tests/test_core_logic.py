"""Framework-free tests: scoring, security, interpolation, heatwave detection."""
from app.core import heat_config as cfg
from app.core.heat_scoring import categorize, compute_score, explain, personalize
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.geo import haversine_km, idw_grid
from app.services.heatwave_events import detect_events


def test_category_boundaries_match_spec():
    assert [categorize(s) for s in (0, 24, 25, 49, 50, 74, 75, 100)] == \
        ["Low", "Low", "Moderate", "Moderate", "High", "High", "Extreme", "Extreme"]
    assert categorize(None) is None


def test_score_is_zero_for_cool_day_and_high_for_extreme_day():
    assert compute_score({"temp_max_c": 20, "apparent_max_c": 18, "temp_min_c": 8, "hot_day_streak": 0})["score"] == 0
    hot = compute_score({"temp_max_c": 46.4, "apparent_max_c": 50, "temp_min_c": 32, "hot_day_streak": 5})
    assert hot["score"] == 100 and hot["category"] == "Extreme"


def test_missing_inputs_are_reported_not_invented():
    r = compute_score({"temp_max_c": 40, "apparent_max_c": None})
    assert set(r["missing"]) == {"apparent_max_c", "temp_min_c", "hot_day_streak"}
    assert r["score"] == round(100 * (40 - 30) / 16)  # only Tmax available -> weight 100%
    assert compute_score({})["score"] is None


def test_weights_sum_to_one():
    assert abs(sum(c["weight"] for c in cfg.COMPONENTS.values()) - 1.0) < 1e-9


def test_explanation_mentions_real_numbers():
    text = " ".join(explain(compute_score({"temp_max_c": 41.2})))
    assert "41.2" in text


def test_personalisation_is_capped_and_documented():
    p = personalize(95, {"age": 70, "is_outdoor_worker": True, "activity_level": "high"})
    assert p["personal_score"] == 100 and len(p["adjustments"]) == 3
    assert personalize(5, {"age": 70})["personal_score"] == 5  # nothing to amplify
    assert personalize(None, {})["personal_score"] is None


def test_password_hashing():
    h = hash_password("correct horse")
    assert "correct horse" not in h
    assert verify_password("correct horse", h) and not verify_password("wrong", h)
    assert not verify_password("x", "garbage")


def test_jwt_roundtrip_and_tamper():
    t = create_access_token(7, "s" * 40, 5)
    assert decode_access_token(t, "s" * 40)["sub"] == "7"
    assert decode_access_token(t, "z" * 40) is None
    assert decode_access_token(t + "x", "s" * 40) is None


def test_haversine_delhi_mumbai():
    d = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < d < 1200


def test_idw_respects_coverage_and_does_not_extrapolate_far():
    pts = [(28.6, 77.2, 40.0), (19.1, 72.9, 30.0)]
    cells = idw_grid(pts, step_deg=1.0, max_km=300)
    assert cells and all(30.0 <= c["value"] <= 40.0 for c in cells)
    assert all(min(haversine_km(c["lat"], c["lon"], a, b) for a, b, _ in pts) <= 300 for c in cells)
    assert not any(c["lat"] < 12 for c in cells)  # nothing near southern India -> no cells there


def test_heatwave_detection_rules():
    normal = {5: 38.0}
    days = [("2024-05-01", 41.0), ("2024-05-02", 41.5),                       # hot but < 4.5 above normal: not a heatwave
            ("2024-05-10", 43.0), ("2024-05-11", 44.0), ("2024-05-12", 43.5),  # >= 4.5 above normal for 3 days
            ("2024-05-20", 46.0)]                                              # single day: too short
    events = detect_events("Delhi", days, normal)
    assert len(events) == 1
    assert events[0]["start"] == "2024-05-10" and events[0]["days"] == 3 and events[0]["peak_tmax_c"] == 44.0


def test_non_consecutive_hot_days_are_separate():
    normal = {5: 38.0}
    days = [("2024-05-10", 45.0), ("2024-05-12", 45.0)]  # 11th missing -> not consecutive
    assert detect_events("Delhi", days, normal) == []
