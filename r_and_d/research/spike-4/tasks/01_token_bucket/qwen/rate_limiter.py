import threading
import time

class RateLimiter:
    def __init__(self, rate: float, burst: int):
        """rate = tokens/sec; burst = bucket capacity (starts full)."""
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking attempt. Return True if acquired, False if not enough."""
        with self.lock:
            # Calculate elapsed time and refill tokens
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens += elapsed * self.rate
            self.last_refill = now
            
            # Ensure tokens don't exceed burst capacity
            if self.tokens > self.burst:
                self.tokens = self.burst
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False