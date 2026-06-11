from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.future_combinator import (
    AllCombinatorError,
    AnyCombinatorError,
    Future,
    FutureState,
    all_combinator,
    any_combinator,
    race_combinator,
)


def _delayed_result_future(value, delay):
    f = Future()

    def complete():
        time.sleep(delay)
        f.set_result(value)

    threading.Thread(target=complete, daemon=True).start()
    return f


def _delayed_error_future(error, delay):
    f = Future()

    def complete():
        time.sleep(delay)
        f.set_error(error)

    threading.Thread(target=complete, daemon=True).start()
    return f


class TestAllCombinator:
    def test_all_succeed(self):
        f1 = _delayed_result_future(1, 0.02)
        f2 = _delayed_result_future(2, 0.04)
        f3 = _delayed_result_future(3, 0.06)
        combined = all_combinator([f1, f2, f3])
        assert combined.get(timeout=2.0) == [1, 2, 3]

    def test_all_succeed_preserves_order(self):
        f1 = _delayed_result_future("a", 0.06)
        f2 = _delayed_result_future("b", 0.02)
        f3 = _delayed_result_future("c", 0.04)
        combined = all_combinator([f1, f2, f3])
        assert combined.get(timeout=2.0) == ["a", "b", "c"]

    def test_one_fails(self):
        f1 = _delayed_result_future(1, 0.02)
        f2 = _delayed_error_future(RuntimeError("boom"), 0.01)
        f3 = _delayed_result_future(3, 0.04)
        combined = all_combinator([f1, f2, f3])
        with pytest.raises(AllCombinatorError) as exc_info:
            combined.get(timeout=2.0)
        assert isinstance(exc_info.value.first_error, RuntimeError)

    def test_multiple_fail_uses_first(self):
        f1 = _delayed_error_future(ValueError("first"), 0.01)
        f2 = _delayed_error_future(RuntimeError("second"), 0.06)
        combined = all_combinator([f1, f2])
        with pytest.raises(AllCombinatorError) as exc_info:
            combined.get(timeout=2.0)
        assert isinstance(exc_info.value.first_error, ValueError)
        assert str(exc_info.value.first_error) == "first"

    def test_empty_list_returns_completed_empty(self):
        combined = all_combinator([])
        assert combined.state == FutureState.COMPLETED
        assert combined.result == []

    def test_single_future_succeed(self):
        f = Future.completed(42)
        combined = all_combinator([f])
        assert combined.get(timeout=1.0) == [42]

    def test_single_future_fail(self):
        f = Future.failed(RuntimeError("oops"))
        combined = all_combinator([f])
        with pytest.raises(AllCombinatorError):
            combined.get(timeout=1.0)

    def test_already_completed_futures(self):
        futures = [Future.completed(i) for i in range(5)]
        combined = all_combinator(futures)
        assert combined.get(timeout=1.0) == [0, 1, 2, 3, 4]

    def test_fails_immediately_on_first_error(self):
        f1 = Future.failed(RuntimeError("immediate"))
        f2 = Future()
        combined = all_combinator([f1, f2])
        with pytest.raises(AllCombinatorError):
            combined.get(timeout=1.0)


class TestAnyCombinator:
    def test_first_success_wins(self):
        f1 = _delayed_error_future(RuntimeError("fail"), 0.06)
        f2 = _delayed_result_future("winner", 0.02)
        f3 = _delayed_result_future("slow", 0.10)
        combined = any_combinator([f1, f2, f3])
        assert combined.get(timeout=2.0) == "winner"

    def test_all_fail(self):
        f1 = _delayed_error_future(ValueError("e1"), 0.02)
        f2 = _delayed_error_future(RuntimeError("e2"), 0.04)
        f3 = _delayed_error_future(TypeError("e3"), 0.06)
        combined = any_combinator([f1, f2, f3])
        with pytest.raises(AnyCombinatorError) as exc_info:
            combined.get(timeout=2.0)
        assert len(exc_info.value.errors) == 3
        assert isinstance(exc_info.value.errors[0], ValueError)
        assert isinstance(exc_info.value.errors[1], RuntimeError)
        assert isinstance(exc_info.value.errors[2], TypeError)

    def test_empty_list_returns_failed(self):
        combined = any_combinator([])
        assert combined.state == FutureState.FAILED
        assert isinstance(combined.error, AnyCombinatorError)
        assert combined.error.errors == []

    def test_single_future_succeed(self):
        f = Future.completed("ok")
        combined = any_combinator([f])
        assert combined.get(timeout=1.0) == "ok"

    def test_single_future_fail(self):
        f = Future.failed(RuntimeError("oops"))
        combined = any_combinator([f])
        with pytest.raises(AnyCombinatorError) as exc_info:
            combined.get(timeout=1.0)
        assert len(exc_info.value.errors) == 1

    def test_first_success_completes_immediately(self):
        f1 = Future.completed("instant")
        f2 = Future()
        combined = any_combinator([f1, f2])
        assert combined.get(timeout=1.0) == "instant"

    def test_all_fail_aggregates_errors_in_order(self):
        errors = [ValueError(f"e{i}") for i in range(3)]
        futures = [Future.failed(e) for e in errors]
        combined = any_combinator(futures)
        with pytest.raises(AnyCombinatorError) as exc_info:
            combined.get(timeout=1.0)
        for i, err in enumerate(exc_info.value.errors):
            assert isinstance(err, ValueError)
            assert str(err) == f"e{i}"


class TestRaceCombinator:
    def test_first_success_wins(self):
        f1 = _delayed_result_future("fast", 0.02)
        f2 = _delayed_result_future("slow", 0.10)
        combined = race_combinator([f1, f2])
        assert combined.get(timeout=2.0) == "fast"

    def test_first_failure_wins(self):
        f1 = _delayed_error_future(RuntimeError("fast fail"), 0.02)
        f2 = _delayed_result_future("slow success", 0.10)
        combined = race_combinator([f1, f2])
        with pytest.raises(RuntimeError, match="fast fail"):
            combined.get(timeout=2.0)

    def test_first_complete_is_failure(self):
        f1 = _delayed_error_future(ValueError("fail first"), 0.02)
        f2 = _delayed_result_future("success", 0.06)
        combined = race_combinator([f1, f2])
        with pytest.raises(ValueError, match="fail first"):
            combined.get(timeout=2.0)

    def test_first_complete_is_success(self):
        f1 = _delayed_result_future("first", 0.02)
        f2 = _delayed_error_future(RuntimeError("later"), 0.06)
        combined = race_combinator([f1, f2])
        assert combined.get(timeout=2.0) == "first"

    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError):
            race_combinator([])

    def test_single_future_success(self):
        f = Future.completed("only")
        combined = race_combinator([f])
        assert combined.get(timeout=1.0) == "only"

    def test_single_future_failure(self):
        f = Future.failed(RuntimeError("solo fail"))
        combined = race_combinator([f])
        with pytest.raises(RuntimeError, match="solo fail"):
            combined.get(timeout=1.0)

    def test_already_completed_wins(self):
        f1 = Future.completed("instant")
        f2 = Future()
        combined = race_combinator([f1, f2])
        assert combined.get(timeout=1.0) == "instant"

    def test_already_failed_wins(self):
        f1 = Future.failed(RuntimeError("instant fail"))
        f2 = Future()
        combined = race_combinator([f1, f2])
        with pytest.raises(RuntimeError, match="instant fail"):
            combined.get(timeout=1.0)
