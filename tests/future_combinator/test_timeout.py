from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.future_combinator import (
    Future,
    FutureState,
    FutureTimeoutError,
    with_timeout,
)


class TestWithTimeout:
    def test_completes_before_timeout(self):
        f = Future()

        def complete():
            time.sleep(0.05)
            f.set_result(42)

        threading.Thread(target=complete, daemon=True).start()
        timed = with_timeout(f, 2.0)
        assert timed.get(timeout=3.0) == 42

    def test_timeout_fires(self):
        f = Future()
        timed = with_timeout(f, 0.1)
        with pytest.raises(FutureTimeoutError):
            timed.get(timeout=2.0)

    def test_already_completed_future_bypasses_timeout(self):
        f = Future.completed(99)
        timed = with_timeout(f, 0.05)
        assert timed.result == 99

    def test_already_failed_future_bypasses_timeout(self):
        err = RuntimeError("already failed")
        f = Future.failed(err)
        timed = with_timeout(f, 0.05)
        assert timed.state == FutureState.FAILED
        assert timed.error is err

    def test_original_future_succeeds_before_timeout(self):
        f = Future()
        timed = with_timeout(f, 1.0)

        f.set_result("done")

        assert timed.get(timeout=2.0) == "done"
        assert f.state == FutureState.COMPLETED

    def test_original_future_fails_before_timeout(self):
        f = Future()
        timed = with_timeout(f, 1.0)

        f.set_error(ValueError("original error"))

        with pytest.raises(ValueError, match="original error"):
            timed.get(timeout=2.0)

    def test_timeout_does_not_affect_already_settled(self):
        f = Future()
        f.set_result("early")
        timed = with_timeout(f, 0.01)
        time.sleep(0.05)
        assert timed.result == "early"

    def test_negative_timeout_raises(self):
        f = Future()
        with pytest.raises(ValueError):
            with_timeout(f, -1.0)

    def test_zero_timeout_raises(self):
        f = Future()
        with pytest.raises(ValueError):
            with_timeout(f, 0.0)

    def test_timeout_with_all_combinator(self):
        from solocoder_py.future_combinator import all_combinator

        f1 = Future()
        f2 = Future()
        combined = all_combinator([f1, f2])
        timed = with_timeout(combined, 0.1)

        f1.set_result(1)

        with pytest.raises(FutureTimeoutError):
            timed.get(timeout=2.0)

    def test_timeout_with_race_combinator(self):
        from solocoder_py.future_combinator import race_combinator

        f1 = Future()
        f2 = Future()
        combined = race_combinator([f1, f2])
        timed = with_timeout(combined, 0.1)

        with pytest.raises(FutureTimeoutError):
            timed.get(timeout=2.0)

    def test_result_arrives_just_before_timeout(self):
        f = Future()
        timed = with_timeout(f, 0.15)

        def complete():
            time.sleep(0.05)
            f.set_result("just in time")

        threading.Thread(target=complete, daemon=True).start()
        assert timed.get(timeout=2.0) == "just in time"
