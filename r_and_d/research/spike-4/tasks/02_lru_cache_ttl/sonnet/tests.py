"""Tests for Task 02 — TTL Cache."""
import time
import threading
import pytest
from ttl_cache import TTLCache


def test_basic_get_put():
    c = TTLCache(max_size=10, ttl_seconds=60)
    c.put("a", 1)
    assert c.get("a") == 1
    assert c.get("missing") is None


def test_lru_eviction():
    c = TTLCache(max_size=2, ttl_seconds=60)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")  # touch a (now a is MRU, b is LRU)
    c.put("c", 3)  # should evict b
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_ttl_expiry():
    c = TTLCache(max_size=10, ttl_seconds=0.05)
    c.put("a", 1)
    assert c.get("a") == 1
    time.sleep(0.1)
    assert c.get("a") is None


def test_invalidate_older_than():
    c = TTLCache(max_size=10, ttl_seconds=60)
    c.put("a", 1)
    time.sleep(0.05)
    c.put("b", 2)
    n = c.invalidate_older_than(0.04)
    assert n >= 1
    assert c.get("a") is None
    assert c.get("b") == 2


def test_validates_args():
    with pytest.raises((ValueError, AssertionError)):
        TTLCache(max_size=0, ttl_seconds=60)
    with pytest.raises((ValueError, AssertionError)):
        TTLCache(max_size=10, ttl_seconds=-1)


def test_thread_safety_under_contention():
    c = TTLCache(max_size=100, ttl_seconds=60)
    errors = []
    def worker(worker_id):
        try:
            for i in range(50):
                c.put(f"k{worker_id}_{i}", i)
                c.get(f"k{worker_id}_{i}")
                if i % 10 == 0:
                    c.invalidate_older_than(0.001)
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(wid,)) for wid in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert errors == [], f"Race condition errors: {errors}"
