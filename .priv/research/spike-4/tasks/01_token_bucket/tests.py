"""Tests for Task 01 — Token Bucket Rate Limiter."""
import threading
import time
import pytest
from rate_limiter import RateLimiter


def test_basic_acquire():
    rl = RateLimiter(rate=2.0, burst=4)
    for _ in range(4):
        assert rl.try_acquire() is True
    assert rl.try_acquire() is False


def test_refill():
    rl = RateLimiter(rate=10.0, burst=2)
    assert rl.try_acquire(2) is True
    assert rl.try_acquire() is False
    time.sleep(0.25)
    assert rl.try_acquire(2) is True


def test_acquire_multiple_tokens():
    rl = RateLimiter(rate=1.0, burst=5)
    assert rl.try_acquire(3) is True
    assert rl.try_acquire(2) is True
    assert rl.try_acquire(1) is False


def test_thread_safety():
    rl = RateLimiter(rate=1000.0, burst=100)
    successes = []
    def worker():
        for _ in range(50):
            if rl.try_acquire():
                successes.append(1)
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert 100 <= len(successes) <= 200


def test_uses_monotonic_clock():
    """Sanity: source code must reference time.monotonic, not time.time."""
    import inspect
    import rate_limiter
    src = inspect.getsource(rate_limiter)
    assert "monotonic" in src, "Must use time.monotonic() for refill timing"
