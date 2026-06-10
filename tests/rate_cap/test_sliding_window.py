from __future__ import annotations

import threading

import pytest

from solocoder_py.rate_cap import ManualClock, SlidingWindowCounter


class TestSlidingWindowBasic:
    def test_constructor_validates_window_seconds(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            SlidingWindowCounter(
                window_seconds=0, max_operations=10, clock=clock
            )

    def test_constructor_validates_max_operations(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="max_operations must be positive"):
            SlidingWindowCounter(
                window_seconds=60, max_operations=0, clock=clock
            )

    def test_constructor_validates_granularity_non_negative(self):
        clock = ManualClock()
        with pytest.raises(
            ValueError, match="slide_granularity_seconds cannot be negative"
        ):
            SlidingWindowCounter(
                window_seconds=60,
                max_operations=10,
                slide_granularity_seconds=-1,
                clock=clock,
            )

    def test_constructor_validates_granularity_not_exceed_window(self):
        clock = ManualClock()
        with pytest.raises(
            ValueError,
            match="slide_granularity_seconds cannot exceed window_seconds",
        ):
            SlidingWindowCounter(
                window_seconds=60,
                max_operations=10,
                slide_granularity_seconds=61,
                clock=clock,
            )

    def test_properties(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60,
            max_operations=10,
            slide_granularity_seconds=5,
            clock=clock,
        )
        assert counter.window_seconds == 60
        assert counter.max_operations == 10
        assert counter.slide_granularity_seconds == 5

    def test_allows_within_limit(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=3, clock=clock
        )
        for _ in range(3):
            ok, used, limit = counter.try_acquire()
            assert ok is True
            assert used <= limit
        ok, used, limit = counter.try_acquire()
        assert ok is False
        assert used == 3
        assert limit == 3

    def test_amount_parameter(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=10, clock=clock
        )
        ok, used, limit = counter.try_acquire(5)
        assert ok is True
        assert used == 5
        ok, used, limit = counter.try_acquire(6)
        assert ok is False
        assert used == 5
        ok, used, limit = counter.try_acquire(5)
        assert ok is True
        assert used == 10

    def test_invalid_amount_raises(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=10, clock=clock
        )
        with pytest.raises(ValueError, match="amount must be positive"):
            counter.try_acquire(0)
        with pytest.raises(ValueError, match="amount must be positive"):
            counter.try_acquire(-1)
        with pytest.raises(ValueError, match="amount must be positive"):
            counter.can_acquire(0)

    def test_current_count_and_remaining(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=5, clock=clock
        )
        assert counter.current_count() == 0
        assert counter.remaining() == 5
        counter.try_acquire(2)
        assert counter.current_count() == 2
        assert counter.remaining() == 3
        counter.try_acquire(3)
        assert counter.current_count() == 5
        assert counter.remaining() == 0

    def test_can_acquire_non_consuming(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=2, clock=clock
        )
        assert counter.can_acquire() is True
        assert counter.can_acquire() is True
        assert counter.current_count() == 0
        counter.try_acquire()
        assert counter.can_acquire() is True
        assert counter.current_count() == 1
        counter.try_acquire()
        assert counter.can_acquire() is False
        assert counter.current_count() == 2


class TestSlidingWindowPrecise:
    def test_requests_expire_after_window(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=2, clock=clock
        )
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is False

        clock.advance(59)
        assert counter.try_acquire()[0] is False

        clock.advance(2)
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is True

        clock.advance(60)
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is True

    def test_partial_window_slide(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=3, clock=clock
        )
        counter.try_acquire()
        clock.advance(20)
        counter.try_acquire()
        clock.advance(20)
        counter.try_acquire()

        assert counter.current_count() == 3
        assert counter.try_acquire()[0] is False

        clock.advance(21)
        assert counter.current_count() == 2
        assert counter.try_acquire()[0] is True

        clock.advance(20)
        assert counter.current_count() == 2
        assert counter.try_acquire()[0] is True

        clock.advance(21)
        assert counter.current_count() == 2
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is False

    def test_exact_window_boundary(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=10, max_operations=1, clock=clock
        )
        assert counter.try_acquire()[0] is True
        clock.advance(10.0)
        assert counter.try_acquire()[0] is True

    def test_just_inside_window(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=10, max_operations=1, clock=clock
        )
        assert counter.try_acquire()[0] is True
        clock.advance(9)
        assert counter.try_acquire()[0] is False

    def test_clock_backward_clears_state(self):
        clock = ManualClock(start_time=100.0)
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=3, clock=clock
        )
        counter.try_acquire()
        counter.try_acquire()
        assert counter.current_count() == 2
        clock.set(50.0)
        assert counter.current_count() == 0
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is False


class TestSlidingWindowGranular:
    def test_granular_basic(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60,
            max_operations=3,
            slide_granularity_seconds=1,
            clock=clock,
        )
        for _ in range(3):
            assert counter.try_acquire()[0] is True
        assert counter.try_acquire()[0] is False

    def test_granular_expire(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60,
            max_operations=2,
            slide_granularity_seconds=1,
            clock=clock,
        )
        counter.try_acquire()
        clock.advance(30)
        counter.try_acquire()
        assert counter.current_count() == 2

        clock.advance(30)
        assert counter.current_count() == 1

        clock.advance(31)
        assert counter.current_count() == 0

    def test_granular_large_granularity(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60,
            max_operations=10,
            slide_granularity_seconds=10,
            clock=clock,
        )
        for _ in range(5):
            counter.try_acquire()
        clock.advance(10)
        for _ in range(5):
            counter.try_acquire()
        assert counter.current_count() == 10

        clock.advance(50)
        assert counter.current_count() == 5

        clock.advance(11)
        assert counter.current_count() == 0


class TestSlidingWindowRollback:
    def test_rollback_precise(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=5, clock=clock
        )
        counter.try_acquire(3)
        assert counter.current_count() == 3
        counter._rollback_last(2)
        assert counter.current_count() == 1
        counter._rollback_last(5)
        assert counter.current_count() == 0

    def test_rollback_granular(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=60,
            max_operations=10,
            slide_granularity_seconds=1,
            clock=clock,
        )
        counter.try_acquire(3)
        clock.advance(5)
        counter.try_acquire(4)
        assert counter.current_count() == 7
        counter._rollback_last(2)
        assert counter.current_count() == 5
        counter._rollback_last(10)
        assert counter.current_count() == 0


class TestSlidingWindowConcurrency:
    def test_concurrent_acquire_no_overcount(self):
        clock = ManualClock()
        counter = SlidingWindowCounter(
            window_seconds=60, max_operations=1000, clock=clock
        )
        successes = 0
        errors = []

        def worker(n):
            nonlocal successes
            for _ in range(n):
                if counter.try_acquire()[0]:
                    successes += 1

        threads = [threading.Thread(target=worker, args=(200,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert successes == 1000
        assert counter.current_count() == 1000

    def test_concurrent_mixed_ops(self):
        clock = ManualClock(start_time=0.0)
        counter = SlidingWindowCounter(
            window_seconds=10,
            max_operations=500,
            slide_granularity_seconds=1,
            clock=clock,
        )

        def worker_acquire(n):
            for _ in range(n):
                counter.try_acquire()

        def worker_count(n):
            for _ in range(n):
                counter.current_count()

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=worker_acquire, args=(100,)))
            threads.append(threading.Thread(target=worker_count, args=(100,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter.current_count() <= 500
