"""
A minimal "run SQL, get list-of-dicts" interface.

Services depend only on `.rows(sql, params)`.  In the web app the implementation is `SAExecutor`
(SQLAlchemy session); for scripts and unit tests `SqliteExecutor` uses the standard library.
SQL uses named parameters (:name), which both implementations understand.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Protocol


class Executor(Protocol):
    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...


class SqliteExecutor:
    def __init__(self, path: str):
        self.path = path

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params or {}).fetchall()]
        finally:
            conn.close()


class SAExecutor:
    def __init__(self, session):
        self.session = session

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        from sqlalchemy import text

        result = self.session.execute(text(sql), params or {})
        return [dict(r) for r in result.mappings().all()]
