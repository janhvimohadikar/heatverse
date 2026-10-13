"""SQLAlchemy engine/session for the SQLite database (application tables + historical tables)."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

HISTORICAL_TABLES = {"city", "weather_observation", "import_log"}  # created by scripts/import_excel.py

_settings = get_settings()
engine = create_engine(_settings.database_url, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")  # SQLite ignores foreign keys unless this is enabled
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_app_tables() -> None:
    """Create application tables (users, predictions, alerts...). Historical tables are NOT touched."""
    from app import models  # noqa: F401  (registers the models)
    from app.db.base import Base

    tables = [t for t in Base.metadata.sorted_tables if t.name not in HISTORICAL_TABLES]
    Base.metadata.create_all(engine, tables=tables)
