"""Worker pool for processing background jobs."""
import queue
import threading
from typing import Callable


class WorkerPool:
    """Fixed-size thread pool with a job queue."""

    def __init__(self, num_workers: int = 4):
        self._queue: queue.Queue = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._results: list[tuple[str, object]] = []
        self._stop = False
        for _ in range(num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._workers.append(t)

    def submit(self, fn: Callable, *args, **kwargs) -> None:
        """Enqueue a job for execution."""
        self._queue.put((fn, args, kwargs))

    def _worker_loop(self) -> None:
        while not self._stop:
            try:
                fn, args, kwargs = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                result = fn(*args, **kwargs)
                self._results.append((fn.__name__, result))
            except Exception as e:
                self._results.append((fn.__name__, f"ERROR: {e}"))

    def get_results(self) -> list[tuple[str, object]]:
        """Return all results collected so far."""
        return self._results

    def shutdown(self) -> None:
        """Signal workers to stop and wait for them."""
        self._stop = True
        for w in self._workers:
            w.join()
