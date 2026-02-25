"""Tests for deepworm.utils."""

import time

import pytest

from deepworm.utils import (
    RateLimiter,
    chunk_text,
    estimate_cost,
    estimate_tokens,
    retry,
    sanitize_filename,
    truncate_text,
)


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


# ── retry decorator tests ──


def test_retry_succeeds_first_try():
    call_count = 0

    @retry(max_retries=3, base_delay=0.01)
    def succeed():
        nonlocal call_count
        call_count += 1
        return "ok"

    assert succeed() == "ok"
    assert call_count == 1


def test_retry_succeeds_after_failures():
    call_count = 0

    @retry(max_retries=3, base_delay=0.01)
    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "ok"

    assert flaky() == "ok"
    assert call_count == 3


def test_retry_exhausted():
    @retry(max_retries=2, base_delay=0.01)
    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        always_fail()


def test_retry_specific_exceptions():
    call_count = 0

    @retry(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
    def wrong_type():
        nonlocal call_count
        call_count += 1
        raise TypeError("not caught")

    with pytest.raises(TypeError):
        wrong_type()
    assert call_count == 1  # No retries for TypeError


def test_retry_on_retry_callback():
    attempts = []

    def track(attempt, exc):
        attempts.append(attempt)

    @retry(max_retries=2, base_delay=0.01, on_retry=track)
    def flaky():
        if len(attempts) < 2:
            raise ValueError("oops")
        return "ok"

    assert flaky() == "ok"
    assert attempts == [1, 2]


# ── sanitize_filename tests ──


def test_sanitize_filename_basic():
    assert sanitize_filename("Hello World!") == "Hello_World"


def test_sanitize_filename_special_chars():
    assert sanitize_filename("file/with:bad*chars?") == "filewithbadchars"


def test_sanitize_filename_max_length():
    long_name = "a" * 200
    assert len(sanitize_filename(long_name)) == 100


def test_sanitize_filename_empty():
    assert sanitize_filename("!!!") == "untitled"


# ── chunk_text tests ──


def test_chunk_text_short():
    assert chunk_text("short text", max_chars=100) == ["short text"]


def test_chunk_text_splits():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = chunk_text(text, max_chars=40, overlap=10)
    assert len(chunks) >= 2
    # All text should be covered
    combined = " ".join(chunks)
    assert "First" in combined
    assert "Fourth" in combined


def test_chunk_text_overlap():
    text = "A" * 100 + ". " + "B" * 100
    chunks = chunk_text(text, max_chars=110, overlap=20)
    assert len(chunks) >= 2

