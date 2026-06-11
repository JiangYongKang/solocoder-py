from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.future_combinator import (
    Future,
    FutureAlreadyCompletedError,
    FutureNotReadyError,
    FutureState,
    FutureTimeoutError,
)


class TestFutureCreation:
    def test_initial_state_is_pending(self):
        f = Future()
        assert f.state == FutureState.PENDING
        assert not f.is_done

    def test_result_raises_not_ready_when_pending(self):
        f = Future()
        with pytest.raises(FutureNotReadyError):
            _ = f.result

    def test_error_raises_not_ready_when_pending(self):
        f = Future()
        with pytest.raises(FutureNotReadyError):
            _ = f.error


class TestFutureSetResult:
    def test_set_result_transitions_to_completed(self):
        f = Future()
        f.set_result(42)
        assert f.state == FutureState.COMPLETED
        assert f.is_done
        assert f.result == 42
        assert f.error is None

    def test_set_result_twice_raises(self):
        f = Future()
        f.set_result(1)
        with pytest.raises(FutureAlreadyCompletedError):
            f.set_result(2)

    def test_set_result_then_set_error_raises(self):
        f = Future()
        f.set_result(1)
        with pytest.raises(FutureAlreadyCompletedError):
            f.set_error(RuntimeError("boom"))

    def test_set_result_various_types(self):
        f1 = Future()
        f1.set_result(None)
        assert f1.result is None

        f2 = Future()
        f2.set_result([1, 2, 3])
        assert f2.result == [1, 2, 3]

        f3 = Future()
        f3.set_result({"key": "value"})
        assert f3.result == {"key": "value"}


class TestFutureSetError:
    def test_set_error_transitions_to_failed(self):
        f = Future()
        err = RuntimeError("something went wrong")
        f.set_error(err)
        assert f.state == FutureState.FAILED
        assert f.is_done
        assert f.error is err

    def test_result_raises_error_when_failed(self):
        f = Future()
        err = ValueError("bad value")
        f.set_error(err)
        with pytest.raises(ValueError, match="bad value"):
            _ = f.result

    def test_set_error_twice_raises(self):
        f = Future()
        f.set_error(RuntimeError("first"))
        with pytest.raises(FutureAlreadyCompletedError):
            f.set_error(RuntimeError("second"))

    def test_set_error_then_set_result_raises(self):
        f = Future()
        f.set_error(RuntimeError("boom"))
        with pytest.raises(FutureAlreadyCompletedError):
            f.set_result(1)


class TestFutureCallback:
    def test_callback_fired_on_set_result(self):
        f = Future()
        results = []
        f.add_callback(lambda fut: results.append(fut.result))
        f.set_result(99)
        assert results == [99]

    def test_callback_fired_on_set_error(self):
        f = Future()
        errors = []
        f.add_callback(lambda fut: errors.append(fut.error))
        f.set_error(RuntimeError("oops"))
        assert len(errors) == 1
        assert isinstance(errors[0], RuntimeError)

    def test_callback_fired_immediately_if_already_completed(self):
        f = Future()
        f.set_result(10)
        results = []
        f.add_callback(lambda fut: results.append(fut.result))
        assert results == [10]

    def test_callback_fired_immediately_if_already_failed(self):
        f = Future()
        f.set_error(RuntimeError("fail"))
        errors = []
        f.add_callback(lambda fut: errors.append(fut.error))
        assert len(errors) == 1

    def test_callback_exception_does_not_affect_others(self):
        f = Future()
        results = []

        def bad_callback(fut: Future) -> None:
            raise RuntimeError("callback error")

        f.add_callback(bad_callback)
        f.add_callback(lambda fut: results.append(fut.result))
        f.set_result(42)
        assert results == [42]

    def test_multiple_callbacks(self):
        f = Future()
        results = []
        f.add_callback(lambda fut: results.append(1))
        f.add_callback(lambda fut: results.append(2))
        f.add_callback(lambda fut: results.append(3))
        f.set_result("ok")
        assert results == [1, 2, 3]


class TestFutureWait:
    def test_wait_returns_true_when_completed(self):
        f = Future()
        f.set_result(1)
        assert f.wait() is True

    def test_wait_with_timeout_returns_true(self):
        f = Future()

        def complete():
            time.sleep(0.05)
            f.set_result(1)

        t = threading.Thread(target=complete, daemon=True)
        t.start()
        assert f.wait(timeout=2.0) is True

    def test_wait_with_timeout_returns_false(self):
        f = Future()
        assert f.wait(timeout=0.05) is False


class TestFutureGet:
    def test_get_returns_result(self):
        f = Future()
        f.set_result("hello")
        assert f.get() == "hello"

    def test_get_raises_original_error(self):
        f = Future()
        f.set_error(ValueError("bad"))
        with pytest.raises(ValueError, match="bad"):
            f.get()

    def test_get_with_timeout_raises_timeout_error(self):
        f = Future()
        with pytest.raises(FutureTimeoutError):
            f.get(timeout=0.05)

    def test_get_waits_then_returns(self):
        f = Future()

        def complete():
            time.sleep(0.05)
            f.set_result(42)

        t = threading.Thread(target=complete, daemon=True)
        t.start()
        assert f.get(timeout=2.0) == 42


class TestFutureStaticFactories:
    def test_completed_creates_completed_future(self):
        f = Future.completed(123)
        assert f.state == FutureState.COMPLETED
        assert f.result == 123

    def test_failed_creates_failed_future(self):
        err = RuntimeError("fail")
        f = Future.failed(err)
        assert f.state == FutureState.FAILED
        assert f.error is err

    def test_from_callable_success(self):
        f = Future.from_callable(lambda: 42)
        assert f.get(timeout=2.0) == 42

    def test_from_callable_error(self):
        f = Future.from_callable(lambda: (_ for _ in ()).throw(ValueError("boom")))
        with pytest.raises(ValueError, match="boom"):
            f.get(timeout=2.0)

    def test_from_callable_concurrent(self):
        results = []

        def slow_fn(idx: int):
            time.sleep(0.05)
            return idx

        futures = [Future.from_callable(lambda i=i: slow_fn(i)) for i in range(5)]
        for f in futures:
            results.append(f.get(timeout=2.0))
        assert results == [0, 1, 2, 3, 4]


class TestFutureConcurrent:
    def test_concurrent_set_result_only_one_succeeds(self):
        f = Future()
        success_count = 0
        barrier = threading.Barrier(3)

        def try_set(val):
            nonlocal success_count
            barrier.wait()
            try:
                f.set_result(val)
                success_count += 1
            except FutureAlreadyCompletedError:
                pass

        threads = [threading.Thread(target=try_set, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert success_count == 1
        assert f.state == FutureState.COMPLETED
