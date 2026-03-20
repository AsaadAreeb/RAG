"""Per-user and per-provider rate limiting with exponential backoff."""
from __future__ import annotations
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float          # tokens per second
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()

    def consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now
        if self._tokens >= amount:
            self._tokens -= amount
            return True
        return False


class RateLimiter:
    """Sliding-window per-user limiter + per-provider token buckets."""

    def __init__(self, user_rpm: int = 10, provider_rpm: int = 20) -> None:
        self.user_rpm = user_rpm
        self._user_windows: dict[str, deque[float]] = defaultdict(deque)
        self._provider_buckets: dict[str, TokenBucket] = {
            "grok": TokenBucket(capacity=provider_rpm, refill_rate=provider_rpm / 60),
            "gemini": TokenBucket(capacity=provider_rpm, refill_rate=provider_rpm / 60),
        }

    def check_user(self, user_id: str) -> bool:
        now = time.monotonic()
        window = self._user_windows[user_id]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.user_rpm:
            return False
        window.append(now)
        return True

    def check_provider(self, provider: str) -> bool:
        bucket = self._provider_buckets.get(provider)
        return bucket.consume() if bucket else True

    async def wait_for_provider(self, provider: str, max_wait: float = 30.0) -> bool:
        bucket = self._provider_buckets.get(provider)
        if not bucket:
            return True
        deadline = time.monotonic() + max_wait
        backoff = 1.0
        while time.monotonic() < deadline:
            if bucket.consume():
                return True
            await asyncio.sleep(min(backoff, deadline - time.monotonic()))
            backoff = min(backoff * 2, 8.0)
        return False
