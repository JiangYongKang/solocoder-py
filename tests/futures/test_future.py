from __future__ import annotations

import pytest

from solocoder_py.futures import Future, FutureState, FutureNotReadyError, FutureAlreadySettledError


class TestFutureCreation:
    def test_initial_state_is_pending(self):
        f = Future()
        assert f.state == FutureState.PENDING
        assert not f.is_settled

    def test_value_raises_not_ready_when_pending(self):
        f = Future()
        with pytest.raises(FutureNotReadyError):
            _ = f.value

    def test_reason_raises_not_ready_when_pending(self):
        f = Future()
        with pytest.raises(FutureNotReadyError):
            _ = f.reason


class TestFutureResolve:
    def test_resolve_creates_fulfilled_future(self):
        f = Future.resolve(42)
        assert f.state == FutureState.FULFILLED
        assert f.is_settled
        assert f.value == 42

    def test_resolve_with_none(self):
        f = Future.resolve(None)
        assert f.state == FutureState.FULFILLED
        assert f.value is None

    def test_resolve_with_list(self):
        f = Future.resolve([1, 2, 3])
        assert f.value == [1, 2, 3]

    def test_resolve_with_dict(self):
        f = Future.resolve({"key": "value"})
        assert f.value == {"key": "value"}


class TestFutureReject:
    def test_reject_creates_rejected_future(self):
        err = RuntimeError("something went wrong")
        f = Future.reject(err)
        assert f.state == FutureState.REJECTED
        assert f.is_settled
        assert f.reason is err

    def test_value_raises_when_rejected(self):
        err = ValueError("bad value")
        f = Future.reject(err)
        with pytest.raises(ValueError, match="bad value"):
            _ = f.value

    def test_reject_with_custom_exception(self):
        class CustomError(Exception):
            pass

        err = CustomError("custom")
        f = Future.reject(err)
        assert isinstance(f.reason, CustomError)


class TestThenChaining:
    def test_then_passes_value_through_chain(self):
        f = Future.resolve(1)
        result = f.then(lambda x: x + 1).then(lambda x: x * 2)
        assert result.value == 4

    def test_then_returns_new_future(self):
        f = Future.resolve(1)
        f2 = f.then(lambda x: x + 1)
        assert f2 is not f
        assert isinstance(f2, Future)

    def test_then_with_pending_future(self):
        f = Future()
        result = f.then(lambda x: x * 2)
        assert result.state == FutureState.PENDING

        f._fulfill(5)
        assert result.value == 10

    def test_then_chain_multiple_steps(self):
        f = Future.resolve("hello")
        result = (
            f.then(lambda s: s.upper())
             .then(lambda s: s + " WORLD")
             .then(lambda s: len(s))
        )
        assert result.value == 11

    def test_then_callback_returns_none(self):
        f = Future.resolve(42)
        result = f.then(lambda x: None)
        assert result.value is None

    def test_then_does_not_flatten_returned_future(self):
        f = Future.resolve(1)
        inner = Future.resolve(99)
        result = f.then(lambda x: inner)
        assert result.value is inner
        assert isinstance(result.value, Future)

    def test_then_vs_compose_difference(self):
        f = Future.resolve(1)
        inner = Future.resolve(99)

        then_result = f.then(lambda x: inner)
        assert then_result.value is inner

        compose_result = f.compose(lambda x: inner)
        assert compose_result.value == 99


class TestCompose:
    def test_compose_flattens_nested_future(self):
        f = Future.resolve(1)
        result = f.compose(lambda x: Future.resolve(x + 10))
        assert result.value == 11

    def test_compose_chain(self):
        f = Future.resolve(2)
        result = (
            f.compose(lambda x: Future.resolve(x * 3))
             .compose(lambda x: Future.resolve(x + 5))
        )
        assert result.value == 11

    def test_compose_with_pending_future(self):
        outer = Future()
        inner = Future()

        result = outer.compose(lambda x: inner)
        assert result.state == FutureState.PENDING

        outer._fulfill("start")
        assert result.state == FutureState.PENDING

        inner._fulfill("end")
        assert result.value == "end"

    def test_compose_callback_must_return_future(self):
        f = Future.resolve(1)
        result = f.compose(lambda x: "not a future")
        assert result.state == FutureState.REJECTED
        assert isinstance(result.reason, TypeError)


class TestCatch:
    def test_catch_catches_exception(self):
        err = RuntimeError("boom")
        f = Future.reject(err)
        result = f.catch(lambda e: "recovered")
        assert result.value == "recovered"

    def test_catch_allows_chain_to_continue(self):
        f = Future.reject(RuntimeError("fail"))
        result = (
            f.catch(lambda e: 100)
             .then(lambda x: x + 1)
        )
        assert result.value == 101

    def test_catch_does_not_fire_on_success(self):
        f = Future.resolve(42)
        result = f.catch(lambda e: 0)
        assert result.value == 42

    def test_catch_with_pending_future(self):
        f = Future()
        result = f.catch(lambda e: "fallback")
        assert result.state == FutureState.PENDING

        f._reject(ValueError("oops"))
        assert result.value == "fallback"

    def test_catch_returns_future_can_continue_chain(self):
        f = Future.reject(RuntimeError("first"))
        result = (
            f.catch(lambda e: Future.resolve("recovered"))
             .then(lambda x: x + "!")
        )
        assert result.value == "recovered!"


class TestExceptionPropagation:
    def test_then_callback_raises_propagates(self):
        f = Future.resolve(1)
        result = f.then(lambda x: (_ for _ in ()).throw(ValueError("oops")))
        assert result.state == FutureState.REJECTED
        assert isinstance(result.reason, ValueError)
        assert str(result.reason) == "oops"

    def test_then_exception_propagates_through_chain(self):
        f = Future.resolve(1)
        result = (
            f.then(lambda x: x + 1)
             .then(lambda x: (_ for _ in ()).throw(RuntimeError("fail")))
             .then(lambda x: x * 2)
        )
        assert result.state == FutureState.REJECTED
        assert isinstance(result.reason, RuntimeError)

    def test_catch_can_recover_from_then_exception(self):
        f = Future.resolve(1)
        result = (
            f.then(lambda x: (_ for _ in ()).throw(ValueError("bad")))
             .catch(lambda e: "fixed")
        )
        assert result.value == "fixed"

    def test_catch_raises_again_propagates(self):
        f = Future.reject(RuntimeError("first"))
        result = f.catch(lambda e: (_ for _ in ()).throw(ValueError("second")))
        assert result.state == FutureState.REJECTED
        assert isinstance(result.reason, ValueError)
        assert str(result.reason) == "second"

    def test_catch_after_catch(self):
        f = Future.reject(RuntimeError("first"))
        result = (
            f.catch(lambda e: (_ for _ in ()).throw(ValueError("second")))
             .catch(lambda e: "finally recovered")
        )
        assert result.value == "finally recovered"


class TestCallbackAfterSettlement:
    def test_then_after_fulfillment_executes_immediately(self):
        f = Future.resolve(99)
        results = []
        f.then(lambda x: results.append(x))
        assert results == [99]

    def test_catch_after_rejection_executes_immediately(self):
        f = Future.reject(RuntimeError("fail"))
        errors = []
        f.catch(lambda e: errors.append(str(e)))
        assert errors == ["fail"]

    def test_then_after_rejection_propagates(self):
        f = Future.reject(ValueError("bad"))
        result = f.then(lambda x: x + 1)
        assert result.state == FutureState.REJECTED
        assert isinstance(result.reason, ValueError)

    def test_catch_after_fulfillment_passes_through(self):
        f = Future.resolve(42)
        result = f.catch(lambda e: 0)
        assert result.value == 42


class TestMultipleCallbacks:
    def test_multiple_then_on_same_future(self):
        f = Future()
        results = []

        f.then(lambda x: results.append(("a", x)))
        f.then(lambda x: results.append(("b", x)))
        f.then(lambda x: results.append(("c", x)))

        f._fulfill(42)
        assert results == [("a", 42), ("b", 42), ("c", 42)]

    def test_multiple_catch_on_same_future(self):
        f = Future()
        errors = []

        f.catch(lambda e: errors.append(("a", str(e))))
        f.catch(lambda e: errors.append(("b", str(e))))

        f._reject(RuntimeError("boom"))
        assert errors == [("a", "boom"), ("b", "boom")]

    def test_callback_order_preserved(self):
        f = Future()
        order = []

        f.then(lambda x: order.append(1))
        f.then(lambda x: order.append(2))
        f.then(lambda x: order.append(3))

        f._fulfill("x")
        assert order == [1, 2, 3]
