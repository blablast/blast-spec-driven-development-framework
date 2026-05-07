import asyncio
from typing import Callable, Awaitable, TypeVar, Generic
T = TypeVar("T")

class AsyncWorkerPool(Generic[T]):
    def __init__(self, concurrency: int):
        """concurrency = max in-flight tasks at once."""
        self._semaphore = asyncio.Semaphore(concurrency)
        self._shutdown_event = asyncio.Event()
        self._tasks = set()

    async def submit(self, coro_factory: Callable[[], Awaitable[T]]) -> T:
        """Run coro_factory() under bounded concurrency. Return result.
        Multiple concurrent submits beyond `concurrency` block until slot free."""
        if self._shutdown_event.is_set():
            raise RuntimeError("Cannot submit to shutdown pool")
        
        async with self._semaphore:
            if self._shutdown_event.is_set():
                raise RuntimeError("Cannot submit to shutdown pool")
            
            task = asyncio.create_task(coro_factory())
            self._tasks.add(task)
            try:
                result = await task
                return result
            finally:
                self._tasks.discard(task)

    async def map(self, coro_factory: Callable[[int], Awaitable[T]],
                  items: list) -> list[T]:
        """Apply coro_factory(item) for each item, results in input order."""
        tasks = []
        for item in items:
            task = asyncio.create_task(coro_factory(item))
            tasks.append(task)
        
        # Wait for all tasks to complete and collect results in order
        results = []
        for task in tasks:
            try:
                result = await task
                results.append(result)
            except Exception:
                # Re-raise the exception to match expected behavior
                raise
        
        return results

    async def shutdown(self) -> None:
        """Wait for all in-flight tasks. Subsequent submits raise."""
        self._shutdown_event.set()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)