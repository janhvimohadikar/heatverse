"""Tests against the REAL imported database (skipped automatically if it has not been imported)."""
import sqlite3
from datetime import date

import pytest

from app.core.errors import NotFoundError, ValidationFailed
from app.db.executor import SqliteExecutor
from app.ml.demo_predictor import DemoClimatologyPredictor
from app.services import analytics, cities, historical, map_service, prediction_service
from tests.helpers import REAL_DB, needs_data

pytestmark = needs_data


@pytest.fixture(scope="module")
def db():
    return SqliteExecutor(str(REAL_DB))


@pytest.fixture(scope="module")
def raw():
    c = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    yield c
    c.close()


def city_id(db, name):
    return next(c["city_id"] for c in cities.list_cities(db) if c["name"] == name)


def test_database_matches_expected_shape(db):
    cov = historical.date_coverage(db)
    assert cov["observations"] == 91320 and cov["cities"] == 10
    assert (cov["first_date"], cov["last_date"]) == ("2000-01-01", "2024-12-31")


def test_city_lookup(db):
    names = {c["name"] for c in cities.list_cities(db)}
    assert {"Delhi", "Mumbai", "Chennai", "Kolkata"} <= names
    with pytest.raises(NotFoundError):
        cities.get_city(db, 9999)


def test_date_and_city_filters(db):
    d = city_id(db, "Delhi")
    res = historical.get_observations(db, d, "2024-05-26", "2024-05-28", 1, 50)
    assert res["total"] == 3 and [r["obs_date"] for r in res["items"]] == ["2024-05-26", "2024-05-27", "2024-05-28"]
    assert res["items"][-1]["temp_max_c"] == 46.4
    with pytest.raises(ValidationFailed):
        historical.get_observations(db, d, "2024-06-01", "2024-05-01", 1, 10)
    with pytest.raises(ValidationFailed):
        historical.get_observations(db, d, "not-a-date", None, 1, 10)
    assert len(historical.get_observations(db, d, None, None, 1, 9999)["items"]) == 200  # page size is capped


def test_annual_trend_matches_raw_sql(db, raw):
    d = city_id(db, "Delhi")
    api = {r["period"]: r["avg_temp_max_c"] for r in analytics.temperature_trends(db, d, "annual")["items"]}
    expected = dict(raw.execute("SELECT CAST(strftime('%Y',obs_date) AS INT), ROUND(AVG(temp_max_c),2) FROM weather_observation "
                                "WHERE city_id=? GROUP BY 1", (d,)).fetchall())
    assert api == expected and len(api) == 25


def test_comparison_and_validation(db):
    ids = [city_id(db, n) for n in ("Delhi", "Mumbai")]
    r = analytics.city_comparison(db, ids, "peak_temp_max_c")
    delhi = next(s for s in r["summaries"] if s["name"] == "Delhi")
    assert delhi["peak_temp_max_c"] == 46.4
    with pytest.raises(ValidationFailed):
        analytics.city_comparison(db, ids, "humidity")  # humidity does not exist in the data


def test_heatwave_events_use_documented_definition(db):
    ev = analytics.heatwave_events(db, city_id(db, "Delhi"))
    assert ev["total_events"] == len(ev["events"]) > 0
    assert all(e["days"] >= 2 and e["peak_tmax_c"] >= 40 for e in ev["events"])
    assert "IMD" in ev["definition"]["note"]
    assert analytics.heatwave_events(db, city_id(db, "Bangalore"))["total_events"] == 0


def test_data_quality_passes(db):
    q = analytics.data_quality(db)
    assert q["total_rows"] == 91320 and q["all_checks_passed"]


def test_map_risk_valid_and_filters(db):
    r = map_service.risk_map(db, "historical", "risk", "2024-05-28")
    assert len(r["features"]) == 10 and sum(r["counts"].values()) == 10
    delhi = next(f for f in r["features"] if f["name"] == "Delhi")
    assert delhi["risk"]["category"] == "Extreme" and delhi["values"]["temp_max_c"] == 46.4
    assert r["data_type"] == "observed"
    for f in r["features"]:
        assert -90 < f["latitude"] < 90 and -180 < f["longitude"] < 180


def test_map_rejects_unsupported_layers_and_dates(db):
    with pytest.raises(ValidationFailed):
        map_service.risk_map(db, "historical", "confidence", None)
    with pytest.raises(ValidationFailed):
        map_service.risk_map(db, "historical", "humidity", None)
    with pytest.raises(NotFoundError):
        map_service.risk_map(db, "historical", "risk", "1990-01-01")
    conf = next(l for l in map_service.list_layers({}) if l["key"] == "confidence")
    assert conf["available"] is False and conf["reason"]


def test_surface_is_labelled_interpolated(db):
    s = map_service.surface(db, "temp_max", "2024-05-28")
    assert s["available"] and s["data_type"] == "interpolated" and "NOT" in s["warning"] and s["cells"]


def test_city_detail(db):
    d = map_service.city_detail(db, city_id(db, "Delhi"), "2024-05-28")
    assert len(d["trend_30d"]) == 30 and d["feature"]["risk"]["score"] >= 75 and d["explanation"]


def test_demo_prediction_is_clearly_labelled_and_has_no_fake_confidence(db):
    res = prediction_service.run_prediction(db, DemoClimatologyPredictor(), city_id(db, "Delhi"), 3, {}, today=date(2026, 5, 20))
    assert res["model"]["is_demo"] is True and "DEMO" in res["model"]["label"]
    assert res["confidence"] is None and res["heatwave_probability"] is None
    with pytest.raises(ValidationFailed):
        prediction_service.run_prediction(db, DemoClimatologyPredictor(), 1, 99, {})
