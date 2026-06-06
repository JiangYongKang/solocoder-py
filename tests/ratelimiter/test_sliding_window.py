from __future__ import annotations

import pytest

from solocoder_py.ratelimiter import ManualClock, SlidingWindowRateLimiter


class TestSlidingWindowBasic:
    def test_constructor_validates_max_requests(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="max_requests must be positive"):
            SlidingWindowRateLimiter(max_requests=0, window_seconds=60.0, clock=clock)

    def test_constructor_validates_window_seconds(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            SlidingWindowRateLimiter(max_requests=10, window_seconds=0.0, clock=clock)

    def test_allows_requests_within_limit(self):
        clock = ManualClock()
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0, clock=clock)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_current_count_reflects_acquired(self):
        clock = ManualClock()
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60.0, clock=clock)
        assert limiter.current_count() == 0
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.current_count() == 2

    def test_can_acquire_is_non_consuming(self):
        clock = ManualClock()
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0, clock=clock)
        assert limiter.can_acquire() is True
        assert limiter.can_acquire() is True
        assert limiter.can_acquire() is True
        assert limiter.current_count() == 0

        limiter.try_acquire()
        assert limiter.can_acquire() is True
        assert limiter.current_count() == 1

        limiter.try_acquire()
        assert limiter.can_acquire() is False
        assert limiter.current_count() == 2


class TestSlidingWindowSlides:
    def test_requests_expire_after_window(self):
        clock = ManualClock(start_time=0.0)
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60.0, clock=clock)

        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

        clock.advance(59)
        assert limiter.try_acquire() is False

        clock.advance(2)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

        clock.advance(60)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

    def test_partial_window_slide(self):
        clock = ManualClock(start_time=0.0)
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0, clock=clock)

        limiter.try_acquire()
        clock.advance(20)
        limiter.try_acquire()
        clock.advance(20)
        limiter.try_acquire()

        assert limiter.current_count() == 3
        assert limiter.try_acquire() is False

        clock.advance(21)
        assert limiter.current_count() == 2
        assert limiter.try_acquire() is True

        clock.advance(20)
        assert limiter.current_count() == 2
        assert limiter.try_acquire() is True

        clock.advance(21)
        assert limiter.current_count() == 2
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False


class TestSlidingWindowBoundary:
    def test_exact_window_boundary_rejection(self):
        clock = ManualClock(start_time=0.0)
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10.0, clock=clock)

        assert limiter.try_acquire() is True
        clock.advance(10.0)
        assert limiter.try_acquire() is True

    def test_just_inside_window_rejection(self):
        clock = ManualClock(start_time=0.0)
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10.0, clock=clock)

        assert limiter.try_acquire() is True
        clock.advance(9)
        assert limiter.try_acquire() is False


class TestSlidingWindowClockBackward:
    def test_clock_backward_clears_state(self):
        clock = ManualClock(start_time=100.0)
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60.0, clock=clock)

        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.current_count() == 2

        clock.set(50.0)
        assert limiter.current_count() == 0
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False


class TestSlidingWindowEdge:
    def test_single_request_limit(self):
        clock = ManualClock()
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=1.0, clock=clock)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False
        clock.advance(1.0)
        assert limiter.try_acquire() is True

    def test_many_requests_fast(self):
        clock = ManualClock()
        limiter = SlidingWindowRateLimiter(max_requests=1000, window_seconds=1.0, clock=clock)
        for _ in range(1000):
            assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False
        assert limiter.current_count() == 1000
