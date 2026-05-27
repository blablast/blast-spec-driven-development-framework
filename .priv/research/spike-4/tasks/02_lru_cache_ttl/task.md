# Task 02 — LRU Cache with TTL

Implement a thread-safe LRU cache with per-entry TTL eviction in `ttl_cache.py`.

## Spec

```python
class TTLCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 60.0):
        """LRU cache with TTL; evicts LRU on capacity, expires on TTL."""

    def get(self, key: str):
        """Return value if present and not expired, else None."""

    def put(self, key: str, value):
        """Insert/update. Evict LRU when over capacity."""

    def invalidate_older_than(self, age_seconds: float) -> int:
        """Drop entries older than age. Return count removed."""
```

## Requirements

- Use `collections.OrderedDict` for LRU ordering
- `time.monotonic()` for TTL math
- Thread-safe: hold lock for ALL state-modifying paths (no TOCTOU races)
- Validate constructor args (max_size > 0, ttl_seconds > 0)
- Pure stdlib only

## Acceptance criteria

All tests in `tests.py` must pass.
