import collections
import time
import threading

class TTLCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 60.0):
        """LRU cache with TTL; evicts LRU on capacity, expires on TTL."""
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache = collections.OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str):
        """Return value if present and not expired, else None."""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            
            # Check if expired
            if time.monotonic() - timestamp > self._ttl_seconds:
                del self._cache[key]
                return None
            
            # Move to end (MRU)
            self._cache.move_to_end(key)
            return value

    def put(self, key: str, value):
        """Insert/update. Evict LRU when over capacity."""
        with self._lock:
            timestamp = time.monotonic()
            
            if key in self._cache:
                # Update existing
                self._cache[key] = (value, timestamp)
                self._cache.move_to_end(key)
            else:
                # Insert new
                self._cache[key] = (value, timestamp)
                
                # Check capacity
                if len(self._cache) > self._max_size:
                    # Remove LRU (first item)
                    self._cache.popitem(last=False)

    def invalidate_older_than(self, age_seconds: float) -> int:
        """Drop entries older than age. Return count removed."""
        with self._lock:
            current_time = time.monotonic()
            removed_count = 0
            
            # Create a list of keys to remove to avoid modifying dict during iteration
            keys_to_remove = []
            for key, (value, timestamp) in self._cache.items():
                if current_time - timestamp > age_seconds:
                    keys_to_remove.append(key)
            
            # Remove the keys
            for key in keys_to_remove:
                del self._cache[key]
                removed_count += 1
                
            return removed_count