"""End-to-end API tests using FastAPI's TestClient (needs the backend dependencies installed)."""
from tests.conftest import auth
from tests.helpers import needs_data


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "ok" and body["model"]["mode"] == "demo" and body["model"]["confidence_available"] is False


@needs_data
def test_cities_and_historical_filters(client):
    items = client.get("/api/cities").json()["items"]
    assert len(items) == 10
    delhi = next(c for c in items if c["name"] == "Delhi")
    r = client.get("/api/weather/historical", params={"city_id": delhi["city_id"], "start": "2024-05-26", "end": "2024-05-28"})
    assert r.status_code == 200 and r.json()["total"] == 3
    assert client.get("/api/weather/historical", params={"city_id": delhi["city_id"], "page_size": 500}).status_code == 422
    assert client.get("/api/weather/historical", params={"city_id": 9999}).status_code == 404


@needs_data
def test_analytics_and_validation(client):
    r = client.get("/api/analytics/temperature-trends", params={"city_id": 4, "granularity": "annual"})
    assert r.status_code == 200 and len(r.json()["items"]) == 25
    assert client.get("/api/analytics/temperature-trends", params={"city_id": 4, "granularity": "weekly"}).status_code == 422
    assert client.get("/api/analytics/city-comparison", params={"city_ids": "1,2", "metric": "humidity"}).status_code == 422
    assert client.get("/api/analytics/city-comparison", params={"city_ids": "a,b"}).status_code == 422


@needs_data
def test_map_endpoints(client):
    r = client.get("/api/map/risk", params={"date": "2024-05-28", "layer": "risk"})
    assert r.status_code == 200 and len(r.json()["features"]) == 10
    assert client.get("/api/map/risk", params={"layer": "confidence"}).status_code == 422
    assert client.get("/api/map/risk", params={"date": "1990-01-01"}).status_code == 404
    layers = client.get("/api/map/layers").json()["items"]
    assert next(l for l in layers if l["key"] == "confidence")["available"] is False
    assert client.get("/api/map/surface", params={"layer": "temp_max", "date": "2024-05-28"}).json()["available"] is True
    demo = client.get("/api/map/risk", params={"mode": "demo_prediction", "horizon_days": 2}).json()
    assert demo["data_type"] == "demo" and "DEMO" in demo["data_type_note"]


def test_auth_flow(client, user_token):
    assert client.post("/api/auth/signup", json={"email": "student@example.com", "password": "password123"}).status_code == 409
    assert client.post("/api/auth/signup", json={"email": "bad-email", "password": "password123"}).status_code == 422
    assert client.post("/api/auth/signup", json={"email": "x@example.com", "password": "short"}).status_code == 422
    assert client.post("/api/auth/login", json={"email": "student@example.com", "password": "wrong-password"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    me = client.get("/api/auth/me", headers=auth(user_token)).json()
    assert me["role"] == "user" and "password" not in str(me)


def test_signup_cannot_self_assign_admin(client):
    r = client.post("/api/auth/signup", json={"email": "sneaky@example.com", "password": "password123", "role": "admin"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "user"


@needs_data
def test_prediction_requires_auth_and_is_labelled_demo(client, user_token):
    assert client.post("/api/predictions", json={"city_id": 4}).status_code == 401
    assert client.post("/api/predictions", json={"city_id": 4, "horizon_days": 99}, headers=auth(user_token)).status_code == 422
    r = client.post("/api/predictions", json={"city_id": 4, "horizon_days": 2}, headers=auth(user_token))
    assert r.status_code == 201
    body = r.json()
    assert body["model"]["is_demo"] is True and body["confidence"] is None and body["heatwave_probability"] is None
    hist = client.get("/api/predictions/history", headers=auth(user_token)).json()
    assert hist["total"] >= 1 and hist["items"][0]["is_demo"] is True
    assert client.delete("/api/predictions/history", headers=auth(user_token)).status_code == 204
    assert client.get("/api/predictions/history", headers=auth(user_token)).json()["total"] == 0


def test_profile_roundtrip(client, user_token):
    body = {"full_name": "Test Student", "age": 21, "is_outdoor_worker": True, "activity_level": "high", "theme": "dark"}
    assert client.put("/api/profile", json=body, headers=auth(user_token)).status_code == 200
    got = client.get("/api/profile", headers=auth(user_token)).json()
    assert got["full_name"] == "Test Student" and got["activity_level"] == "high"
    assert client.put("/api/profile", json={**body, "age": 500}, headers=auth(user_token)).status_code == 422


def test_admin_endpoints_are_protected_on_the_backend(client, user_token, admin_token):
    for path in ("/api/admin/overview", "/api/admin/users", "/api/admin/alerts", "/api/admin/data-quality", "/api/admin/audit-log"):
        assert client.get(path).status_code == 401, path
        assert client.get(path, headers=auth(user_token)).status_code == 403, path
        assert client.get(path, headers=auth(admin_token)).status_code == 200, path


def test_admin_alert_lifecycle_and_self_protection(client, admin_token):
    h = auth(admin_token)
    r = client.post("/api/admin/alerts", json={"level": "advisory", "title": "Test notice", "message": "Hello"}, headers=h)
    assert r.status_code == 201
    assert any(a["title"] == "Test notice" for a in client.get("/api/alerts/active").json()["items"])
    assert client.delete(f"/api/admin/alerts/{r.json()['alert_id']}", headers=h).status_code == 204
    me = client.get("/api/auth/me", headers=h).json()
    assert client.patch(f"/api/admin/users/{me['user_id']}", json={"role": "user"}, headers=h).status_code == 400


def test_hospital_endpoint_validation(client):
    assert client.get("/api/hospitals/nearby").status_code == 422
