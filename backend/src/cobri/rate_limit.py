"""Replaceable in-process rate limiting for authenticated actions."""

import asyncio
from collections import defaultdict, deque
from time import monotonic
from typing import Protocol

from cobri.errors import RateLimitExceeded
from cobri.identity.auth import Principal


class RateLimiter(Protocol):
    async def check(self, principal: Principal, action: str) -> None: ...


class InMemoryRateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.limit = requests_per_minute
        self._requests: dict[tuple[str, str, str], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, principal: Principal, action: str) -> None:
        now = monotonic()
        key = (principal.issuer, principal.subject, action)
        async with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= now - 60:
                requests.popleft()
            if len(requests) >= self.limit:
                raise RateLimitExceeded
            requests.append(now)
