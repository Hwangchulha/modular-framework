import time
from collections import deque, defaultdict
from typing import Dict, Deque

class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_sec: float):
        self.max = max_events
        self.win = window_sec
        self.store: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self.store[key]
        # drop old
        while q and (now - q[0]) > self.win:
            q.popleft()
        if len(q) >= self.max:
            return False
        q.append(now)
        return True

# global limiter for convenience
LOGIN_EMAIL_LIMITER = SlidingWindowLimiter(max_events=8, window_sec=300)  # 8 tries / 5 min
LOGIN_IP_LIMITER    = SlidingWindowLimiter(max_events=20, window_sec=300) # 20 tries / 5 min
