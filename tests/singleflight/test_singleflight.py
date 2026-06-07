from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.singleflight import (
    CallCancelledError,
    Clock,
    KeyStats,
    ManualClock,
    SingleFlight,
    SingleFlightError,
    SystemClock,
    WaitTimeoutError,
)

from .conftest import make_sf


class TestKeyStatsModel:
    def test_key_stats_creation(self):
        stats = KeyStats(key="test-key")
        assert stats.key == "test-key"
        assert stats.executions == 0
        assert stats.shared_hits == 0
        assert stats.failures == 0

    def test_key_stats_custom_values(self):
        stats = KeyStats(key="k", executions=5, shared_hits=10, failures=2)
        assert stats.key == "k"
        assert stats.executions == 5
        assert stats.shared_hits == 10
        assert stats.failures == 2

    def test_key_stats_empty_key_rejected(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            KeyStats(key="")

    def test_key_stats_negative_executions_rejected(self):
        with pytest.raises(ValueError, match="executions cannot be negative"):
            KeyStats(key="k", executions=-1)

    def test_key_stats_negative_shared_hits_rejected(self):
        with pytest.raises(ValueError, match="shared_hits cannot be negative"):
            KeyStats(key="k", shared_hits=-1)

    def test_key_stats_negative_failures_rejected(self):
        with pytest.raises(ValueError, match="failures cannot be negative"):
            KeyStats(key="k", failures=-1)


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

    def test_manual_clock_advance(self):
        clock = ManualClock()
        clock.advance(5.0)
        assert clock.now() == 5.0
        clock.advance(2.5)
        assert clock.now() == 7.5

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0

    def test_manual_clock_advance_negative_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot advance by negative seconds"):
            clock.advance(-1)

    def test_clock_is_abc(self):
        with pytest.raises(TypeError):
            Clock()


class TestSingleFlightDefaultClock:
    def test_default_clock_is_system_clock(self):
        sf = make_sf()
        assert isinstance(sf.clock, SystemClock)

    def test_custom_clock_injected(self):
        clock = ManualClock()
        sf = make_sf(clock=clock)
        assert sf.clock is clock


class TestSingleRequestNoMerge:
    def test_single_request_returns_result(self):
        sf = make_sf()
        result = sf.do("key1", lambda: 42)
        assert result == 42

    def test_single_request_with_string_result(self):
        sf = make_sf()
        result = sf.do("key2", lambda: "hello")
        assert result == "hello"

    def test_single_request_none_result(self):
        sf = make_sf()
        result = sf.do("key3", lambda: None)
        assert result is None

    def test_single_request_stats(self):
        sf = make_sf()
        sf.do("k", lambda: 1)
        stats = sf.get_stats("k")
        assert stats is not None
        assert stats.executions == 1
        assert stats.shared_hits == 0
        assert stats.failures == 0

    def test_empty_key_rejected(self):
        sf = make_sf()
        with pytest.raises(ValueError, match="key cannot be empty"):
            sf.do("", lambda: 1)

    def test_non_callable_rejected(self):
        sf = make_sf()
        with pytest.raises(ValueError, match="fn must be callable"):
            sf.do("k", 42)

    def test_zero_timeout_rejected(self):
        sf = make_sf()
        with pytest.raises(ValueError, match="timeout must be positive"):
            sf.do("k", lambda: 1, timeout=0)

    def test_negative_timeout_rejected(self):
        sf = make_sf()
        with pytest.raises(ValueError, match="timeout must be positive"):
            sf.do("k", lambda: 1, timeout=-1)


class TestSameKeyMultiThreadMerge:
    def test_same_key_multiple_threads_executes_once(self):
        sf = make_sf()
        call_count = 0
        count_lock = threading.Lock()
        barrier = threading.Barrier(5)
        results: dict[int, int] = {}
        errors: dict[int, Exception] = {}

        def worker(idx: int):
            barrier.wait()
            try:
                def fn():
                    nonlocal call_count
                    with count_lock:
                        call_count += 1
                    time.sleep(0.05)
                    return idx * 10
                results[idx] = sf.do("shared-key", fn)
            except Exception as e:
                errors[idx] = e

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert call_count == 1
        assert len(errors) == 0
        for i in range(5):
            assert i in results
        leader_result = results[0]
        for i in range(5):
            assert results[i] == leader_result

    def test_same_key_stats_reflect_shared_hits(self):
        sf = make_sf()
        call_count = 0
        barrier = threading.Barrier(4)
        results = []

        def worker():
            barrier.wait()
            def fn():
                nonlocal call_count
                call_count += 1
                time.sleep(0.05)
                return "done"
            results.append(sf.do("stats-key", fn))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert call_count == 1
        assert len(results) == 4
        stats = sf.get_stats("stats-key")
        assert stats is not None
        assert stats.executions == 1
        assert stats.shared_hits == 3
        assert stats.failures == 0


class TestDifferentKeysParallel:
    def test_different_keys_execute_in_parallel(self):
        sf = make_sf()
        start_times: dict[str, float] = {}
        end_times: dict[str, float] = {}
        lock = threading.Lock()

        def worker(key: str):
            def fn():
                with lock:
                    start_times[key] = time.monotonic()
                time.sleep(0.1)
                with lock:
                    end_times[key] = time.monotonic()
                return key
            return sf.do(key, fn)

        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(f"key-{i}",))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(start_times) == 3
        assert len(end_times) == 3
        total_elapsed = max(end_times.values()) - min(start_times.values())
        assert total_elapsed < 0.25

    def test_different_keys_stats_independent(self):
        sf = make_sf()

        sf.do("a", lambda: 1)
        sf.do("b", lambda: 2)
        sf.do("a", lambda: 3)

        stats_a = sf.get_stats("a")
        stats_b = sf.get_stats("b")
        assert stats_a is not None
        assert stats_b is not None
        assert stats_a.executions == 2
        assert stats_a.shared_hits == 0
        assert stats_b.executions == 1
        assert stats_b.shared_hits == 0


class TestReExecuteAfterCompletion:
    def test_execute_again_after_first_completes(self):
        sf = make_sf()
        call_count = 0

        def fn():
            nonlocal call_count
            call_count += 1
            return call_count

        r1 = sf.do("rerun-key", fn)
        assert r1 == 1
        assert call_count == 1

        r2 = sf.do("rerun-key", fn)
        assert r2 == 2
        assert call_count == 2

        stats = sf.get_stats("rerun-key")
        assert stats is not None
        assert stats.executions == 2
        assert stats.shared_hits == 0

    def test_in_flight_count_zero_after_completion(self):
        sf = make_sf()
        assert sf.in_flight_count("k") == 0
        sf.do("k", lambda: time.sleep(0.01))
        assert sf.in_flight_count("k") == 0


class TestWaitTimeout:
    def test_waiter_times_out(self):
        sf = make_sf()
        slow_leader_started = threading.Event()
        results: dict[str, object] = {}
        errors: dict[str, Exception] = {}

        def leader_worker():
            def fn():
                slow_leader_started.set()
                time.sleep(2.0)
                return "leader-done"
            try:
                results["leader"] = sf.do("timeout-key", fn)
            except Exception as e:
                errors["leader"] = e

        def waiter_worker():
            try:
                results["waiter"] = sf.do("timeout-key", lambda: "should-not-run", timeout=0.1)
            except Exception as e:
                errors["waiter"] = e

        leader = threading.Thread(target=leader_worker)
        leader.start()
        slow_leader_started.wait(timeout=2)

        waiter = threading.Thread(target=waiter_worker)
        waiter.start()
        waiter.join(timeout=5)

        assert "waiter" not in results
        assert "waiter" in errors
        assert isinstance(errors["waiter"], WaitTimeoutError)

        leader.join(timeout=10)
        assert results.get("leader") == "leader-done"

    def test_timeout_error_is_single_flight_error(self):
        assert issubclass(WaitTimeoutError, SingleFlightError)


class TestExceptionPropagation:
    def test_regular_exception_is_shared_with_waiters(self):
        sf = make_sf()
        barrier = threading.Barrier(3)
        errors = []

        class CustomError(Exception):
            pass

        def worker():
            barrier.wait()
            def fn():
                time.sleep(0.05)
                raise CustomError("business error")
            try:
                sf.do("fail-key", fn)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 3
        for e in errors:
            assert isinstance(e, CustomError)
            assert str(e) == "business error"

    def test_base_exception_not_captured_as_failure(self):
        sf = make_sf()

        class FatalSignal(BaseException):
            pass

        with pytest.raises(FatalSignal):
            sf.do("fatal", lambda: (_ for _ in ()).throw(FatalSignal("system signal")))

        assert sf.get_stats("fatal") is None
        assert sf.in_flight_count("fatal") == 0

    def test_base_exception_waiters_are_woken_with_call_cancelled_error(self):
        sf = make_sf()
        leader_ready = threading.Event()
        leader_errors: dict[str, BaseException] = {}
        waiter_errors: dict[str, Exception] = {}
        waiter_results: dict[str, object] = {}

        class FatalSignal(BaseException):
            pass

        def leader_worker():
            def fn():
                leader_ready.set()
                time.sleep(0.05)
                raise FatalSignal("interrupt")
            try:
                sf.do("cancel-key", fn)
            except BaseException as e:
                leader_errors["leader"] = e

        def waiter_worker(idx: int):
            try:
                waiter_results[idx] = sf.do("cancel-key", lambda: "should-not-run")
            except Exception as e:
                waiter_errors[idx] = e

        leader = threading.Thread(target=leader_worker)
        leader.start()
        leader_ready.wait(timeout=2)

        waiters = [threading.Thread(target=waiter_worker, args=(i,)) for i in range(3)]
        for w in waiters:
            w.start()
        for w in waiters:
            w.join(timeout=5)

        leader.join(timeout=5)

        assert isinstance(leader_errors.get("leader"), FatalSignal)
        for i in range(3):
            assert i not in waiter_results
            assert i in waiter_errors
            assert isinstance(waiter_errors[i], CallCancelledError)
            assert issubclass(CallCancelledError, SingleFlightError)
        assert sf.get_stats("cancel-key") is None
        assert sf.in_flight_count("cancel-key") == 0

    def test_call_cancelled_error_is_single_flight_error(self):
        assert issubclass(CallCancelledError, SingleFlightError)

    def test_regular_exception_counts_as_failure(self):
        sf = make_sf()

        class BizError(Exception):
            pass

        with pytest.raises(BizError):
            sf.do("biz", lambda: (_ for _ in ()).throw(BizError("oops")))

        stats = sf.get_stats("biz")
        assert stats is not None
        assert stats.executions == 1
        assert stats.failures == 1


class TestLeaderFailure:
    def test_waiter_receives_same_error(self):
        sf = make_sf()
        barrier = threading.Barrier(3)
        results = []
        errors = []

        class CustomError(Exception):
            pass

        def worker():
            barrier.wait()
            def fn():
                time.sleep(0.05)
                raise CustomError("something failed")
            try:
                results.append(sf.do("fail-key", fn))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 0
        assert len(errors) == 3
        for e in errors:
            assert isinstance(e, CustomError)
            assert str(e) == "something failed"

        stats = sf.get_stats("fail-key")
        assert stats is not None
        assert stats.executions == 1
        assert stats.shared_hits == 2
        assert stats.failures == 1

    def test_failure_not_cached_retry_executes_again(self):
        sf = make_sf()
        call_count = 0

        class CustomError(Exception):
            pass

        def failing_fn():
            nonlocal call_count
            call_count += 1
            raise CustomError(f"fail-{call_count}")

        with pytest.raises(CustomError, match="fail-1"):
            sf.do("retry-key", failing_fn)
        assert call_count == 1

        with pytest.raises(CustomError, match="fail-2"):
            sf.do("retry-key", failing_fn)
        assert call_count == 2

        def success_fn():
            nonlocal call_count
            call_count += 1
            return call_count

        result = sf.do("retry-key", success_fn)
        assert result == 3
        assert call_count == 3

        stats = sf.get_stats("retry-key")
        assert stats is not None
        assert stats.executions == 3
        assert stats.failures == 2


class TestStats:
    def test_get_stats_returns_copy(self):
        sf = make_sf()
        sf.do("k", lambda: 1)
        s1 = sf.get_stats("k")
        assert s1 is not None
        s1.executions = 999
        s2 = sf.get_stats("k")
        assert s2 is not None
        assert s2.executions == 1

    def test_get_stats_nonexistent_returns_none(self):
        sf = make_sf()
        assert sf.get_stats("nope") is None

    def test_get_stats_empty_key_rejected(self):
        sf = make_sf()
        with pytest.raises(ValueError, match="key cannot be empty"):
            sf.get_stats("")

    def test_get_all_stats(self):
        sf = make_sf()
        sf.do("x", lambda: 1)
        sf.do("y", lambda: 2)
        all_stats = sf.get_all_stats()
        assert "x" in all_stats
        assert "y" in all_stats
        assert all_stats["x"].executions == 1
        assert all_stats["y"].executions == 1

    def test_reset_stats(self):
        sf = make_sf()
        sf.do("a", lambda: 1)
        assert sf.get_stats("a") is not None
        sf.reset_stats()
        assert sf.get_stats("a") is None
        assert sf.get_all_stats() == {}


class TestInFlightCount:
    def test_in_flight_count_during_execution(self):
        sf = make_sf()
        ready = threading.Event()
        proceed = threading.Event()

        def slow_fn():
            ready.set()
            proceed.wait(timeout=5)
            return "ok"

        def leader():
            sf.do("inflight", slow_fn)

        t = threading.Thread(target=leader)
        t.start()
        ready.wait(timeout=2)

        assert sf.in_flight_count("inflight") == 1
        assert sf.in_flight_count() == 1
        assert sf.in_flight_count("other") == 0

        proceed.set()
        t.join(timeout=5)
        assert sf.in_flight_count("inflight") == 0
        assert sf.in_flight_count() == 0


class TestClear:
    def test_clear_removes_everything(self):
        sf = make_sf()
        sf.do("a", lambda: 1)
        sf.do("b", lambda: 2)
        assert len(sf.get_all_stats()) == 2
        sf.clear()
        assert len(sf.get_all_stats()) == 0
        assert sf.in_flight_count() == 0
