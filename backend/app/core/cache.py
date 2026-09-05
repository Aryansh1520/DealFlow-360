"""Pluggable cache — `BACKEND_PHASE_3.md` Task 6.

`InProcessLRUCache` ships and is wired by default. `RedisCache` is a real class
selected by `CACHE_BACKEND=redis`, present so the seam is genuine, not used in the
demo.

The win: cache keys **embed the policy version and a catalogue epoch**, so
activating a new policy or editing the catalogue changes the key and the old entry
is simply never read again — no TTL guessing, no stale-pricing window.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Protocol

from app.config.settings import settings


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    def invalidate_prefix(self, prefix: str) -> None: ...


class InProcessLRUCache:
    def __init__(self, max_entries: int = 1024) -> None:
        self._data: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._max = max_entries
        self._lock = RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            value, expires_at = item
            if expires_at is not None and expires_at < time.monotonic():
                self._data.pop(key, None)
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            expires_at = time.monotonic() + ttl if ttl else None
            self._data[key] = (value, expires_at)
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [k for k in self._data if k.startswith(prefix)]:
                self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisCache:  # pragma: no cover - not exercised in the demo
    def __init__(self, url: str) -> None:
        import redis  # type: ignore

        self._client = redis.Redis.from_url(url)

    def get(self, key: str) -> Any | None:
        import pickle

        raw = self._client.get(key)
        return pickle.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        import pickle

        self._client.set(key, pickle.dumps(value), ex=ttl)

    def invalidate_prefix(self, prefix: str) -> None:
        for key in self._client.scan_iter(match=f"{prefix}*"):
            self._client.delete(key)


def _build_cache() -> Cache:
    backend = getattr(settings, "cache_backend", "memory")
    if backend == "redis":
        return RedisCache(settings.redis_url)
    return InProcessLRUCache()


cache: Cache = _build_cache()
