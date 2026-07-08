"""Simple in-process TTL cache for upstream API responses."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")
_store: dict[str, tuple[float, Any]] = {}


def cached(
    key: str,
    ttl_sec: float,
    factory: Callable[[], T],
    *,
    cache_empty: bool = True,
) -> T:
    now = time.monotonic()
    hit = _store.get(key)
    if hit is not None:
        expires_at, value = hit
        if now < expires_at:
            return value
    value = factory()
    should_store = cache_empty
    if not cache_empty:
        if isinstance(value, list):
            should_store = len(value) > 0
        elif value is None:
            should_store = False
        else:
            should_store = bool(value)
    if should_store:
        _store[key] = (now + ttl_sec, value)
    return value
