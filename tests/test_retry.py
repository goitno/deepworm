"""Tests for deepworm.retry."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from deepworm.retry import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    RetryConfig,
    retry_with_strategy,
)


class TestRetryConfig:
    def test_exponential_delay(self):
        config = RetryConfig(base_delay=1.0, strategy=BackoffStrategy.EXPONENTIAL)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0

    def test_linear_delay(self):
        config = RetryConfig(base_delay=1.0, strategy=BackoffStrategy.LINEAR)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 3.0

    def test_constant_delay(self):
        config = RetryConfig(base_delay=2.0, strategy=BackoffStrategy.CONSTANT)
        assert config.calculate_delay(0) == 2.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(5) == 2.0

    def test_exponential_jitter_delay(self):
        config = RetryConfig(
            base_delay=1.0,
            strategy=BackoffStrategy.EXPONENTIAL_JITTER,
            jitter_factor=0.5,
        )
        # Jitter makes it non-deterministic, but should be within range
        delays = [config.calculate_delay(1) for _ in range(50)]
        assert all(0.5 <= d <= 3.5 for d in delays)  # 2.0 ± 1.0 (50%)

    def test_max_delay_cap(self):
        config = RetryConfig(
            base_delay=10.0, max_delay=15.0,
            strategy=BackoffStrategy.EXPONENTIAL,
        )
        assert config.calculate_delay(5) == 15.0  # capped

    def test_defaults(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.strategy == BackoffStrategy.EXPONENTIAL_JITTER


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert not cb.is_open

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        func = MagicMock(side_effect=RuntimeError("fail"))

        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(func)

        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            cb.call(func)

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        fail_func = MagicMock(side_effect=RuntimeError("fail"))
        ok_func = MagicMock(return_value="ok")

        # Two failures then a success
        with pytest.raises(RuntimeError):
            cb.call(fail_func)
        with pytest.raises(RuntimeError):
            cb.call(fail_func)
        assert cb.call(ok_func) == "ok"

        # Should still be closed
        assert cb.state == CircuitState.CLOSED

    def test_half_open_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown=0.01)
        fail_func = MagicMock(side_effect=RuntimeError("fail"))
        ok_func = MagicMock(return_value="recovered")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(fail_func)
        with pytest.raises(RuntimeError):
            cb.call(fail_func)
        assert cb.state == CircuitState.OPEN

        # Wait for cooldown
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # Test call succeeds → closes circuit
        assert cb.call(ok_func) == "recovered"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown=0.01)
        fail_func = MagicMock(side_effect=RuntimeError("fail"))

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(fail_func)

        # Wait for cooldown
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # Test call fails → re-open
        with pytest.raises(RuntimeError):
            cb.call(fail_func)
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        func = MagicMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError):
            cb.call(func)
        assert cb.is_open

        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_circuit_open_error_message(self):
        cb = CircuitBreaker(failure_threshold=1, cooldown=10.0)
        func = MagicMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError):
            cb.call(func)

        with pytest.raises(CircuitOpenError, match="Circuit breaker is open"):
            cb.call(func)


class TestRetryWithStrategy:
    def test_succeeds_first_try(self):
        config = RetryConfig(max_retries=3)
        call_count = 0

        @retry_with_strategy(config)
        def func():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert func() == "ok"
        assert call_count == 1

    def test_retries_and_succeeds(self):
        config = RetryConfig(
            max_retries=3, base_delay=0.01,
            strategy=BackoffStrategy.CONSTANT,
        )
        call_count = 0

        @retry_with_strategy(config)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        assert func() == "ok"
        assert call_count == 3

    def test_exhausts_retries(self):
        config = RetryConfig(
            max_retries=2, base_delay=0.01,
            strategy=BackoffStrategy.CONSTANT,
        )

        @retry_with_strategy(config)
        def func():
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            func()

    def test_non_retryable_exceptions(self):
        config = RetryConfig(
            max_retries=5, base_delay=0.01,
            non_retryable_exceptions=(KeyboardInterrupt, SystemExit),
        )
        call_count = 0

        @retry_with_strategy(config)
        def func():
            nonlocal call_count
            call_count += 1
            raise KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            func()
        assert call_count == 1  # No retries

    def test_on_retry_callback(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, strategy=BackoffStrategy.CONSTANT)
        retries = []

        def on_retry(attempt, exc, delay):
            retries.append((attempt, str(exc), delay))

        @retry_with_strategy(config, on_retry=on_retry)
        def func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            func()

        assert len(retries) == 2
        assert retries[0][0] == 1
        assert retries[1][0] == 2

    def test_timeout_budget(self):
        config = RetryConfig(
            max_retries=100, base_delay=0.01,
            timeout=0.05, strategy=BackoffStrategy.CONSTANT,
        )

        @retry_with_strategy(config)
        def func():
            raise ValueError("fail")

        with pytest.raises((ValueError, TimeoutError)):
            func()
