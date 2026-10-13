"""Pytest fixtures.  The API tests run against a COPY of the real database so the original is never modified."""
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.helpers import REAL_DB  # noqa: E402


@pytest.fixture(scope="session")
def tmp_db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "test.db"
    if REAL_DB.exists():
        shutil.copyfile(REAL_DB, path)
    return path


@pytest.fixture(scope="session")
def client(tmp_db_path):
    os.environ["DATABASE_PATH"] = str(tmp_db_path)
    os.environ["SECRET_KEY"] = "pytest-only-secret-key-0123456789-abcdefghij"
    os.environ["LIVE_WEATHER_ENABLED"] = "false"
    os.environ["HOSPITALS_ENABLED"] = "false"
    os.environ["MODEL_PATH"] = ""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _signup(client, email, password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def user_token(client):
    return _signup(client, "student@example.com")


@pytest.fixture(scope="session")
def admin_token(client):
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models import User, UserProfile

    with SessionLocal() as s:
        u = User(email="admin@example.com", password_hash=hash_password("adminpass123"), role="admin")
        u.profile = UserProfile()
        s.add(u)
        s.commit()
    r = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "adminpass123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}
