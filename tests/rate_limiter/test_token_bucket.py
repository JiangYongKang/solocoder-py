from __future__ import annotations

import math
import threading
import time

import pytest

from solocoder_py.rate_limiter import (
    TokenBucket,
    TokenBucketConfig,
    TokenExhaustedError,
    WaitTimeoutError,
)
from solocoder_py.ratelimiter import ManualClock, SystemClock


class TestTokenBucketInitialization:
    def test_default_initial_tokens_equals_capacity(self, basic_bucket, basic_config):
        assert basic_bucket.capacity == basic_config.capacity
        assert basic_bucket.refill_rate == basic_config.refill_rate
        assert basic_bucket.available_tokens() == basic_config.capacity

    def test_custom_initial_tokens(self, manual_clock):
        config = TokenBucketConfig(refill_rate=2.0, capacity=10, initial_tokens=3)
        bucket = TokenBucket(config=config, clock=manual_clock)
        assert bucket.available_tokens() == 3

    def test_zero_initial_tokens(self, empty_bucket):
        assert empty_bucket.available_tokens() == 0
        assert empty_bucket.is_empty() is True

    def test_is_full_initially(self, basic_bucket):
        assert basic_bucket.is_full() is True

    def test_is_empty_true(self, empty_bucket):
        assert empty_bucket.is_empty() is True

    def test_is_empty_false(self, basic_bucket):
        assert basic_bucket.is_empty() is False


class TestTokenBucketRefill:
    def test_refill_after_time_passes(self, basic_bucket, manual_clock):
        for _ in range(10):
            basic_bucket.try_acquire()
        assert basic_bucket.available_tokens() == 0

        manual_clock.advance(1.0)
        assert basic_bucket.available_tokens() == 2

    def test_refill_partial_tokens(self, basic_bucket, manual_clock):
        for _ in range(10):
            basic_bucket.try_acquire()

        manual_clock.advance(0.5)
        assert basic_bucket.available_tokens() == 1

        manual_clock.advance(0.25)
        tokens = basic_bucket.tokens
        assert 1.0 < tokens < 2.0

    def test_refill_does_not_exceed_capacity(self, basic_bucket, manual_clock):
        manual_clock.advance(100.0)
        assert basic_bucket.available_tokens() == basic_bucket.capacity

    def test_refill_zero_time_passed(self, basic_bucket, manual_clock):
        initial = basic_bucket.available_tokens()
        manual_clock.advance(0.0)
        assert basic_bucket.available_tokens() == initial

    def test_refill_high_rate(self, manual_clock):
        config = TokenBucketConfig(refill_rate=100.0, capacity=50)
        bucket = TokenBucket(config=config, clock=manual_clock)
        for _ in range(50):
            bucket.try_acquire()
        assert bucket.available_tokens() == 0

        manual_clock.advance(0.5)
        assert bucket.available_tokens() == 50


class TestTokenBucketTryAcquire:
    def test_try_acquire_success(self, basic_bucket):
        initial = basic_bucket.available_tokens()
        result = basic_bucket.try_acquire()
        assert result.acquired is True
        assert result.tokens_consumed == 1
        assert result.tokens_remaining == initial - 1
        assert result.retry_after is None

    def test_try_acquire_multiple_tokens(self, basic_bucket):
        initial = basic_bucket.available_tokens()
        result = basic_bucket.try_acquire(5)
        assert result.acquired is True
        assert result.tokens_consumed == 5
        assert result.tokens_remaining == initial - 5

    def test_try_acquire_failure_empty_bucket(self, empty_bucket):
        result = empty_bucket.try_acquire()
        assert result.acquired is False
        assert result.tokens_consumed == 0
        assert result.tokens_remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_try_acquire_failure_insufficient_tokens(self, basic_bucket):
        result = basic_bucket.try_acquire(15)
        assert result.acquired is False
        assert result.tokens_consumed == 0
        assert result.retry_after is not None

    def test_try_acquire_retry_after_calculation(self, empty_bucket):
        result = empty_bucket.try_acquire()
        expected = 1.0 / 5.0
        assert abs(result.retry_after - expected) < 0.001

    def test_try_acquire_zero_tokens_raises(self, basic_bucket):
        with pytest.raises(ValueError, match="tokens must be positive"):
            basic_bucket.try_acquire(0)

    def test_try_acquire_negative_tokens_raises(self, basic_bucket):
        with pytest.raises(ValueError, match="tokens must be positive"):
            basic_bucket.try_acquire(-1)


class TestTokenBucketAcquire:
    def test_acquire_immediate_success(self, basic_bucket):
        result = basic_bucket.acquire()
        assert result.acquired is True
        assert result.tokens_consumed == 1

    def test_acquire_waits_for_tokens(self, empty_bucket, manual_clock):
        result = empty_bucket.acquire()
        assert result.acquired is True
        assert result.tokens_consumed == 1
        assert manual_clock.now() == 0.2

    def test_acquire_timeout_zero_raises(self, empty_bucket):
        with pytest.raises(TokenExhaustedError):
            empty_bucket.acquire(timeout=0)

    def test_acquire_timeout_exceeded_raises(self, empty_bucket):
        with pytest.raises(WaitTimeoutError):
            empty_bucket.acquire(timeout=0.1)

    def test_acquire_timeout_sufficient(self, empty_bucket, manual_clock):
        result = empty_bucket.acquire(timeout=1.0)
        assert result.acquired is True
        assert manual_clock.now() == 0.2

    def test_acquire_multiple_tokens_wait(self, empty_bucket, manual_clock):
        result = empty_bucket.acquire(3)
        assert result.acquired is True
        assert manual_clock.now() == 0.6


class TestTokenBucketEstimatedWaitTime:
    def test_wait_time_zero_when_available(self, basic_bucket):
        assert basic_bucket.estimated_wait_time(1) == 0.0

    def test_wait_time_calculation(self, empty_bucket):
        wait = empty_bucket.estimated_wait_time(1)
        assert abs(wait - 0.2) < 0.001

    def test_wait_time_multiple_tokens(self, empty_bucket):
        wait = empty_bucket.estimated_wait_time(5)
        assert abs(wait - 1.0) < 0.001

    def test_wait_time_zero_needed(self, basic_bucket):
        assert basic_bucket.estimated_wait_time(0) == 0.0

    def test_wait_time_negative_needed(self, basic_bucket):
        assert basic_bucket.estimated_wait_time(-5) == 0.0


class TestTokenBucketSetTokens:
    def test_set_tokens_valid(self, basic_bucket):
        basic_bucket.set_tokens(5)
        assert basic_bucket.available_tokens() == 5

    def test_set_tokens_zero(self, basic_bucket):
        basic_bucket.set_tokens(0)
        assert basic_bucket.available_tokens() == 0
        assert basic_bucket.is_empty() is True

    def test_set_tokens_capped_at_capacity(self, basic_bucket):
        basic_bucket.set_tokens(100)
        assert basic_bucket.available_tokens() == basic_bucket.capacity

    def test_set_tokens_negative_raises(self, basic_bucket):
        with pytest.raises(ValueError, match="token_count must be non-negative"):
            basic_bucket.set_tokens(-1)


class TestTokenBucketReset:
    def test_reset_restores_initial_tokens(self, basic_bucket, manual_clock):
        for _ in range(7):
            basic_bucket.try_acquire()
        assert basic_bucket.available_tokens() == 3

        basic_bucket.reset()
        assert basic_bucket.available_tokens() == basic_bucket.capacity
        assert basic_bucket.last_refill_time == manual_clock.now()

    def test_reset_empty_bucket(self, empty_bucket, manual_clock):
        manual_clock.advance(2.0)
        empty_bucket.reset()
        assert empty_bucket.available_tokens() == 0


class TestTokenBucketState:
    def test_get_state(self, basic_bucket, manual_clock, basic_config):
        state = basic_bucket.get_state()
        assert state.capacity == basic_config.capacity
        assert state.refill_rate == basic_config.refill_rate
        assert state.tokens == float(basic_config.capacity)
        assert state.last_refill_time == 0.0

    def test_get_state_after_consume(self, basic_bucket, manual_clock):
        basic_bucket.try_acquire(3)
        manual_clock.advance(1.0)
        state = basic_bucket.get_state()
        assert state.tokens == 9.0


class TestTokenBucketBurstCapacity:
    def test_burst_full_capacity(self, burst_bucket):
        for i in range(20):
            result = burst_bucket.try_acquire()
            assert result.acquired is True, f"Failed at iteration {i}"
        assert burst_bucket.available_tokens() == 0

    def test_burst_exactly_capacity(self, burst_bucket):
        result = burst_bucket.try_acquire(20)
        assert result.acquired is True
        assert result.tokens_remaining == 0
        assert burst_bucket.is_empty() is True

    def test_burst_exceeded_fails(self, burst_bucket):
        burst_bucket.try_acquire(20)
        result = burst_bucket.try_acquire()
        assert result.acquired is False

    def test_burst_replenishes_at_rate(self, burst_bucket, manual_clock):
        burst_bucket.try_acquire(20)
        assert burst_bucket.available_tokens() == 0

        manual_clock.advance(5.0)
        assert burst_bucket.available_tokens() == 5

        manual_clock.advance(100.0)
        assert burst_bucket.available_tokens() == 20


class TestTokenBucketBoundaryConditions:
    def test_bucket_empty_then_refill(self, empty_bucket, manual_clock):
        assert empty_bucket.available_tokens() == 0
        manual_clock.advance(2.0)
        assert empty_bucket.available_tokens() == 10

    def test_consume_all_then_one_more(self, basic_bucket):
        for _ in range(10):
            result = basic_bucket.try_acquire()
            assert result.acquired is True
        result = basic_bucket.try_acquire()
        assert result.acquired is False

    def test_full_bucket_no_growth(self, basic_bucket, manual_clock):
        assert basic_bucket.is_full() is True
        manual_clock.advance(10.0)
        assert basic_bucket.available_tokens() == basic_bucket.capacity
        assert basic_bucket.is_full() is True

    def test_available_tokens_floor(self, manual_clock):
        config = TokenBucketConfig(refill_rate=1.0, capacity=10, initial_tokens=0)
        bucket = TokenBucket(config=config, clock=manual_clock)
        manual_clock.advance(0.9)
        assert bucket.available_tokens() == 0
        manual_clock.advance(0.2)
        assert bucket.available_tokens() == 1


class TestTokenBucketConcurrency:
    def test_concurrent_acquire_thread_safety(self):
        config = TokenBucketConfig(refill_rate=1000.0, capacity=200, initial_tokens=200)
        bucket = TokenBucket(config=config, clock=SystemClock())

        acquired_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal acquired_count
            for _ in range(20):
                result = bucket.try_acquire()
                if result.acquired:
                    with lock:
                        acquired_count += 1

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert acquired_count <= 200

    def test_concurrent_set_and_acquire(self):
        config = TokenBucketConfig(refill_rate=100.0, capacity=100, initial_tokens=100)
        bucket = TokenBucket(config=config, clock=SystemClock())
        errors = []

        def setter():
            try:
                for _ in range(100):
                    bucket.set_tokens(50)
            except Exception as e:
                errors.append(e)

        def acquirer():
            try:
                for _ in range(100):
                    bucket.try_acquire()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=setter),
            threading.Thread(target=acquirer),
            threading.Thread(target=setter),
            threading.Thread(target=acquirer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
