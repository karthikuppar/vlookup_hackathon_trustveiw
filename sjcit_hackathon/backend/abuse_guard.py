"""Small in-memory sliding-window rate limiter for chat, uploads and registration.

Per process only: behind several workers or instances, enforce limits at the gateway as well."""
from __future__ import annotations
import threading
import time
from collections import defaultdict, deque

DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    "chat": (30, 60),       # 30 questions / minute / user
    "upload": (20, 60),     # 20 uploads / minute / user
    "register": (5, 600),   # 5 registrations / 10 minutes / address
    "login_ip": (30, 300),  # 30 failed logins / 5 minutes / address, across all accounts (password spraying)
}


class RateLimiter:
    def __init__(self, limits: dict[str, tuple[int, int]] | None = None):
        self.limits = dict(limits or DEFAULT_LIMITS)
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, q: deque, window: int, now: float) -> None:
        while q and q[0] <= now - window:
            q.popleft()

    def allow(self, bucket: str, subject: str) -> bool:
        """Count one event; False if the subject is over its limit for this bucket."""
        n, window = self.limits[bucket]
        now = time.monotonic()
        with self._lock:
            q = self._hits[(bucket, subject)]
            self._prune(q, window, now)
            if len(q) >= n:
                return False
            q.append(now)
            return True

    def over(self, bucket: str, subject: str) -> bool:
        """True if the subject is already at its limit (does not count an event)."""
        n, window = self.limits[bucket]
        now = time.monotonic()
        with self._lock:
            q = self._hits[(bucket, subject)]
            self._prune(q, window, now)
            return len(q) >= n

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
