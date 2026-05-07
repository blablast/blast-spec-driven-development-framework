"""Tests for Task 05 — Async Worker Pool."""
import asyncio
import time
import pytest
from worker_pool import AsyncWorkerPool


@pytest.mark.asyncio
async def test_basic_submit():
    pool = AsyncWorkerPool(concurrency=2)
    async def task():
        return 42
    result = await pool.submit(task)
    assert result == 42
    await pool.shutdown()


@pytest.mark.asyncio
async def test_concurrency_limit():
    pool = AsyncWorkerPool(concurrency=2)
    in_flight = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def task():
        nonlocal in_flight, max_seen
        async with lock:
            in_flight += 1
            max_seen = max(max_seen, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        return "ok"

    results = await asyncio.gather(*[pool.submit(task) for _ in range(10)])
    assert all(r == "ok" for r in results)
    assert max_seen <= 2, f"concurrency exceeded limit: {max_seen}"
    await pool.shutdown()


@pytest.mark.asyncio
async def test_map_preserves_order():
    pool = AsyncWorkerPool(concurrency=4)
    async def task(i):
        await asyncio.sleep((10 - i) * 0.01)
        return i * 2
    items = list(range(10))
    results = await pool.map(task, items)
    assert results == [i * 2 for i in items], "map must preserve input order"
    await pool.shutdown()


@pytest.mark.asyncio
async def test_exception_propagates():
    pool = AsyncWorkerPool(concurrency=2)
    async def failing():
        raise ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        await pool.submit(failing)
    await pool.shutdown()


@pytest.mark.asyncio
async def test_shutdown_blocks_new():
    pool = AsyncWorkerPool(concurrency=2)
    async def task():
        return "ok"
    await pool.submit(task)
    await pool.shutdown()
    with pytest.raises(RuntimeError):
        await pool.submit(task)
