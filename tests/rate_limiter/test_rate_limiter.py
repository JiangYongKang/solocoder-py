from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.rate_limiter import (
    InvalidResponseHeaderError,
    RateLimiter,
    RateLimitHeaders,
    SyncStrategy,
    TokenBucketConfig,
)
from solocoder_py.ratelimiter import ManualClock, SystemClock


class TestRateLimiterBasicOperations:
    def test_properties(self, basic_rate_limiter, basic_config):
        assert basic_rate_limiter.capacity == basic_config.capacity
        assert basic_rate_limiter.refill_rate == basic_config.refill_rate
        assert basic_rate_limiter.sync_strategy == SyncStrategy.MIN
        assert basic_rate_limiter.last_headers is None

    def test_set_sync_strategy(self, basic_rate_limiter):
        basic_rate_limiter.sync_strategy = SyncStrategy.SERVER
        assert basic_rate_limiter.sync_strategy == SyncStrategy.SERVER

    def test_available_tokens(self, basic_rate_limiter, basic_config):
        assert basic_rate_limiter.available_tokens == basic_config.capacity

    def test_is_full(self, basic_rate_limiter):
        assert basic_rate_limiter.is_full() is True

    def test_is_empty(self, basic_rate_limiter):
        assert basic_rate_limiter.is_empty() is False

    def test_estimated_wait_time(self, basic_rate_limiter):
        assert basic_rate_limiter.estimated_wait_time(1) == 0.0

    def test_try_acquire_success(self, basic_rate_limiter):
        result = basic_rate_limiter.try_acquire()
        assert result.acquired is True
        assert basic_rate_limiter.available_tokens == 9

    def test_try_acquire_failure(self, basic_rate_limiter):
        for _ in range(10):
            basic_rate_limiter.try_acquire()
        result = basic_rate_limiter.try_acquire()
        assert result.acquired is False

    def test_reset(self, basic_rate_limiter):
        basic_rate_limiter.try_acquire(5)
        basic_rate_limiter.reset()
        assert basic_rate_limiter.available_tokens == 10
        assert basic_rate_limiter.last_headers is None


class TestRateLimiterHeaderSyncMinStrategy:
    def test_min_strategy_server_has_fewer(self, basic_rate_limiter, manual_clock):
        headers = {"X-RateLimit-Remaining": "3"}
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 3
        assert basic_rate_limiter.last_headers is not None
        assert basic_rate_limiter.last_headers.remaining == 3

    def test_min_strategy_local_has_fewer(self, basic_rate_limiter):
        basic_rate_limiter.try_acquire(7)
        assert basic_rate_limiter.available_tokens == 3

        headers = {"X-RateLimit-Remaining": "8"}
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 3

    def test_min_strategy_reset_in_future_no_change(self, basic_rate_limiter, manual_clock):
        headers = {
            "X-RateLimit-Remaining": "5",
            "X-RateLimit-Reset": str(manual_clock.now() + 100.0),
        }
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 5

    def test_min_strategy_reset_in_past_restores(self, basic_rate_limiter, manual_clock):
        basic_rate_limiter.try_acquire(8)
        assert basic_rate_limiter.available_tokens == 2

        headers = {
            "X-RateLimit-Remaining": "2",
            "X-RateLimit-Reset": str(manual_clock.now() - 1.0),
        }
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 10

    def test_min_strategy_server_remaining_negative(self, basic_rate_limiter):
        headers = {"X-RateLimit-Remaining": "-5"}
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 0

    def test_min_strategy_server_remaining_exceeds_capacity(self, basic_rate_limiter):
        headers = {"X-RateLimit-Remaining": "999"}
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 10


class TestRateLimiterHeaderSyncServerStrategy:
    def test_server_strategy_overrides_local(self, server_sync_limiter):
        server_sync_limiter.try_acquire(5)
        assert server_sync_limiter.available_tokens == 5

        headers = {"X-RateLimit-Remaining": "8"}
        server_sync_limiter.update_from_response_headers(headers)
        assert server_sync_limiter.available_tokens == 8

    def test_server_strategy_reset_in_past(self, server_sync_limiter, manual_clock):
        server_sync_limiter.try_acquire(10)
        assert server_sync_limiter.available_tokens == 0

        headers = {"X-RateLimit-Reset": str(manual_clock.now() - 1.0)}
        server_sync_limiter.update_from_response_headers(headers)
        assert server_sync_limiter.available_tokens == 10

    def test_server_strategy_reset_in_future(self, server_sync_limiter, manual_clock):
        server_sync_limiter.try_acquire(7)
        assert server_sync_limiter.available_tokens == 3

        headers = {"X-RateLimit-Reset": str(manual_clock.now() + 10.0)}
        server_sync_limiter.update_from_response_headers(headers)
        assert server_sync_limiter.available_tokens == 3


class TestRateLimiterHeaderSyncLocalStrategy:
    def test_local_strategy_ignores_remaining(self, local_sync_limiter):
        local_sync_limiter.try_acquire(5)
        assert local_sync_limiter.available_tokens == 5

        headers = {"X-RateLimit-Remaining": "2"}
        local_sync_limiter.update_from_response_headers(headers)
        assert local_sync_limiter.available_tokens == 5
        assert local_sync_limiter.last_headers is not None

    def test_local_strategy_ignores_reset(self, local_sync_limiter, manual_clock):
        local_sync_limiter.try_acquire(8)
        assert local_sync_limiter.available_tokens == 2

        headers = {"X-RateLimit-Reset": str(manual_clock.now() - 1.0)}
        local_sync_limiter.update_from_response_headers(headers)
        assert local_sync_limiter.available_tokens == 2


class TestRateLimiterHeaderParsingErrors:
    def test_invalid_remaining_header_raises(self, basic_rate_limiter):
        with pytest.raises(InvalidResponseHeaderError):
            basic_rate_limiter.update_from_response_headers(
                {"X-RateLimit-Remaining": "invalid"}
            )

    def test_invalid_reset_header_raises(self, basic_rate_limiter):
        with pytest.raises(InvalidResponseHeaderError):
            basic_rate_limiter.update_from_response_headers(
                {"X-RateLimit-Reset": "not_a_timestamp"}
            )


class TestRateLimiterHeaderObjectUpdate:
    def test_update_from_headers_object(self, basic_rate_limiter):
        headers_obj = RateLimitHeaders(remaining=5, limit=100)
        basic_rate_limiter.update_from_headers_object(headers_obj)
        assert basic_rate_limiter.available_tokens == 5
        assert basic_rate_limiter.last_headers is headers_obj

    def test_update_from_headers_object_server_strategy(self, server_sync_limiter):
        headers_obj = RateLimitHeaders(remaining=2, reset=-1.0)
        server_sync_limiter.update_from_headers_object(headers_obj)
        assert server_sync_limiter.available_tokens == 10


class TestRateLimiterEdgeCases:
    def test_reset_headers_cleared(self, basic_rate_limiter):
        basic_rate_limiter.update_from_response_headers({"X-RateLimit-Remaining": "3"})
        assert basic_rate_limiter.last_headers is not None
        basic_rate_limiter.reset()
        assert basic_rate_limiter.last_headers is None

    def test_burst_requests_exactly_capacity(self, manual_clock):
        config = TokenBucketConfig(refill_rate=5.0, capacity=15, initial_tokens=15)
        limiter = RateLimiter(config=config, clock=manual_clock)
        result = limiter.try_acquire(15)
        assert result.acquired is True
        assert limiter.available_tokens == 0
        assert limiter.is_empty() is True

    def test_empty_bucket_request_wait(self, manual_clock):
        config = TokenBucketConfig(refill_rate=10.0, capacity=10, initial_tokens=0)
        limiter = RateLimiter(config=config, clock=manual_clock)
        result = limiter.acquire(1)
        assert result.acquired is True
        assert manual_clock.now() == 0.1

    def test_local_tokens_exceed_server_sync(self, basic_rate_limiter):
        basic_rate_limiter.update_from_response_headers({"X-RateLimit-Remaining": "0"})
        assert basic_rate_limiter.available_tokens == 0
        result = basic_rate_limiter.try_acquire()
        assert result.acquired is False
        assert result.retry_after is not None

    def test_server_reset_before_now(self, basic_rate_limiter, manual_clock):
        basic_rate_limiter.try_acquire(10)
        assert basic_rate_limiter.available_tokens == 0

        headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(manual_clock.now() - 0.5),
        }
        basic_rate_limiter.update_from_response_headers(headers)
        assert basic_rate_limiter.available_tokens == 10


class TestRateLimiterConcurrency:
    def test_concurrent_acquire_and_update_headers(self):
        config = TokenBucketConfig(refill_rate=100.0, capacity=100, initial_tokens=100)
        limiter = RateLimiter(config=config, clock=SystemClock())
        errors = []

        def acquirer():
            try:
                for _ in range(50):
                    limiter.try_acquire()
            except Exception as e:
                errors.append(e)

        def updater():
            try:
                for i in range(50):
                    limiter.update_from_response_headers(
                        {"X-RateLimit-Remaining": str(50 + i % 30)}
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=acquirer),
            threading.Thread(target=updater),
            threading.Thread(target=acquirer),
            threading.Thread(target=updater),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_reset_and_acquire(self):
        config = TokenBucketConfig(refill_rate=100.0, capacity=50, initial_tokens=50)
        limiter = RateLimiter(config=config, clock=SystemClock())
        errors = []

        def worker_acquire():
            try:
                for _ in range(100):
                    limiter.try_acquire()
            except Exception as e:
                errors.append(e)

        def worker_reset():
            try:
                for _ in range(20):
                    limiter.reset()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_acquire) for _ in range(4)]
        threads += [threading.Thread(target=worker_reset) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
