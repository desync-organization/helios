"""Bounded rate and idempotency guards."""

from __future__ import annotations

import time
from collections import OrderedDict, deque


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._requests: dict[str, deque[float]] = {}

    def allow(self, key: str, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        requests = self._requests.setdefault(key, deque())
        while requests and requests[0] <= current - self._window:
            requests.popleft()
        if len(requests) >= self._limit:
            return False
        requests.append(current)
        return True


class PromptDeduper:
    def __init__(self, ttl_seconds: float, capacity: int = 4096) -> None:
        self._ttl = ttl_seconds
        self._capacity = capacity
        self._items: OrderedDict[str, tuple[float, str]] = OrderedDict()

    def get(self, key: str, *, now: float | None = None) -> str | None:
        current = time.monotonic() if now is None else now
        value = self._items.get(key)
        if value is None:
            return None
        expires, task_id = value
        if expires <= current:
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return task_id

    def put(self, key: str, task_id: str, *, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        self._items[key] = (current + self._ttl, task_id)
        self._items.move_to_end(key)
        while len(self._items) > self._capacity:
            self._items.popitem(last=False)
