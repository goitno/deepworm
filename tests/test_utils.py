"""Tests for deepworm.utils."""

import time

from deepworm.utils import RateLimiter, estimate_cost, estimate_tokens, truncate_text


def test_estimate_tokens():
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("a" * 4000) == 1000


def test_estimate_cost_gpt4o_mini():
    cost = estimate_cost(1_000_000, 500_000, model="gpt-4o-mini")
    # input: 0.15/M, output: 0.60/M  → 0.15 + 0.30 = 0.45
    assert abs(cost - 0.45) < 0.001


def test_estimate_cost_unknown_model():
    cost = estimate_cost(1_000_000, 1_000_000, model="unknown-model")
    assert cost > 0  # uses fallback pricing


def test_truncate_text_short():
    text = "hello world"
    assert truncate_text(text, 100) == "hello world"


def test_truncate_text_long():
    text = "hello " * 1000
    result = truncate_text(text, 100)
    assert len(result) <= 104  # max_chars + "..."
    assert result.endswith("...")


def test_rate_limiter_allows_within_limit():
    """Should not block when under the limit."""
    limiter = RateLimiter(max_calls=5, period=1.0)
    start = time.time()
    for _ in range(5):
        limiter.acquire()
    elapsed = time.time() - start
    assert elapsed < 0.5  # Should be near-instant


def test_rate_limiter_throttles():
    """Should slow down when over the limit."""
    limiter = RateLimiter(max_calls=2, period=0.5)
    limiter.acquire()  # call 1
    limiter.acquire()  # call 2
    start = time.time()
    limiter.acquire()  # call 3 - should wait
    elapsed = time.time() - start
    assert elapsed >= 0.1  # Should have waited


def test_rate_limiter_context_manager():
    """Should work as context manager."""
    limiter = RateLimiter(max_calls=10, period=1.0)
    with limiter:
        pass  # Should not raise
