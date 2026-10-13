"""Tiny in-memory TTL cache for expensive aggregations and external API calls."""
from __future__ import annotations

import time
from typing import Any, Callable

_store: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl_seconds: int, producer: Callable[[], Any]) -> Any:
    now = time.monotonic()
    hit = _store.get(key)
    if hit and now - hit[0] < ttl_seconds:
        return hit[1]
    value = producer()
    _store[key] = (now, value)
    return value


def clear() -> None:
    _store.clear()
