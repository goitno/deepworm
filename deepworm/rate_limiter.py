"""Rate limiting for API calls and request throttling.

Provides token bucket, sliding window, and fixed window rate limiters
for controlling API call frequency and preventing rate limit errors.
"""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union


class LimiterStrategy(Enum):
    """Rate limiting strategy."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class LimitAction(Enum):
    """Action when rate limit is hit."""

    REJECT = "reject"
    WAIT = "wait"
    THROTTLE = "throttle"


@dataclass
class RateLimitInfo:
    """Information about current rate limit state."""

    allowed: bool
    remaining: int
    limit: int
    reset_at: float
    retry_after: float = 0.0
    strategy: LimiterStrategy = LimiterStrategy.TOKEN_BUCKET

    @property
    def utilization(self) -> float:
        if self.limit == 0:
            return 0.0
        return 1.0 - (self.remaining / self.limit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "reset_at": self.reset_at,
            "retry_after": round(self.retry_after, 3),
            "utilization": round(self.utilization, 3),
            "strategy": self.strategy.value,
        }

    def to_headers(self) -> Dict[str, str]:
        """Generate standard rate limit headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
            "Retry-After": str(int(self.retry_after)) if self.retry_after > 0 else "0",
        }


@dataclass
class RateLimitStats:
    """Statistics for a rate limiter."""

    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    total_wait_ms: float = 0.0

    @property
    def rejection_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.rejected_requests / self.total_requests

    @property
    def avg_wait_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_wait_ms / self.total_requests

    def reset(self) -> None:
        self.total_requests = 0
        self.allowed_requests = 0
        self.rejected_requests = 0
        self.total_wait_ms = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "allowed_requests": self.allowed_requests,
            "rejected_requests": self.rejected_requests,
            "rejection_rate": round(self.rejection_rate, 3),
            "avg_wait_ms": round(self.avg_wait_ms, 3),
        }


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------


class TokenBucket:
    """Token bucket rate limiter.

    Tokens are added at a fixed rate. Each request consumes one token.
    If no tokens available, request is rejected or waits.
    """

    def __init__(
        self,
        rate: float,
        capacity: int,
        *,
        action: LimitAction = LimitAction.REJECT,
    ) -> None:
        self._rate = rate  # tokens per second
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._action = action
        self._stats = RateLimitStats()
        self._lock = threading.Lock()

    @property
    def stats(self) -> RateLimitStats:
        return self._stats

    @property
    def strategy(self) -> LimiterStrategy:
        return LimiterStrategy.TOKEN_BUCKET

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity, self._tokens + elapsed * self._rate,
        )
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> RateLimitInfo:
        """Try to acquire tokens. Returns RateLimitInfo."""
        with self._lock:
            self._refill()
            self._stats.total_requests += 1

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats.allowed_requests += 1
                return RateLimitInfo(
                    allowed=True,
                    remaining=int(self._tokens),
                    limit=self._capacity,
                    reset_at=time.time() + (self._capacity - self._tokens) / self._rate,
                    strategy=self.strategy,
                )

            # Not enough tokens
            wait_time = (tokens - self._tokens) / self._rate

            if self._action == LimitAction.WAIT:
                # Release lock and wait
                self._stats.total_wait_ms += wait_time * 1000

        if self._action == LimitAction.WAIT:
            time.sleep(wait_time)
            return self.acquire(tokens)

        with self._lock:
            self._stats.rejected_requests += 1
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                limit=self._capacity,
                reset_at=time.time() + wait_time,
                retry_after=wait_time,
                strategy=self.strategy,
            )

    def check(self) -> RateLimitInfo:
        """Check rate limit without consuming a token."""
        with self._lock:
            self._refill()
            return RateLimitInfo(
                allowed=self._tokens >= 1,
                remaining=int(self._tokens),
                limit=self._capacity,
                reset_at=time.time() + (self._capacity - self._tokens) / max(self._rate, 0.001),
                strategy=self.strategy,
            )

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(self._capacity)
            self._last_refill = time.monotonic()
            self._stats.reset()


# ---------------------------------------------------------------------------
# Sliding Window
# ---------------------------------------------------------------------------


class SlidingWindow:
    """Sliding window rate limiter.

    Tracks timestamps of requests within a rolling window.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        *,
        action: LimitAction = LimitAction.REJECT,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._timestamps: deque = deque()
        self._action = action
        self._stats = RateLimitStats()
        self._lock = threading.Lock()

    @property
    def stats(self) -> RateLimitStats:
        return self._stats

    @property
    def strategy(self) -> LimiterStrategy:
        return LimiterStrategy.SLIDING_WINDOW

    def _cleanup(self) -> None:
        now = time.monotonic()
        cutoff = now - self._window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def acquire(self) -> RateLimitInfo:
        """Try to acquire a slot in the window."""
        with self._lock:
            self._cleanup()
            self._stats.total_requests += 1
            now = time.monotonic()

            if len(self._timestamps) < self._max_requests:
                self._timestamps.append(now)
                self._stats.allowed_requests += 1
                return RateLimitInfo(
                    allowed=True,
                    remaining=self._max_requests - len(self._timestamps),
                    limit=self._max_requests,
                    reset_at=time.time() + self._window,
                    strategy=self.strategy,
                )

            # Window full
            oldest = self._timestamps[0]
            wait_time = (oldest + self._window) - now

            if self._action == LimitAction.WAIT and wait_time > 0:
                self._stats.total_wait_ms += wait_time * 1000

        if self._action == LimitAction.WAIT and wait_time > 0:
            time.sleep(wait_time)
            return self.acquire()

        with self._lock:
            self._stats.rejected_requests += 1
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                limit=self._max_requests,
                reset_at=time.time() + max(wait_time, 0),
                retry_after=max(wait_time, 0),
                strategy=self.strategy,
            )

    def check(self) -> RateLimitInfo:
        with self._lock:
            self._cleanup()
            remaining = self._max_requests - len(self._timestamps)
            return RateLimitInfo(
                allowed=remaining > 0,
                remaining=remaining,
                limit=self._max_requests,
                reset_at=time.time() + self._window,
                strategy=self.strategy,
            )

    def reset(self) -> None:
        with self._lock:
            self._timestamps.clear()
            self._stats.reset()


# ---------------------------------------------------------------------------
# Fixed Window
# ---------------------------------------------------------------------------


class FixedWindow:
    """Fixed window rate limiter.

    Resets counts at fixed time intervals.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        *,
        action: LimitAction = LimitAction.REJECT,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._count = 0
        self._window_start = time.monotonic()
        self._action = action
        self._stats = RateLimitStats()
        self._lock = threading.Lock()

    @property
    def stats(self) -> RateLimitStats:
        return self._stats

    @property
    def strategy(self) -> LimiterStrategy:
        return LimiterStrategy.FIXED_WINDOW

    def _check_window(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= self._window:
            self._count = 0
            self._window_start = now

    def acquire(self) -> RateLimitInfo:
        with self._lock:
            self._check_window()
            self._stats.total_requests += 1

            if self._count < self._max_requests:
                self._count += 1
                self._stats.allowed_requests += 1
                return RateLimitInfo(
                    allowed=True,
                    remaining=self._max_requests - self._count,
                    limit=self._max_requests,
                    reset_at=time.time() + (self._window - (time.monotonic() - self._window_start)),
                    strategy=self.strategy,
                )

            wait_time = self._window - (time.monotonic() - self._window_start)

            if self._action == LimitAction.WAIT and wait_time > 0:
                self._stats.total_wait_ms += wait_time * 1000

        if self._action == LimitAction.WAIT and wait_time > 0:
            time.sleep(wait_time)
            return self.acquire()

        with self._lock:
            self._stats.rejected_requests += 1
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                limit=self._max_requests,
                reset_at=time.time() + max(wait_time, 0),
                retry_after=max(wait_time, 0),
                strategy=self.strategy,
            )

    def check(self) -> RateLimitInfo:
        with self._lock:
            self._check_window()
            remaining = self._max_requests - self._count
            return RateLimitInfo(
                allowed=remaining > 0,
                remaining=remaining,
                limit=self._max_requests,
                reset_at=time.time() + (self._window - (time.monotonic() - self._window_start)),
                strategy=self.strategy,
            )

    def reset(self) -> None:
        with self._lock:
            self._count = 0
            self._window_start = time.monotonic()
            self._stats.reset()


# ---------------------------------------------------------------------------
# Multi-key rate limiter
# ---------------------------------------------------------------------------


class KeyedRateLimiter:
    """Rate limiter that tracks limits per key (e.g. per API provider)."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        strategy: LimiterStrategy = LimiterStrategy.SLIDING_WINDOW,
        action: LimitAction = LimitAction.REJECT,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._strategy = strategy
        self._action = action
        self._limiters: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _get_limiter(self, key: str) -> Any:
        if key not in self._limiters:
            if self._strategy == LimiterStrategy.TOKEN_BUCKET:
                rate = self._max_requests / max(self._window, 0.001)
                self._limiters[key] = TokenBucket(
                    rate=rate, capacity=self._max_requests, action=self._action,
                )
            elif self._strategy == LimiterStrategy.FIXED_WINDOW:
                self._limiters[key] = FixedWindow(
                    max_requests=self._max_requests,
                    window_seconds=self._window,
                    action=self._action,
                )
            else:
                self._limiters[key] = SlidingWindow(
                    max_requests=self._max_requests,
                    window_seconds=self._window,
                    action=self._action,
                )
        return self._limiters[key]

    def acquire(self, key: str) -> RateLimitInfo:
        with self._lock:
            limiter = self._get_limiter(key)
        return limiter.acquire()

    def check(self, key: str) -> RateLimitInfo:
        with self._lock:
            limiter = self._get_limiter(key)
        return limiter.check()

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                if key in self._limiters:
                    self._limiters[key].reset()
            else:
                for limiter in self._limiters.values():
                    limiter.reset()
                self._limiters.clear()

    @property
    def keys(self) -> List[str]:
        return list(self._limiters.keys())


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

T = TypeVar("T")


def rate_limit(
    max_requests: int,
    window_seconds: float = 1.0,
    *,
    strategy: LimiterStrategy = LimiterStrategy.TOKEN_BUCKET,
    action: LimitAction = LimitAction.WAIT,
) -> Callable:
    """Decorator to rate-limit a function."""
    if strategy == LimiterStrategy.TOKEN_BUCKET:
        rate = max_requests / max(window_seconds, 0.001)
        limiter = TokenBucket(rate=rate, capacity=max_requests, action=action)
    elif strategy == LimiterStrategy.FIXED_WINDOW:
        limiter = FixedWindow(
            max_requests=max_requests,
            window_seconds=window_seconds,
            action=action,
        )
    else:
        limiter = SlidingWindow(
            max_requests=max_requests,
            window_seconds=window_seconds,
            action=action,
        )

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            info = limiter.acquire()
            if not info.allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {info.retry_after:.1f}s",
                    info=info,
                )
            return func(*args, **kwargs)

        wrapper._limiter = limiter  # type: ignore
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", info: Optional[RateLimitInfo] = None) -> None:
        super().__init__(message)
        self.info = info


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_token_bucket(
    rate: float,
    capacity: int,
    action: LimitAction = LimitAction.REJECT,
) -> TokenBucket:
    """Create a token bucket rate limiter."""
    return TokenBucket(rate=rate, capacity=capacity, action=action)


def create_sliding_window(
    max_requests: int,
    window_seconds: float,
    action: LimitAction = LimitAction.REJECT,
) -> SlidingWindow:
    """Create a sliding window rate limiter."""
    return SlidingWindow(
        max_requests=max_requests,
        window_seconds=window_seconds,
        action=action,
    )


def create_fixed_window(
    max_requests: int,
    window_seconds: float,
    action: LimitAction = LimitAction.REJECT,
) -> FixedWindow:
    """Create a fixed window rate limiter."""
    return FixedWindow(
        max_requests=max_requests,
        window_seconds=window_seconds,
        action=action,
    )


def create_keyed_limiter(
    max_requests: int,
    window_seconds: float,
    strategy: LimiterStrategy = LimiterStrategy.SLIDING_WINDOW,
    action: LimitAction = LimitAction.REJECT,
) -> KeyedRateLimiter:
    """Create a keyed rate limiter."""
    return KeyedRateLimiter(
        max_requests=max_requests,
        window_seconds=window_seconds,
        strategy=strategy,
        action=action,
    )
