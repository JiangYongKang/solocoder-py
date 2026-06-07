from __future__ import annotations

import pytest

from solocoder_py.retry import ManualClock, SystemClock


class TestSystemClock:
    def test_system_clock_monotonic_increases(self):
        clock = SystemClock()
        t1 = clock.now()
        t2 = clock.now()
        assert t2 >= t1

    def test_system_clock_sleep(self):
        clock = SystemClock()
        t1 = clock.now()
        clock.sleep(0.01)
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

    def test_manual_clock_sleep_advances_time(self):
        clock = ManualClock(start_time=0.0)
        clock.sleep(5.0)
        assert clock.now() == 5.0

    def test_manual_clock_sleep_records_history(self):
        clock = ManualClock()
        clock.sleep(1.0)
        clock.sleep(2.5)
        clock.sleep(0.5)
        assert clock.sleep_history == [1.0, 2.5, 0.5]

    def test_manual_clock_sleep_negative_raises(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot sleep for negative seconds"):
            clock.sleep(-1.0)
