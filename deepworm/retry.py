"""Advanced retry strategies and circuit breaker patterns.

Provides configurable retry strategies beyond basic exponential backoff:
- Exponential backoff with jitter
- Linear backoff
- Constant delay
- Circuit breaker (prevent cascading failures)
- Retry budgets (time-based limits)
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class BackoffStrategy(Enum):
    """Available backoff strategies."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.5  # For exponential_jitter, adds random ±jitter_factor
    timeout: float = 0.0  # Total time budget (0 = unlimited)
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    non_retryable_exceptions: tuple[type[Exception], ...] = ()

    def calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given attempt number (0-indexed).

        Args:
            attempt: The current attempt number (0 = first retry).

        Returns:
            Delay in seconds.
        """
        if self.strategy == BackoffStrategy.CONSTANT:
            delay = self.base_delay
        elif self.strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        elif self.strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        elif self.strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base = self.base_delay * (2 ** attempt)
            jitter_range = base * self.jitter_factor
            delay = base + random.uniform(-jitter_range, jitter_range)
        else:
            delay = self.base_delay

        return max(0.0, min(delay, self.max_delay))


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if recovery happened


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    When too many failures occur, the circuit opens and prevents new
    calls for a cooldown period. After cooldown, one test call is allowed.
    If it succeeds, the circuit closes; if it fails, it opens again.

    Example::

        breaker = CircuitBreaker(failure_threshold=5, cooldown=30.0)

        try:
            result = breaker.call(api_request, url)
        except CircuitOpenError:
            # Circuit is open, use fallback
            result = fallback_response()
    """
    failure_threshold: int = 5
    cooldown: float = 30.0  # seconds
    success_threshold: int = 1  # successes needed to close from half-open
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.cooldown:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Function to call.
            *args, **kwargs: Arguments to pass.

        Returns:
            The function's return value.

        Raises:
            CircuitOpenError: If the circuit is open.
        """
        state = self.state

        if state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit breaker is open. {self._failure_count} failures. "
                f"Will retry after {self.cooldown}s cooldown."
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.debug("Circuit breaker closed after recovery")
        else:
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.debug("Circuit breaker re-opened from half-open")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.debug(
                "Circuit breaker opened after %d failures",
                self._failure_count,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open."""
    pass


def retry_with_strategy(
    config: RetryConfig,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[F], F]:
    """Decorator for retrying with a configurable strategy.

    Args:
        config: RetryConfig with strategy and limits.
        on_retry: Optional callback(attempt, exception, delay).

    Example::

        cfg = RetryConfig(max_retries=5, strategy=BackoffStrategy.EXPONENTIAL_JITTER)

        @retry_with_strategy(cfg)
        def api_call():
            return requests.get(url)
    """
    import functools

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            last_error: Exception | None = None

            for attempt in range(config.max_retries + 1):
                # Check time budget
                if config.timeout > 0:
                    elapsed = time.time() - start_time
                    if elapsed >= config.timeout:
                        raise TimeoutError(
                            f"Retry budget exhausted ({config.timeout}s) "
                            f"after {attempt} attempts"
                        )

                try:
                    return func(*args, **kwargs)
                except config.non_retryable_exceptions:
                    raise  # Don't retry these
                except config.retryable_exceptions as e:
                    last_error = e
                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)

                        # Don't exceed time budget with delay
                        if config.timeout > 0:
                            remaining = config.timeout - (time.time() - start_time)
                            if delay > remaining:
                                delay = max(0.0, remaining)

                        if on_retry:
                            on_retry(attempt + 1, e, delay)
                        else:
                            logger.debug(
                                "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                                func.__name__, attempt + 1, config.max_retries,
                                delay, e,
                            )
                        time.sleep(delay)

            raise last_error  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
