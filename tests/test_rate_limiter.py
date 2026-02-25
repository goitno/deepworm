"""Tests for deepworm.rate_limiter module."""

import time

import pytest

from deepworm.rate_limiter import (
    FixedWindow,
    KeyedRateLimiter,
    LimitAction,
    LimiterStrategy,
    RateLimitExceeded,
    RateLimitInfo,
    RateLimitStats,
    SlidingWindow,
    TokenBucket,
    create_fixed_window,
    create_keyed_limiter,
    create_sliding_window,
    create_token_bucket,
    rate_limit,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_strategy_values(self):
        assert LimiterStrategy.TOKEN_BUCKET.value == "token_bucket"
        assert LimiterStrategy.SLIDING_WINDOW.value == "sliding_window"
        assert LimiterStrategy.FIXED_WINDOW.value == "fixed_window"

    def test_action_values(self):
        assert LimitAction.REJECT.value == "reject"
        assert LimitAction.WAIT.value == "wait"
        assert LimitAction.THROTTLE.value == "throttle"


# ---------------------------------------------------------------------------
# RateLimitInfo
# ---------------------------------------------------------------------------


class TestRateLimitInfo:
    def test_creation(self):
        info = RateLimitInfo(
            allowed=True, remaining=5, limit=10, reset_at=time.time() + 60,
        )
        assert info.allowed
        assert info.remaining == 5
        assert info.limit == 10

    def test_utilization(self):
        info = RateLimitInfo(allowed=True, remaining=3, limit=10, reset_at=0)
        assert info.utilization == pytest.approx(0.7, abs=0.01)

    def test_utilization_zero_limit(self):
        info = RateLimitInfo(allowed=False, remaining=0, limit=0, reset_at=0)
        assert info.utilization == 0.0

    def test_to_dict(self):
        info = RateLimitInfo(
            allowed=True, remaining=5, limit=10, reset_at=0, retry_after=1.5,
        )
        d = info.to_dict()
        assert d["allowed"] is True
        assert d["remaining"] == 5
        assert d["retry_after"] == 1.5

    def test_to_headers(self):
        info = RateLimitInfo(
            allowed=True, remaining=5, limit=10, reset_at=1000, retry_after=0,
        )
        headers = info.to_headers()
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "5"


# ---------------------------------------------------------------------------
# RateLimitStats
# ---------------------------------------------------------------------------


class TestRateLimitStats:
    def test_defaults(self):
        stats = RateLimitStats()
        assert stats.total_requests == 0
        assert stats.rejection_rate == 0.0
        assert stats.avg_wait_ms == 0.0

    def test_rejection_rate(self):
        stats = RateLimitStats(
            total_requests=100, allowed_requests=80, rejected_requests=20,
        )
        assert stats.rejection_rate == pytest.approx(0.2, abs=0.01)

    def test_reset(self):
        stats = RateLimitStats(total_requests=10, allowed_requests=8, rejected_requests=2)
        stats.reset()
        assert stats.total_requests == 0

    def test_to_dict(self):
        stats = RateLimitStats(total_requests=10)
        d = stats.to_dict()
        assert "total_requests" in d
        assert "rejection_rate" in d


# ---------------------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_basic_acquire(self):
        bucket = TokenBucket(rate=10, capacity=10)
        info = bucket.acquire()
        assert info.allowed
        assert info.remaining == 9

    def test_capacity_limit(self):
        bucket = TokenBucket(rate=1, capacity=3)
        results = [bucket.acquire() for _ in range(5)]
        allowed = sum(1 for r in results if r.allowed)
        assert allowed == 3

    def test_refill(self):
        bucket = TokenBucket(rate=100, capacity=5)
        # Drain all tokens
        for _ in range(5):
            bucket.acquire()
        # Wait for refill
        time.sleep(0.06)
        info = bucket.acquire()
        assert info.allowed

    def test_check_doesnt_consume(self):
        bucket = TokenBucket(rate=10, capacity=5)
        info1 = bucket.check()
        info2 = bucket.check()
        assert info1.remaining == info2.remaining

    def test_reset(self):
        bucket = TokenBucket(rate=1, capacity=5)
        for _ in range(5):
            bucket.acquire()
        bucket.reset()
        info = bucket.check()
        assert info.remaining == 5

    def test_stats(self):
        bucket = TokenBucket(rate=1, capacity=2)
        bucket.acquire()
        bucket.acquire()
        bucket.acquire()  # Rejected
        assert bucket.stats.total_requests == 3
        assert bucket.stats.allowed_requests == 2
        assert bucket.stats.rejected_requests == 1

    def test_strategy(self):
        bucket = TokenBucket(rate=1, capacity=1)
        assert bucket.strategy == LimiterStrategy.TOKEN_BUCKET

    def test_rejected_has_retry_after(self):
        bucket = TokenBucket(rate=1, capacity=1)
        bucket.acquire()
        info = bucket.acquire()
        assert not info.allowed
        assert info.retry_after > 0


# ---------------------------------------------------------------------------
# SlidingWindow
# ---------------------------------------------------------------------------


class TestSlidingWindow:
    def test_basic(self):
        sw = SlidingWindow(max_requests=5, window_seconds=1.0)
        info = sw.acquire()
        assert info.allowed
        assert info.remaining == 4

    def test_limit(self):
        sw = SlidingWindow(max_requests=3, window_seconds=1.0)
        for _ in range(3):
            sw.acquire()
        info = sw.acquire()
        assert not info.allowed

    def test_window_reset(self):
        sw = SlidingWindow(max_requests=2, window_seconds=0.05)
        sw.acquire()
        sw.acquire()
        info = sw.acquire()
        assert not info.allowed
        time.sleep(0.06)
        info = sw.acquire()
        assert info.allowed

    def test_check(self):
        sw = SlidingWindow(max_requests=5, window_seconds=1.0)
        info = sw.check()
        assert info.allowed
        assert info.remaining == 5

    def test_reset(self):
        sw = SlidingWindow(max_requests=3, window_seconds=1.0)
        sw.acquire()
        sw.acquire()
        sw.reset()
        info = sw.check()
        assert info.remaining == 3

    def test_strategy(self):
        sw = SlidingWindow(max_requests=1, window_seconds=1.0)
        assert sw.strategy == LimiterStrategy.SLIDING_WINDOW


# ---------------------------------------------------------------------------
# FixedWindow
# ---------------------------------------------------------------------------


class TestFixedWindow:
    def test_basic(self):
        fw = FixedWindow(max_requests=5, window_seconds=1.0)
        info = fw.acquire()
        assert info.allowed
        assert info.remaining == 4

    def test_limit(self):
        fw = FixedWindow(max_requests=3, window_seconds=1.0)
        for _ in range(3):
            fw.acquire()
        info = fw.acquire()
        assert not info.allowed

    def test_window_reset(self):
        fw = FixedWindow(max_requests=2, window_seconds=0.05)
        fw.acquire()
        fw.acquire()
        time.sleep(0.06)
        info = fw.acquire()
        assert info.allowed

    def test_check(self):
        fw = FixedWindow(max_requests=5, window_seconds=1.0)
        info = fw.check()
        assert info.remaining == 5

    def test_reset(self):
        fw = FixedWindow(max_requests=3, window_seconds=1.0)
        fw.acquire()
        fw.reset()
        assert fw.check().remaining == 3

    def test_strategy(self):
        fw = FixedWindow(max_requests=1, window_seconds=1.0)
        assert fw.strategy == LimiterStrategy.FIXED_WINDOW


# ---------------------------------------------------------------------------
# KeyedRateLimiter
# ---------------------------------------------------------------------------


class TestKeyedRateLimiter:
    def test_separate_keys(self):
        krl = KeyedRateLimiter(max_requests=2, window_seconds=1.0)
        krl.acquire("a")
        krl.acquire("a")
        info_a = krl.acquire("a")
        assert not info_a.allowed

        info_b = krl.acquire("b")
        assert info_b.allowed

    def test_keys_tracked(self):
        krl = KeyedRateLimiter(max_requests=5, window_seconds=1.0)
        krl.acquire("x")
        krl.acquire("y")
        assert set(krl.keys) == {"x", "y"}

    def test_reset_single_key(self):
        krl = KeyedRateLimiter(max_requests=2, window_seconds=1.0)
        krl.acquire("x")
        krl.acquire("x")
        krl.reset("x")
        info = krl.check("x")
        assert info.remaining == 2

    def test_reset_all(self):
        krl = KeyedRateLimiter(max_requests=2, window_seconds=1.0)
        krl.acquire("x")
        krl.acquire("y")
        krl.reset()
        assert len(krl.keys) == 0

    def test_token_bucket_strategy(self):
        krl = KeyedRateLimiter(
            max_requests=5,
            window_seconds=1.0,
            strategy=LimiterStrategy.TOKEN_BUCKET,
        )
        info = krl.acquire("key")
        assert info.allowed

    def test_fixed_window_strategy(self):
        krl = KeyedRateLimiter(
            max_requests=5,
            window_seconds=1.0,
            strategy=LimiterStrategy.FIXED_WINDOW,
        )
        info = krl.acquire("key")
        assert info.allowed


# ---------------------------------------------------------------------------
# rate_limit decorator
# ---------------------------------------------------------------------------


class TestRateLimitDecorator:
    def test_allows_within_limit(self):
        @rate_limit(5, 1.0, action=LimitAction.REJECT)
        def my_func():
            return "ok"

        result = my_func()
        assert result == "ok"

    def test_rejects_over_limit(self):
        @rate_limit(2, 1.0, action=LimitAction.REJECT)
        def limited():
            return "ok"

        limited()
        limited()
        with pytest.raises(RateLimitExceeded):
            limited()

    def test_exception_has_info(self):
        @rate_limit(1, 1.0, action=LimitAction.REJECT)
        def once():
            return "ok"

        once()
        with pytest.raises(RateLimitExceeded) as exc_info:
            once()
        assert exc_info.value.info is not None
        assert not exc_info.value.info.allowed

    def test_preserves_name(self):
        @rate_limit(5, 1.0)
        def my_function():
            """My doc."""
            pass

        assert my_function.__name__ == "my_function"


# ---------------------------------------------------------------------------
# RateLimitExceeded
# ---------------------------------------------------------------------------


class TestRateLimitExceeded:
    def test_message(self):
        exc = RateLimitExceeded("custom message")
        assert str(exc) == "custom message"

    def test_default_message(self):
        exc = RateLimitExceeded()
        assert "Rate limit exceeded" in str(exc)

    def test_info(self):
        info = RateLimitInfo(allowed=False, remaining=0, limit=10, reset_at=0)
        exc = RateLimitExceeded(info=info)
        assert exc.info is not None
        assert exc.info.limit == 10


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactories:
    def test_create_token_bucket(self):
        tb = create_token_bucket(10, 100)
        assert isinstance(tb, TokenBucket)

    def test_create_sliding_window(self):
        sw = create_sliding_window(100, 60)
        assert isinstance(sw, SlidingWindow)

    def test_create_fixed_window(self):
        fw = create_fixed_window(100, 60)
        assert isinstance(fw, FixedWindow)

    def test_create_keyed_limiter(self):
        krl = create_keyed_limiter(100, 60)
        assert isinstance(krl, KeyedRateLimiter)
