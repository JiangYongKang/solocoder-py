from __future__ import annotations

import threading

import pytest

from solocoder_py.token_bucket import (
    InvalidBucketConfigError,
    ManualClock,
    MultiSubjectTokenBucketLimiter,
    NotEnoughTokensError,
    TokenBucket,
)


class TestTokenBucketConstruction:
    def test_valid_construction(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        assert bucket.capacity == 10
        assert bucket.refill_rate_per_second == 2.0
        assert bucket.get_available_tokens() == 10.0

    def test_invalid_capacity_zero(self):
        clock = ManualClock()
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            TokenBucket(capacity=0, refill_rate_per_second=1.0, clock=clock)

    def test_invalid_capacity_negative(self):
        clock = ManualClock()
        with pytest.raises(InvalidBucketConfigError, match="capacity must be positive"):
            TokenBucket(capacity=-5, refill_rate_per_second=1.0, clock=clock)

    def test_refill_rate_zero_allowed(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=10, refill_rate_per_second=0.0, clock=clock)
        assert bucket.refill_rate_per_second == 0.0

    def test_invalid_refill_rate_negative(self):
        clock = ManualClock()
        with pytest.raises(InvalidBucketConfigError, match="refill_rate_per_second must be non-negative"):
            TokenBucket(capacity=10, refill_rate_per_second=-1.0, clock=clock)


class TestTokenBucketBasicConsumption:
    def test_try_acquire_single_token(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        assert bucket.try_acquire() is True
        assert bucket.get_available_tokens() == 4.0

    def test_try_acquire_multiple_tokens(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=10, refill_rate_per_second=1.0, clock=clock)
        assert bucket.try_acquire(3) is True
        assert bucket.get_available_tokens() == 7.0

    def test_try_acquire_zero_tokens_raises(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        with pytest.raises(InvalidBucketConfigError, match="tokens must be positive"):
            bucket.try_acquire(0)

    def test_try_acquire_negative_tokens_raises(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        with pytest.raises(InvalidBucketConfigError, match="tokens must be positive"):
            bucket.try_acquire(-1)

    def test_try_acquire_insufficient_tokens_returns_false(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        assert bucket.try_acquire(10) is False
        assert bucket.get_available_tokens() == 5.0

    def test_acquire_success(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        bucket.acquire(2)
        assert bucket.get_available_tokens() == 3.0

    def test_acquire_failure_raises(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        with pytest.raises(NotEnoughTokensError) as exc_info:
            bucket.acquire(10)
        assert exc_info.value.requested == 10
        assert exc_info.value.available == 5.0

    def test_can_acquire_non_consuming(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        assert bucket.can_acquire(3) is True
        assert bucket.can_acquire(3) is True
        assert bucket.get_available_tokens() == 5.0

    def test_can_acquire_insufficient(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        assert bucket.can_acquire(10) is False

    def test_can_acquire_zero_raises(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        with pytest.raises(InvalidBucketConfigError, match="tokens must be positive"):
            bucket.can_acquire(0)


class TestTokenBucketRefill:
    def test_refill_after_one_second(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        bucket.try_acquire(5)
        assert bucket.get_available_tokens() == 5.0
        clock.advance(1.0)
        assert bucket.get_available_tokens() == 7.0

    def test_refill_partial_second(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        bucket.try_acquire(5)
        clock.advance(0.5)
        assert bucket.get_available_tokens() == 6.0

    def test_refill_does_not_exceed_capacity(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        bucket.try_acquire(3)
        clock.advance(100.0)
        assert bucket.get_available_tokens() == 10.0

    def test_refill_no_time_passed(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        bucket.try_acquire(3)
        clock.advance(0.0)
        assert bucket.get_available_tokens() == 7.0

    def test_refill_then_consume(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)
        bucket.try_acquire(10)
        assert bucket.get_available_tokens() == 0.0
        assert bucket.try_acquire() is False
        clock.advance(1.0)
        assert bucket.try_acquire() is True
        assert bucket.get_available_tokens() == 1.0
        clock.advance(2.0)
        assert bucket.try_acquire(3) is True
        assert bucket.get_available_tokens() == 2.0

    def test_continual_refill(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=100, refill_rate_per_second=10.0, clock=clock)
        bucket.try_acquire(100)
        for i in range(10):
            clock.advance(0.5)
            assert abs(bucket.get_available_tokens() - (i + 1) * 5.0) < 1e-9


class TestTokenBucketBurst:
    def test_burst_full_capacity(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=10, refill_rate_per_second=1.0, clock=clock)
        assert bucket.try_acquire(10) is True
        assert bucket.get_available_tokens() == 0.0

    def test_burst_exceeds_capacity_rejected(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=10, refill_rate_per_second=1.0, clock=clock)
        assert bucket.try_acquire(11) is False
        assert bucket.get_available_tokens() == 10.0

    def test_burst_exactly_zero_after(self):
        clock = ManualClock()
        bucket = TokenBucket(capacity=5, refill_rate_per_second=1.0, clock=clock)
        for _ in range(5):
            assert bucket.try_acquire() is True
        assert bucket.get_available_tokens() == 0.0
        assert bucket.try_acquire() is False
        clock.advance(1.0)
        assert bucket.try_acquire() is True


class TestTokenBucketConcurrency:
    def test_concurrent_acquire_no_negative(self):
        clock = ManualClock(start_time=0.0)
        bucket = TokenBucket(capacity=100, refill_rate_per_second=0.0, clock=clock)
        results = []
        lock = threading.Lock()

        def worker():
            while True:
                success = bucket.try_acquire()
                with lock:
                    results.append(success)
                if not success:
                    break

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert bucket.get_available_tokens() >= 0.0
        success_count = sum(1 for r in results if r)
        assert success_count == 100

    def test_concurrent_multi_token_acquire(self):
        bucket = TokenBucket(capacity=100, refill_rate_per_second=0.0)
        total_acquired = 0
        lock = threading.Lock()

        def worker():
            nonlocal total_acquired
            while True:
                if bucket.try_acquire(3):
                    with lock:
                        total_acquired += 3
                else:
                    break

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert bucket.get_available_tokens() >= 0.0
        assert total_acquired <= 100
        assert total_acquired >= 99

    def test_concurrent_refill_and_acquire(self):
        bucket = TokenBucket(capacity=100, refill_rate_per_second=1000.0)
        errors = []

        def acquire_worker():
            for _ in range(100):
                try:
                    bucket.try_acquire()
                    avail = bucket.get_available_tokens()
                    if avail < 0:
                        errors.append(f"Negative tokens: {avail}")
                except Exception as e:
                    errors.append(str(e))

        threads = [threading.Thread(target=acquire_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert bucket.get_available_tokens() >= 0.0
        assert errors == []


class TestMultiSubjectLimiterConstruction:
    def test_valid_construction(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=10, refill_rate_per_second=2.0, clock=clock
        )
        assert limiter.default_capacity == 10
        assert limiter.default_refill_rate_per_second == 2.0

    def test_invalid_capacity(self):
        clock = ManualClock()
        with pytest.raises(InvalidBucketConfigError):
            MultiSubjectTokenBucketLimiter(
                capacity=0, refill_rate_per_second=1.0, clock=clock
            )


class TestMultiSubjectLimiterIsolation:
    def test_subjects_isolated(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        for _ in range(5):
            assert limiter.try_acquire("user_a") is True
        assert limiter.try_acquire("user_a") is False
        assert limiter.try_acquire("user_b") is True
        assert limiter.try_acquire("user_b") is True
        assert limiter.get_available_tokens("user_a") == 0.0
        assert limiter.get_available_tokens("user_b") == 3.0

    def test_multi_token_consumption_isolated(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=10, refill_rate_per_second=1.0, clock=clock
        )
        assert limiter.try_acquire("user_a", 7) is True
        assert limiter.try_acquire("user_b", 8) is True
        assert limiter.get_available_tokens("user_a") == 3.0
        assert limiter.get_available_tokens("user_b") == 2.0

    def test_list_subjects(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        assert limiter.list_subjects() == []
        limiter.try_acquire("user_a")
        limiter.try_acquire("user_b")
        subjects = limiter.list_subjects()
        assert "user_a" in subjects
        assert "user_b" in subjects
        assert len(subjects) == 2

    def test_has_subject(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        assert limiter.has_subject("user_a") is False
        limiter.get_available_tokens("user_a")
        assert limiter.has_subject("user_a") is True


class TestMultiSubjectLimiterRefill:
    def test_refill_per_subject(self):
        clock = ManualClock(start_time=0.0)
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=10, refill_rate_per_second=2.0, clock=clock
        )
        limiter.try_acquire("user_a", 10)
        limiter.try_acquire("user_b", 5)
        assert limiter.get_available_tokens("user_a") == 0.0
        assert limiter.get_available_tokens("user_b") == 5.0
        clock.advance(2.0)
        assert limiter.get_available_tokens("user_a") == 4.0
        assert limiter.get_available_tokens("user_b") == 9.0


class TestMultiSubjectLimiterConcurrency:
    def test_concurrent_different_subjects(self):
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=100, refill_rate_per_second=0.0
        )
        results = {"user_a": 0, "user_b": 0}
        lock = threading.Lock()

        def worker(subject_id):
            while True:
                if limiter.try_acquire(subject_id):
                    with lock:
                        results[subject_id] += 1
                else:
                    break

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=worker, args=("user_a",)))
            threads.append(threading.Thread(target=worker, args=("user_b",)))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert results["user_a"] == 100
        assert results["user_b"] == 100
        assert limiter.get_available_tokens("user_a") >= 0.0
        assert limiter.get_available_tokens("user_b") >= 0.0

    def test_concurrent_same_subject_multi_token(self):
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=100, refill_rate_per_second=0.0
        )
        total = 0
        lock = threading.Lock()

        def worker():
            nonlocal total
            while True:
                if limiter.try_acquire("user", 2):
                    with lock:
                        total += 2
                else:
                    break

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert limiter.get_available_tokens("user") >= 0.0
        assert total <= 100
        assert total >= 98


class TestMultiSubjectLimiterAcquire:
    def test_acquire_success(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        limiter.acquire("user", 3)
        assert limiter.get_available_tokens("user") == 2.0

    def test_acquire_failure(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        with pytest.raises(NotEnoughTokensError):
            limiter.acquire("user", 10)

    def test_can_acquire(self):
        clock = ManualClock()
        limiter = MultiSubjectTokenBucketLimiter(
            capacity=5, refill_rate_per_second=1.0, clock=clock
        )
        assert limiter.can_acquire("user", 5) is True
        assert limiter.can_acquire("user", 6) is False
        assert limiter.get_available_tokens("user") == 5.0
