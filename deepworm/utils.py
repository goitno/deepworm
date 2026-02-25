"""Utility functions for deepworm."""

from __future__ import annotations

import functools
import logging
import threading
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger("deepworm")

F = TypeVar("F", bound=Callable[..., Any])


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (approx 4 chars per token)."""
    return len(text) // 4


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """Estimate API cost in USD.

    Prices are approximate and may change.
    """
    prices = {
        "gpt-4o-mini": (0.15, 0.60),      # per 1M tokens: (input, output)
        "gpt-4o": (2.50, 10.00),
        "gpt-4-turbo": (10.00, 30.00),
        "claude-3-5-haiku-latest": (0.80, 4.00),
        "claude-3-5-sonnet-latest": (3.00, 15.00),
        "claude-sonnet-4-20250514": (3.00, 15.00),
        "gemini-2.0-flash": (0.10, 0.40),
    }

    input_price, output_price = prices.get(model, (1.00, 3.00))
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return round(cost, 6)


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Truncate text to a maximum number of characters at a word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."


class RateLimiter:
    """Thread-safe token bucket rate limiter.

    Limits the rate of operations (e.g., API calls, HTTP requests).
    """

    def __init__(self, max_calls: int, period: float = 1.0):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the period.
            period: Time period in seconds (default: 1 second).
        """
        self.max_calls = max_calls
        self.period = period
        self._lock = threading.Lock()
        self._calls: list[float] = []

    def acquire(self) -> None:
        """Wait until a call is allowed under the rate limit."""
        with self._lock:
            now = time.time()
            # Remove expired entries
            self._calls = [t for t in self._calls if now - t < self.period]

            if len(self._calls) >= self.max_calls:
                # Need to wait
                sleep_time = self._calls[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # Clean up again
                now = time.time()
                self._calls = [t for t in self._calls if now - t < self.period]

            self._calls.append(time.time())

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        pass


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        exceptions: Tuple of exception types to catch.
        on_retry: Optional callback ``(attempt, exception)`` called before each retry.

    Example::

        @retry(max_retries=3)
        def fetch_data(url):
            return httpx.get(url).text
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        if on_retry:
                            on_retry(attempt + 1, e)
                        else:
                            logger.debug(
                                "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                                func.__name__, attempt + 1, max_retries, delay, e,
                            )
                        time.sleep(delay)
            raise last_error  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Convert a string to a safe filename.

    Replaces special characters and limits length.
    """
    import re

    safe = re.sub(r'[^\w\s.-]', '', name)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:max_length] or "untitled"


def chunk_text(text: str, max_chars: int = 4000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries.

    Useful for processing long documents within token limits.

    Args:
        text: The text to split.
        max_chars: Maximum characters per chunk.
        overlap: Number of overlapping characters between chunks.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars

        if end < len(text):
            # Try to break at sentence boundary
            for sep in ('. ', '.\n', '\n\n', '\n', ' '):
                boundary = text.rfind(sep, start + max_chars // 2, end)
                if boundary != -1:
                    end = boundary + len(sep)
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks

