# Task 01 — Token Bucket Rate Limiter

Implement a thread-safe token bucket rate limiter in `rate_limiter.py`.

## Spec

```python
class RateLimiter:
    def __init__(self, rate: float, burst: int):
        """rate = tokens/sec; burst = bucket capacity (starts full)."""

    def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking attempt. Return True if acquired, False if not enough."""
```

## Requirements

- Use `time.monotonic()` (NOT `time.time()`) for clock
- Lazy refill: compute on each call based on elapsed time
- Thread-safe: protect bucket state with `threading.Lock`
- Pure stdlib only (no third-party deps)

## Acceptance criteria

All tests in `tests.py` must pass.
