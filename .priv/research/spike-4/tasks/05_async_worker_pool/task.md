# Task 05 — Async Worker Pool

Implement a bounded-concurrency async worker pool in `worker_pool.py`.

## Spec

```python
import asyncio
from typing import Callable, Awaitable, TypeVar, Generic
T = TypeVar("T")

class AsyncWorkerPool(Generic[T]):
    def __init__(self, concurrency: int):
        """concurrency = max in-flight tasks at once."""

    async def submit(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        """Run coro_factory() under bounded concurrency. Return result.
        Multiple concurrent submits beyond `concurrency` block until slot free."""

    async def map(self, coro_factory: Callable[[int], Awaitable[T]],
                  items: list) -> list[T]:
        """Apply coro_factory(item) for each item, results in input order."""

    async def shutdown(self) -> None:
        """Wait for all in-flight tasks. Subsequent submits raise."""
```

## Requirements

- Use `asyncio.Semaphore` for concurrency limit
- Results from `map` MUST be in input order (not completion order)
- After shutdown: `submit` raises `RuntimeError`
- Handle exceptions in tasks: propagate to caller of `submit`
- Pure stdlib (asyncio)

## Acceptance criteria

All tests in `tests.py` must pass.
