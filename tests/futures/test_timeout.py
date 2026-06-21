from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.futures import Future, FutureState, TimeoutError


class TestWithTimeout:
    def test_completes_before_timeout(self):
        f = Future()

        def complete():
            time.sleep(0.05)
            f._fulfill(42)

        threading.Thread(target=complete, daemon=True).start()
        timed = f.with_timeout(2.0)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 3.0:
            time.sleep(0.01)

        assert timed.state == FutureState.FULFILLED
        assert timed.value == 42

    def test_timeout_fires(self):
        f = Future()
        timed = f.with_timeout(0.1)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)
        assert timed.reason.timeout == 0.1

    def test_already_fulfilled_bypasses_timeout(self):
        f = Future.resolve(99)
        timed = f.with_timeout(0.05)
        assert timed is f
        assert timed.value == 99

    def test_already_rejected_bypasses_timeout(self):
        err = RuntimeError("already failed")
        f = Future.reject(err)
        timed = f.with_timeout(0.05)
        assert timed is f
        assert timed.state == FutureState.REJECTED
        assert timed.reason is err

    def test_original_future_succeeds_before_timeout(self):
        f = Future()
        timed = f.with_timeout(1.0)

        f._fulfill("done")

        assert timed.value == "done"
        assert f.state == FutureState.FULFILLED

    def test_original_future_fails_before_timeout(self):
        f = Future()
        timed = f.with_timeout(1.0)

        f._reject(ValueError("original error"))

        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, ValueError)
        assert str(timed.reason) == "original error"

    def test_negative_timeout_raises(self):
        f = Future()
        with pytest.raises(ValueError, match="timeout must be positive"):
            f.with_timeout(-1.0)

    def test_zero_timeout_raises(self):
        f = Future()
        with pytest.raises(ValueError, match="timeout must be positive"):
            f.with_timeout(0.0)

    def test_timeout_result_ignores_late_fulfillment(self):
        f = Future()
        timed = f.with_timeout(0.05)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.REJECTED

        f._fulfill("too late")
        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)

    def test_timeout_result_ignores_late_rejection(self):
        f = Future()
        timed = f.with_timeout(0.05)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)

        f._reject(RuntimeError("too late"))
        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)

    def test_timeout_with_all_combinator(self):
        f1 = Future()
        f2 = Future()
        combined = Future.all([f1, f2])
        timed = combined.with_timeout(0.1)

        f1._fulfill(1)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)

    def test_timeout_with_race_combinator(self):
        f1 = Future()
        f2 = Future()
        combined = Future.race([f1, f2])
        timed = combined.with_timeout(0.1)

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.REJECTED
        assert isinstance(timed.reason, TimeoutError)

    def test_result_arrives_just_before_timeout(self):
        f = Future()
        timed = f.with_timeout(0.2)

        def complete():
            time.sleep(0.05)
            f._fulfill("just in time")

        threading.Thread(target=complete, daemon=True).start()

        start = time.time()
        while timed.state == FutureState.PENDING and time.time() - start < 2.0:
            time.sleep(0.01)

        assert timed.state == FutureState.FULFILLED
        assert timed.value == "just in time"
