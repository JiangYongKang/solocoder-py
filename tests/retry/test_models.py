from __future__ import annotations

import random

import pytest

from solocoder_py.retry import InvalidRetryStrategyError, RetryStrategy


class TestRetryStrategyDefaults:
    def test_default_values(self):
        strategy = RetryStrategy()
        assert strategy.initial_delay == 1.0
        assert strategy.backoff_multiplier == 2.0
        assert strategy.max_delay == 60.0
        assert strategy.max_attempts == 3
        assert strategy.enable_jitter is False
        assert strategy.jitter_ratio == 0.2


class TestRetryStrategyValidation:
    def test_initial_delay_must_be_positive(self):
        with pytest.raises(InvalidRetryStrategyError, match="initial_delay must be positive"):
            RetryStrategy(initial_delay=0)
        with pytest.raises(InvalidRetryStrategyError, match="initial_delay must be positive"):
            RetryStrategy(initial_delay=-1.0)

    def test_backoff_multiplier_must_be_at_least_one(self):
        with pytest.raises(
            InvalidRetryStrategyError,
            match="backoff_multiplier must be greater than or equal to 1.0",
        ):
            RetryStrategy(backoff_multiplier=0.5)
        with pytest.raises(
            InvalidRetryStrategyError,
            match="backoff_multiplier must be greater than or equal to 1.0",
        ):
            RetryStrategy(backoff_multiplier=0.99)
        strategy = RetryStrategy(backoff_multiplier=1.0)
        assert strategy.backoff_multiplier == 1.0

    def test_max_delay_must_be_positive(self):
        with pytest.raises(InvalidRetryStrategyError, match="max_delay must be positive"):
            RetryStrategy(max_delay=0)
        with pytest.raises(InvalidRetryStrategyError, match="max_delay must be positive"):
            RetryStrategy(max_delay=-5.0)

    def test_max_delay_must_be_gte_initial_delay(self):
        with pytest.raises(
            InvalidRetryStrategyError,
            match="max_delay must be greater than or equal to initial_delay",
        ):
            RetryStrategy(initial_delay=10.0, max_delay=5.0)
        strategy = RetryStrategy(initial_delay=5.0, max_delay=5.0)
        assert strategy.max_delay == 5.0

    def test_max_attempts_must_be_at_least_one(self):
        with pytest.raises(InvalidRetryStrategyError, match="max_attempts must be at least 1"):
            RetryStrategy(max_attempts=0)
        with pytest.raises(InvalidRetryStrategyError, match="max_attempts must be at least 1"):
            RetryStrategy(max_attempts=-1)
        strategy = RetryStrategy(max_attempts=1)
        assert strategy.max_attempts == 1

    def test_jitter_ratio_must_be_between_zero_and_one(self):
        with pytest.raises(
            InvalidRetryStrategyError,
            match="jitter_ratio must be between 0 and 1",
        ):
            RetryStrategy(jitter_ratio=-0.1)
        with pytest.raises(
            InvalidRetryStrategyError,
            match="jitter_ratio must be between 0 and 1",
        ):
            RetryStrategy(jitter_ratio=1.1)
        strategy = RetryStrategy(jitter_ratio=0.0)
        assert strategy.jitter_ratio == 0.0
        strategy = RetryStrategy(jitter_ratio=1.0)
        assert strategy.jitter_ratio == 1.0


class TestDelayCalculation:
    def test_attempt_number_zero_or_negative_raises(self):
        strategy = RetryStrategy()
        with pytest.raises(ValueError, match="attempt_number must be >= 1"):
            strategy.calculate_delay(0)
        with pytest.raises(ValueError, match="attempt_number must be >= 1"):
            strategy.calculate_delay(-1)

    def test_first_attempt_has_zero_delay(self):
        strategy = RetryStrategy(initial_delay=5.0, backoff_multiplier=2.0)
        assert strategy.calculate_delay(1) == 0.0

    def test_exponential_backoff_no_jitter(self):
        strategy = RetryStrategy(initial_delay=1.0, backoff_multiplier=2.0, max_delay=60.0)
        assert strategy.calculate_delay(2) == 1.0
        assert strategy.calculate_delay(3) == 2.0
        assert strategy.calculate_delay(4) == 4.0
        assert strategy.calculate_delay(5) == 8.0

    def test_max_delay_capping(self):
        strategy = RetryStrategy(initial_delay=1.0, backoff_multiplier=2.0, max_delay=5.0)
        assert strategy.calculate_delay(2) == 1.0
        assert strategy.calculate_delay(3) == 2.0
        assert strategy.calculate_delay(4) == 4.0
        assert strategy.calculate_delay(5) == 5.0
        assert strategy.calculate_delay(6) == 5.0
        assert strategy.calculate_delay(10) == 5.0

    def test_multiplier_of_one_keeps_delay_constant(self):
        strategy = RetryStrategy(
            initial_delay=3.0, backoff_multiplier=1.0, max_delay=10.0
        )
        assert strategy.calculate_delay(2) == 3.0
        assert strategy.calculate_delay(3) == 3.0
        assert strategy.calculate_delay(10) == 3.0


class TestJitter:
    def test_jitter_disabled_no_variation(self):
        strategy = RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            enable_jitter=False,
        )
        for _ in range(20):
            assert strategy.calculate_delay(3) == 2.0

    def test_jitter_range_is_within_bounds(self):
        strategy = RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            enable_jitter=True,
            jitter_ratio=0.2,
        )
        rng = random.Random(42)
        delays = [strategy.calculate_delay(3, rng=rng) for _ in range(100)]
        base_delay = 2.0
        jitter_range = base_delay * 0.2
        lower_bound = base_delay - jitter_range
        upper_bound = base_delay + jitter_range
        for d in delays:
            assert lower_bound <= d <= upper_bound

    def test_jitter_with_deterministic_rng(self):
        strategy = RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            enable_jitter=True,
            jitter_ratio=0.5,
        )
        rng1 = random.Random(123)
        rng2 = random.Random(123)
        for _ in range(10):
            assert strategy.calculate_delay(4, rng=rng1) == strategy.calculate_delay(4, rng=rng2)

    def test_jitter_with_max_delay_capping(self):
        strategy = RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=5.0,
            enable_jitter=True,
            jitter_ratio=0.2,
        )
        rng = random.Random(99)
        delays = [strategy.calculate_delay(10, rng=rng) for _ in range(100)]
        base = 5.0
        jitter_range = base * 0.2
        for d in delays:
            assert (base - jitter_range) <= d <= (base + jitter_range)


class TestShouldAttempt:
    def test_should_attempt(self):
        strategy = RetryStrategy(max_attempts=3)
        assert strategy.should_attempt(1)
        assert strategy.should_attempt(2)
        assert strategy.should_attempt(3)
        assert not strategy.should_attempt(4)
        assert not strategy.should_attempt(5)

    def test_max_attempts_one(self):
        strategy = RetryStrategy(max_attempts=1)
        assert strategy.should_attempt(1)
        assert not strategy.should_attempt(2)
