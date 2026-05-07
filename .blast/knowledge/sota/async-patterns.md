# SOTA: Python async patterns (2026)

**Last refreshed**: 2026-05-07
**Refresh cadence**: every 6 months

## Concurrency primitives

| Need | SOTA choice | Avoid |
|---|---|---|
| Bounded concurrency | `asyncio.Semaphore` | manual counter + lock |
| Task pool with results | `asyncio.gather()` for known list, `TaskGroup` (3.11+) for dynamic | `asyncio.wait()` (lower-level, more error-prone) |
| Producer/consumer | `asyncio.Queue` | own implementations |
| Cancellation | `asyncio.CancelledError` handling + `TaskGroup` | manual flag-based cancellation |
| Exception aggregation | `TaskGroup` raises `ExceptionGroup` (3.11+), `gather(return_exceptions=True)` for older | swallowing exceptions |
| Timeouts | `asyncio.timeout()` context manager (3.11+) | `wait_for` (older API) |

## Idiomatic patterns (2026)

### TaskGroup for concurrent IO (3.11+)

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(fetch(url1))
    tg.create_task(fetch(url2))
# Auto-await all, raise ExceptionGroup on any failure
```

### Bounded concurrency with Semaphore

```python
sem = asyncio.Semaphore(10)
async def bounded(coro):
    async with sem:
        return await coro
results = await asyncio.gather(*[bounded(fetch(url)) for url in urls])
```

### Async iterator with backpressure

```python
async def stream():
    queue = asyncio.Queue(maxsize=100)
    # ...
```

## Anti-patterns to flag

- `time.sleep()` in async function → `await asyncio.sleep()`
- Synchronous library in async code → wrap in `asyncio.to_thread()` (3.9+) or use async alternative
- `asyncio.run()` inside async code → just `await`
- Catching bare `Exception` swallowing CancelledError → must re-raise CancelledError
- Manual event loop creation in 2026 → `asyncio.run()` is standard entry point
- Threading + asyncio mixing without `asyncio.to_thread()` → race conditions

## When to use threading instead of asyncio

- CPU-bound work → `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`
- Blocking I/O without async equivalent → `asyncio.to_thread()` for occasional, threading for heavy
- Existing sync codebase migration → don't rewrite for async unless I/O bound

## References

- Python asyncio docs: https://docs.python.org/3/library/asyncio.html
- TaskGroup PEP 654: https://peps.python.org/pep-0654/
- Real Python async tutorial: search for current
