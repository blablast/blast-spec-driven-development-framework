import threading
import time


class RateLimiter:
    def __init__(self, rate: float, burst: int):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def try_acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            self._tokens = min(self._burst, self._tokens + (now - self._last) * self._rate)
            self._last = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False