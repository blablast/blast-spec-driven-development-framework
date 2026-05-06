"""LRU cache with TTL eviction. Used for storing API responses."""
import time
import threading
from collections import OrderedDict


class TTLCache:
    """Thread-safe LRU cache with per-entry TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 60.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: "OrderedDict[str, tuple[float, object]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        if key not in self._store:
            return None
        with self._lock:
            ts, value = self._store[key]
            if time.time() - ts > self._ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def put(self, key: str, value: object) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)
            self._store.move_to_end(key)
            if len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def invalidate_older_than(self, age_seconds: float) -> int:
        """Drop entries older than `age_seconds`. Returns count removed."""
        count = 0
        cutoff = time.time() - age_seconds
        for key in list(self._store.keys()):
            ts, _ = self._store[key]
            if ts < cutoff:
                with self._lock:
                    del self._store[key]
                    count += 1
        return count
