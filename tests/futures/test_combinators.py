from __future__ import annotations

import pytest

from solocoder_py.futures import Future, FutureState, SettledResult


class TestAllCombinator:
    def test_all_succeed(self):
        f1 = Future.resolve(1)
        f2 = Future.resolve(2)
        f3 = Future.resolve(3)
        combined = Future.all([f1, f2, f3])
        assert combined.value == [1, 2, 3]

    def test_all_preserves_order(self):
        f1 = Future.resolve("a")
        f2 = Future.resolve("b")
        f3 = Future.resolve("c")
        combined = Future.all([f1, f2, f3])
        assert combined.value == ["a", "b", "c"]

    def test_all_with_pending_futures(self):
        f1 = Future()
        f2 = Future()
        f3 = Future()
        combined = Future.all([f1, f2, f3])
        assert combined.state == FutureState.PENDING

        f1._fulfill(1)
        assert combined.state == FutureState.PENDING

        f2._fulfill(2)
        assert combined.state == FutureState.PENDING

        f3._fulfill(3)
        assert combined.value == [1, 2, 3]

    def test_all_one_fails(self):
        f1 = Future.resolve(1)
        f2 = Future.reject(RuntimeError("boom"))
        f3 = Future.resolve(3)
        combined = Future.all([f1, f2, f3])
        assert combined.state == FutureState.REJECTED
        assert isinstance(combined.reason, RuntimeError)
        assert str(combined.reason) == "boom"

    def test_all_first_failure_wins(self):
        f1 = Future.reject(ValueError("first"))
        f2 = Future.reject(RuntimeError("second"))
        combined = Future.all([f1, f2])
        assert isinstance(combined.reason, ValueError)
        assert str(combined.reason) == "first"

    def test_all_empty_list(self):
        combined = Future.all([])
        assert combined.state == FutureState.FULFILLED
        assert combined.value == []

    def test_all_single_future_success(self):
        f = Future.resolve(42)
        combined = Future.all([f])
        assert combined.value == [42]

    def test_all_single_future_fail(self):
        f = Future.reject(RuntimeError("oops"))
        combined = Future.all([f])
        assert combined.state == FutureState.REJECTED
        assert isinstance(combined.reason, RuntimeError)

    def test_all_fails_immediately_on_first_error(self):
        f1 = Future.reject(RuntimeError("immediate"))
        f2 = Future()
        combined = Future.all([f1, f2])
        assert combined.state == FutureState.REJECTED
        assert isinstance(combined.reason, RuntimeError)

    def test_all_mixed_settled_and_pending(self):
        f1 = Future.resolve(1)
        f2 = Future()
        combined = Future.all([f1, f2])
        assert combined.state == FutureState.PENDING

        f2._fulfill(2)
        assert combined.value == [1, 2]


class TestAllSettled:
    def test_all_settled_all_success(self):
        f1 = Future.resolve(1)
        f2 = Future.resolve(2)
        f3 = Future.resolve(3)
        combined = Future.allSettled([f1, f2, f3])
        results = combined.value
        assert len(results) == 3
        assert all(r.status == "fulfilled" for r in results)
        assert results[0].value == 1
        assert results[1].value == 2
        assert results[2].value == 3

    def test_all_settled_all_failure(self):
        f1 = Future.reject(RuntimeError("e1"))
        f2 = Future.reject(ValueError("e2"))
        combined = Future.allSettled([f1, f2])
        results = combined.value
        assert len(results) == 2
        assert all(r.status == "rejected" for r in results)
        assert isinstance(results[0].reason, RuntimeError)
        assert isinstance(results[1].reason, ValueError)

    def test_all_settled_mixed(self):
        f1 = Future.resolve(1)
        f2 = Future.reject(RuntimeError("fail"))
        f3 = Future.resolve(3)
        combined = Future.allSettled([f1, f2, f3])
        results = combined.value
        assert len(results) == 3
        assert results[0].status == "fulfilled"
        assert results[0].value == 1
        assert results[1].status == "rejected"
        assert isinstance(results[1].reason, RuntimeError)
        assert results[2].status == "fulfilled"
        assert results[2].value == 3

    def test_all_settled_empty_list(self):
        combined = Future.allSettled([])
        assert combined.state == FutureState.FULFILLED
        assert combined.value == []

    def test_all_settled_with_pending(self):
        f1 = Future()
        f2 = Future()
        combined = Future.allSettled([f1, f2])
        assert combined.state == FutureState.PENDING

        f1._fulfill("a")
        assert combined.state == FutureState.PENDING

        f2._reject(ValueError("bad"))
        results = combined.value
        assert len(results) == 2
        assert results[0].status == "fulfilled"
        assert results[0].value == "a"
        assert results[1].status == "rejected"
        assert isinstance(results[1].reason, ValueError)

    def test_all_settled_preserves_order(self):
        f1 = Future()
        f2 = Future()
        f3 = Future()
        combined = Future.allSettled([f1, f2, f3])

        f2._fulfill("second")
        f1._fulfill("first")
        f3._fulfill("third")

        results = combined.value
        assert results[0].value == "first"
        assert results[1].value == "second"
        assert results[2].value == "third"

    def test_all_settled_result_class_methods(self):
        success = SettledResult.fulfilled(42)
        assert success.status == "fulfilled"
        assert success.value == 42
        assert success.reason is None

        fail = SettledResult.rejected(RuntimeError("oops"))
        assert fail.status == "rejected"
        assert fail.value is None
        assert isinstance(fail.reason, RuntimeError)


class TestRaceCombinator:
    def test_race_first_success_wins(self):
        f1 = Future.resolve("fast")
        f2 = Future()
        combined = Future.race([f1, f2])
        assert combined.value == "fast"

    def test_race_first_failure_wins(self):
        f1 = Future.reject(RuntimeError("fast fail"))
        f2 = Future()
        combined = Future.race([f1, f2])
        assert combined.state == FutureState.REJECTED
        assert isinstance(combined.reason, RuntimeError)

    def test_race_empty_list_raises(self):
        with pytest.raises(ValueError, match="race requires at least one Future"):
            Future.race([])

    def test_race_single_future_success(self):
        f = Future.resolve("only")
        combined = Future.race([f])
        assert combined.value == "only"

    def test_race_single_future_failure(self):
        f = Future.reject(RuntimeError("solo fail"))
        combined = Future.race([f])
        assert combined.state == FutureState.REJECTED

    def test_race_with_pending(self):
        f1 = Future()
        f2 = Future()
        combined = Future.race([f1, f2])
        assert combined.state == FutureState.PENDING

        f1._fulfill("winner")
        assert combined.value == "winner"

        f2._fulfill("loser")
        assert combined.value == "winner"

    def test_race_later_results_ignored(self):
        f1 = Future()
        f2 = Future()
        combined = Future.race([f1, f2])

        f1._fulfill("first")
        assert combined.value == "first"

        f2._reject(RuntimeError("too late"))
        assert combined.value == "first"
        assert combined.state == FutureState.FULFILLED
