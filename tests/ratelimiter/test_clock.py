from __future__ import annotations

import pytest

from solocoder_py.ratelimiter import ManualClock, SystemClock


class TestSystemClock:
    def test_system_clock_monotonic_increases(self):
        clock = SystemClock()
        t1 = clock.now()
        t2 = clock.now()
        assert t2 >= t1


class TestManualClock:
    def test_manual_clock_starts_at_zero(self):
        clock = ManualClock()
        assert clock.now() == 0.0

    def test_manual_clock_custom_start(self):
        clock = ManualClock(start_time=100.5)
        assert clock.now() == 100.5

    def test_manual_clock_advance(self):
        clock = ManualClock(start_time=10.0)
        clock.advance(5.0)
        assert clock.now() == 15.0
        clock.advance(0.5)
        assert clock.now() == 15.5

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0

    def test_manual_clock_cannot_advance_negative(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot advance by negative seconds"):
            clock.advance(-1.0)
