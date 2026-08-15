"""
rate_limit.py — Tiny in-memory sliding-window rate limiter.

Dependency-free protection against brute-forcing the auth endpoints. For a
multi-process / multi-instance deployment, swap this for Redis-backed
``slowapi``; the interface is deliberately minimal.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a minute and try again.",
            )
        hits.append(now)


# 10 auth attempts per minute per IP.
auth_rate_limit = RateLimiter(max_calls=10, window_seconds=60)
