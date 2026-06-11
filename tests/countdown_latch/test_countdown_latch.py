from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.countdown_latch import (
    Clock,
    CountdownLatch,
    CountdownLatchError,
    InvalidCountError,
    LatchState,
    LatchStats,
    LatchTimeoutError,
    ManualClock,
    SystemClock,
)

from .conftest import make_latch


class TestLatchState:
    def test_state_values(self):
        assert LatchState.WAITING == "waiting"
        assert LatchState.OPENED == "opened"


class TestLatchStats:
    def test_stats_creation(self):
        stats = LatchStats(
            initial_count=5,
            current_count=3,
            state=LatchState.WAITING,
            waiting_threads=2,
        )
        assert stats.initial_count == 5
        assert stats.current_count == 3
        assert stats.state == LatchState.WAITING
        assert stats.waiting_threads == 2


class TestClock:
    def test_system_clock_returns_monotonic(self):
        clock = SystemClock()
        t1 = clock.now()
        time.sleep(0.01)
        t2 = clock.now()
        assert t2 >= t1

    def test_manual_clock_initial_value(self):
        clock = ManualClock()
        assert clock.now() == 0.0

    def test_manual_clock_custom_start(self):
        clock = ManualClock(start_time=100.5)
        assert clock.now() == 100.5

    def test_manual_clock_negative_start_rejected(self):
        with pytest.raises(ValueError, match="start_time cannot be negative"):
            ManualClock(start_time=-1.0)

    def test_manual_clock_advance(self):
        clock = ManualClock()
        clock.advance(5.0)
        assert clock.now() == 5.0
        clock.advance(2.5)
        assert clock.now() == 7.5

    def test_manual_clock_advance_negative_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot advance by negative seconds"):
            clock.advance(-1.0)

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0

    def test_manual_clock_set_negative_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="timestamp cannot be negative"):
            clock.set(-5.0)

    def test_clock_is_abc(self):
        with pytest.raises(TypeError):
            Clock()


class TestExceptions:
    def test_invalid_count_error_is_latch_error(self):
        assert issubclass(InvalidCountError, CountdownLatchError)

    def test_timeout_error_is_latch_error(self):
        assert issubclass(LatchTimeoutError, CountdownLatchError)


class TestLatchCreation:
    def test_create_latch_with_positive_count(self):
        latch = make_latch(3)
        assert latch.count == 3
        assert latch.current_count == 3
        assert latch.is_open is False
        stats = latch.get_stats()
        assert stats.initial_count == 3
        assert stats.current_count == 3
        assert stats.state == LatchState.WAITING

    def test_create_latch_with_zero_count(self):
        latch = make_latch(0)
        assert latch.count == 0
        assert latch.current_count == 0
        assert latch.is_open is True
        stats = latch.get_stats()
        assert stats.state == LatchState.OPENED

    def test_create_latch_with_negative_count_rejected(self):
        with pytest.raises(InvalidCountError, match="count cannot be negative"):
            make_latch(-1)

    def test_default_clock_is_system_clock(self):
        latch = make_latch(3)
        assert isinstance(latch.clock, SystemClock)

    def test_custom_clock_injected(self):
        clock = ManualClock()
        latch = make_latch(3, clock=clock)
        assert latch.clock is clock


class TestCountDownNormalFlow:
    def test_single_count_down(self):
        latch = make_latch(3)
        latch.count_down()
        assert latch.current_count == 2
        assert latch.is_open is False

    def test_multiple_count_down_to_zero(self):
        latch = make_latch(3)
        latch.count_down()
        assert latch.current_count == 2
        latch.count_down()
        assert latch.current_count == 1
        latch.count_down()
        assert latch.current_count == 0
        assert latch.is_open is True
        stats = latch.get_stats()
        assert stats.state == LatchState.OPENED

    def test_count_down_from_one_opens_immediately(self):
        latch = make_latch(1)
        assert latch.current_count == 1
        latch.count_down()
        assert latch.current_count == 0
        assert latch.is_open is True


class TestCountDownEdgeCases:
    def test_count_down_below_zero_clamped(self):
        latch = make_latch(2)
        latch.count_down()
        latch.count_down()
        assert latch.current_count == 0
        latch.count_down()
        assert latch.current_count == 0
        latch.count_down()
        assert latch.current_count == 0

    def test_count_down_on_already_open_latch_does_nothing(self):
        latch = make_latch(1)
        latch.count_down()
        assert latch.is_open is True
        assert latch.current_count == 0
        latch.count_down()
        assert latch.current_count == 0
        assert latch.is_open is True

    def test_count_down_on_zero_initial_latch_does_nothing(self):
        latch = make_latch(0)
        assert latch.is_open is True
        latch.count_down()
        assert latch.current_count == 0
        assert latch.is_open is True


class TestWaitNormalFlow:
    def test_wait_returns_true_after_latch_opens(self):
        latch = make_latch(2)
        results: dict[str, bool] = {}
        errors: dict[str, Exception] = {}

        def waiter(name: str):
            try:
                results[name] = latch.wait()
            except Exception as e:
                errors[name] = e

        t1 = threading.Thread(target=waiter, args=("t1",))
        t2 = threading.Thread(target=waiter, args=("t2",))
        t1.start()
        t2.start()
        time.sleep(0.05)

        assert latch.get_stats().waiting_threads == 2

        latch.count_down()
        latch.count_down()

        t1.join(timeout=5)
        t2.join(timeout=5)

        assert len(errors) == 0
        assert results.get("t1") is True
        assert results.get("t2") is True
        assert latch.is_open is True

    def test_all_waiters_wake_up_simultaneously(self):
        latch = make_latch(1)
        wake_times: dict[str, float] = {}
        start_event = threading.Event()

        def waiter(name: str):
            start_event.wait()
            latch.wait()
            wake_times[name] = time.monotonic()

        threads = [threading.Thread(target=waiter, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()

        start_event.set()
        time.sleep(0.05)
        assert latch.get_stats().waiting_threads == 5

        latch.count_down()

        for t in threads:
            t.join(timeout=5)

        assert len(wake_times) == 5
        times = list(wake_times.values())
        max_diff = max(times) - min(times)
        assert max_diff < 0.1


class TestWaitEdgeCases:
    def test_wait_on_already_open_latch_returns_immediately(self):
        latch = make_latch(0)
        assert latch.is_open is True
        start = time.monotonic()
        result = latch.wait()
        elapsed = time.monotonic() - start
        assert result is True
        assert elapsed < 0.01

    def test_wait_after_latch_opened_returns_immediately(self):
        latch = make_latch(1)
        latch.count_down()
        assert latch.is_open is True
        start = time.monotonic()
        result = latch.wait()
        elapsed = time.monotonic() - start
        assert result is True
        assert elapsed < 0.01

    def test_wait_with_timeout_completes_before_timeout(self):
        latch = make_latch(1)
        results: dict[str, bool] = {}

        def waiter():
            results["t"] = latch.wait(timeout=1.0)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        latch.count_down()
        t.join(timeout=5)

        assert results.get("t") is True

    def test_wait_with_timeout_triggers_timeout(self, manual_clock):
        latch = make_latch(3, clock=manual_clock)
        results: dict[str, bool] = {}

        def waiter():
            results["t"] = latch.wait(timeout=5.0)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        assert latch.get_stats().waiting_threads == 1

        manual_clock.advance(4.9)
        time.sleep(0.02)
        assert not results

        manual_clock.advance(0.2)
        t.join(timeout=5)

        assert results.get("t") is False
        assert latch.is_open is False

    def test_wait_timeout_at_exact_boundary(self, manual_clock):
        latch = make_latch(3, clock=manual_clock)
        results: dict[str, bool] = {}

        def waiter():
            results["t"] = latch.wait(timeout=5.0)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        manual_clock.advance(5.0)
        t.join(timeout=5)

        assert results.get("t") is False

    def test_wait_timeout_not_triggered_if_latch_opens_in_time(self, manual_clock):
        latch = make_latch(1, clock=manual_clock)
        results: dict[str, bool] = {}

        def waiter():
            results["t"] = latch.wait(timeout=5.0)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        manual_clock.advance(3.0)
        latch.count_down()
        t.join(timeout=5)

        assert results.get("t") is True

    def test_zero_timeout_rejected(self):
        latch = make_latch(3)
        with pytest.raises(ValueError, match="timeout must be positive"):
            latch.wait(timeout=0)

    def test_negative_timeout_rejected(self):
        latch = make_latch(3)
        with pytest.raises(ValueError, match="timeout must be positive"):
            latch.wait(timeout=-1.0)


class TestOneShotSemantics:
    def test_latch_remains_open_after_count_reaches_zero(self):
        latch = make_latch(2)
        latch.count_down()
        latch.count_down()
        assert latch.is_open is True

        for _ in range(10):
            latch.count_down()

        assert latch.is_open is True
        assert latch.current_count == 0
        assert latch.wait() is True

    def test_wait_after_latch_opened_returns_true_instantly(self):
        latch = make_latch(3)
        for _ in range(3):
            latch.count_down()

        assert latch.is_open is True
        for _ in range(5):
            start = time.monotonic()
            assert latch.wait() is True
            assert time.monotonic() - start < 0.01

    def test_mixed_count_down_and_wait_after_open(self):
        latch = make_latch(1)
        latch.count_down()
        assert latch.is_open is True

        results = []
        for _ in range(3):
            results.append(latch.wait())
            latch.count_down()

        assert all(r is True for r in results)
        assert latch.current_count == 0
        assert latch.is_open is True


class TestNegativeCountEdgeCase:
    def test_excessive_count_down_does_not_make_count_negative(self):
        latch = make_latch(2)
        latch.count_down()
        latch.count_down()
        assert latch.current_count == 0

        latch.count_down()
        assert latch.current_count == 0

        latch.count_down()
        latch.count_down()
        assert latch.current_count == 0
        assert latch.is_open is True

    def test_latch_opens_even_with_excessive_count_down(self):
        latch = make_latch(3)
        results: dict[str, bool] = {}

        def waiter():
            results["t"] = latch.wait()

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        for _ in range(10):
            latch.count_down()

        t.join(timeout=5)
        assert results.get("t") is True
        assert latch.current_count == 0


class TestMultipleThreadsCountingDown:
    def test_multiple_threads_count_down(self):
        latch = make_latch(5)
        barrier = threading.Barrier(5)
        count_call_count = 0
        count_lock = threading.Lock()

        def worker():
            barrier.wait()
            nonlocal count_call_count
            latch.count_down()
            with count_lock:
                count_call_count += 1

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert count_call_count == 5
        assert latch.current_count == 0
        assert latch.is_open is True

    def test_more_threads_than_count(self):
        latch = make_latch(3)
        results: dict[int, bool] = {}
        errors: dict[int, Exception] = {}

        def counter(idx: int):
            try:
                latch.count_down()
                results[idx] = latch.wait(timeout=1.0)
            except Exception as e:
                errors[idx] = e

        threads = [threading.Thread(target=counter, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        assert len(results) == 10
        assert all(r is True for r in results.values())
        assert latch.current_count == 0
        assert latch.is_open is True


class TestStats:
    def test_stats_reflect_waiting_threads(self):
        latch = make_latch(3)
        start_event = threading.Event()

        def waiter():
            start_event.wait()
            latch.wait()

        threads = [threading.Thread(target=waiter) for _ in range(3)]
        for t in threads:
            t.start()

        start_event.set()
        time.sleep(0.05)

        stats = latch.get_stats()
        assert stats.waiting_threads == 3
        assert stats.current_count == 3
        assert stats.state == LatchState.WAITING

        latch.count_down()
        latch.count_down()
        latch.count_down()

        for t in threads:
            t.join(timeout=5)

        stats = latch.get_stats()
        assert stats.waiting_threads == 0
        assert stats.state == LatchState.OPENED

    def test_stats_after_timeout(self, manual_clock):
        latch = make_latch(3, clock=manual_clock)
        result = None

        def waiter():
            nonlocal result
            result = latch.wait(timeout=5.0)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)

        assert latch.get_stats().waiting_threads == 1

        manual_clock.advance(6.0)
        t.join(timeout=5)

        assert result is False
        assert latch.get_stats().waiting_threads == 0


class TestConcurrentStress:
    def test_high_concurrency_wait_and_countdown(self):
        latch = make_latch(10)
        wait_results: dict[int, bool] = {}
        countdown_results: dict[int, bool] = {}
        errors: dict[int, Exception] = {}
        lock = threading.Lock()

        def waiter(idx: int):
            try:
                result = latch.wait(timeout=2.0)
                with lock:
                    wait_results[idx] = result
            except Exception as e:
                with lock:
                    errors[idx] = e

        def counter(idx: int):
            try:
                latch.count_down()
                with lock:
                    countdown_results[idx] = True
            except Exception as e:
                with lock:
                    errors[idx] = e

        wait_threads = [threading.Thread(target=waiter, args=(i,)) for i in range(50)]
        count_threads = [threading.Thread(target=counter, args=(i,)) for i in range(10)]

        for t in wait_threads:
            t.start()
        for t in count_threads:
            t.start()

        for t in wait_threads:
            t.join(timeout=5)
        for t in count_threads:
            t.join(timeout=5)

        assert len(errors) == 0
        assert len(countdown_results) == 10
        assert len(wait_results) == 50
        assert all(r is True for r in wait_results.values())
        assert latch.is_open is True


class TestRealWorldScenario:
    def test_parallel_tasks_waiting_for_each_other(self):
        num_tasks = 4
        latch = make_latch(num_tasks)
        results: dict[int, float] = {}
        start_barrier = threading.Barrier(num_tasks)
        lock = threading.Lock()

        def worker(task_id: int):
            start_barrier.wait()
            time.sleep(0.01 * task_id)
            with lock:
                results[task_id] = time.monotonic()
            latch.count_down()
            latch.wait()
            with lock:
                results[f"{task_id}_done"] = time.monotonic()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_tasks)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == num_tasks * 2

        for i in range(num_tasks):
            assert i in results
            assert f"{i}_done" in results

        done_times = [results[f"{i}_done"] for i in range(num_tasks)]
        max_done_diff = max(done_times) - min(done_times)
        assert max_done_diff < 0.1
