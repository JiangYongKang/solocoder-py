from __future__ import annotations

from typing import List

import pytest

from solocoder_py.interceptor import (
    InterceptorChain,
    InterceptorError,
    Request,
    RequestContext,
    Response,
    ShortCircuitError,
)
from tests.interceptor.conftest import (
    ContextWritingInterceptor,
    ExceptionInterceptor,
    RecordingInterceptor,
    ShortCircuitInterceptor,
)


class TestInterceptorChainManagement:
    def test_empty_chain_size(self):
        chain = InterceptorChain()
        assert chain.size == 0

    def test_chain_initialized_with_interceptors(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain = InterceptorChain(interceptors=[itc1, itc2])
        assert chain.size == 2

    def test_add_last(self):
        chain = InterceptorChain()
        itc1 = RecordingInterceptor("first")
        itc2 = RecordingInterceptor("second")
        chain.add_last(itc1)
        chain.add_last(itc2)
        assert chain.size == 2
        assert chain.get(0).name == "first"
        assert chain.get(1).name == "second"

    def test_add_first(self):
        chain = InterceptorChain()
        itc1 = RecordingInterceptor("first")
        itc2 = RecordingInterceptor("second")
        chain.add_last(itc1)
        chain.add_first(itc2)
        assert chain.get(0).name == "second"
        assert chain.get(1).name == "first"

    def test_add_at_index(self):
        chain = InterceptorChain()
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        itc3 = RecordingInterceptor("c")
        chain.add_last(itc1)
        chain.add_last(itc3)
        chain.add(itc2, index=1)
        assert chain.size == 3
        assert chain.get(0).name == "a"
        assert chain.get(1).name == "b"
        assert chain.get(2).name == "c"

    def test_add_at_invalid_index_raises(self):
        chain = InterceptorChain()
        itc = RecordingInterceptor("a")
        with pytest.raises(IndexError):
            chain.add(itc, index=5)

    def test_remove(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain = InterceptorChain(interceptors=[itc1, itc2])
        assert chain.remove(itc1) is True
        assert chain.size == 1
        assert chain.get(0).name == "b"

    def test_remove_nonexistent_returns_false(self):
        chain = InterceptorChain()
        itc = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain.add_last(itc)
        assert chain.remove(itc2) is False

    def test_remove_at(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        itc3 = RecordingInterceptor("c")
        chain = InterceptorChain(interceptors=[itc1, itc2, itc3])
        removed = chain.remove_at(1)
        assert removed.name == "b"
        assert chain.size == 2
        assert chain.get(0).name == "a"
        assert chain.get(1).name == "c"

    def test_remove_at_invalid_index_raises(self):
        chain = InterceptorChain()
        with pytest.raises(IndexError):
            chain.remove_at(0)

    def test_remove_by_name(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain = InterceptorChain(interceptors=[itc1, itc2])
        removed = chain.remove_by_name("a")
        assert removed is not None
        assert removed.name == "a"
        assert chain.size == 1

    def test_remove_by_name_nonexistent_returns_none(self):
        chain = InterceptorChain()
        assert chain.remove_by_name("nonexistent") is None

    def test_clear(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain = InterceptorChain(interceptors=[itc1, itc2])
        chain.clear()
        assert chain.size == 0

    def test_contains(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        chain = InterceptorChain(interceptors=[itc1])
        assert chain.contains(itc1) is True
        assert chain.contains(itc2) is False

    def test_contains_name(self):
        itc = RecordingInterceptor("a")
        chain = InterceptorChain(interceptors=[itc])
        assert chain.contains_name("a") is True
        assert chain.contains_name("b") is False

    def test_index_of(self):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        itc3 = RecordingInterceptor("c")
        chain = InterceptorChain(interceptors=[itc1, itc2, itc3])
        assert chain.index_of(itc1) == 0
        assert chain.index_of(itc2) == 1
        assert chain.index_of(itc3) == 2
        assert chain.index_of(RecordingInterceptor("d")) == -1

    def test_get_invalid_index_raises(self):
        chain = InterceptorChain()
        with pytest.raises(IndexError):
            chain.get(0)

    def test_interceptors_returns_copy(self):
        itc1 = RecordingInterceptor("a")
        chain = InterceptorChain(interceptors=[itc1])
        result = chain.interceptors
        result.append(RecordingInterceptor("b"))
        assert chain.size == 1


class TestEmptyChain:
    def test_empty_chain_request_reaches_handler(
        self,
        empty_chain: InterceptorChain,
        sample_request: Request,
        default_handler,
    ):
        response = empty_chain.execute(sample_request, default_handler)
        assert response.status_code == 200
        assert response.body == "OK"
        assert response.headers.get("X-Handler") == "called"


class TestSingleInterceptor:
    def test_single_interceptor_before_and_after(
        self,
        single_interceptor_chain: tuple[InterceptorChain, RecordingInterceptor],
        sample_request: Request,
        default_handler,
    ):
        chain, itc = single_interceptor_chain
        response = chain.execute(sample_request, default_handler)
        assert itc.before_called is True
        assert itc.after_called is True
        assert response.status_code == 200

    def test_single_interceptor_execution_order(
        self,
        single_interceptor_chain: tuple[InterceptorChain, RecordingInterceptor],
        sample_request: Request,
        default_handler,
    ):
        chain, itc = single_interceptor_chain
        response = chain.execute(sample_request, default_handler)
        assert itc.call_order == ["auth:before", "auth:after"]


class TestMultipleInterceptorsNormalFlow:
    def test_three_interceptors_order(
        self,
        three_interceptor_chain: tuple[InterceptorChain, List[RecordingInterceptor]],
        sample_request: Request,
        default_handler,
    ):
        chain, interceptors = three_interceptor_chain
        response = chain.execute(sample_request, default_handler)

        for itc in interceptors:
            assert itc.before_called is True
            assert itc.after_called is True
        assert response.status_code == 200

    def test_three_interceptors_before_order(
        self,
        sample_request: Request,
        default_handler,
    ):
        from solocoder_py.interceptor.models import BaseInterceptor

        shared_order: List[str] = []

        class SharedRecordingInterceptor(BaseInterceptor):
            def __init__(self, name: str) -> None:
                self.name = name

            def before_request(self, ctx: RequestContext) -> None:
                shared_order.append(f"{self.name}:before")

            def after_request(self, ctx: RequestContext) -> None:
                shared_order.append(f"{self.name}:after")

        itc1 = SharedRecordingInterceptor("first")
        itc2 = SharedRecordingInterceptor("second")
        itc3 = SharedRecordingInterceptor("third")
        chain = InterceptorChain(interceptors=[itc1, itc2, itc3])
        chain.execute(sample_request, default_handler)

        assert shared_order == [
            "first:before",
            "second:before",
            "third:before",
            "third:after",
            "second:after",
            "first:after",
        ]


class TestContextPropagation:
    def test_context_data_written_and_read(
        self,
        sample_request: Request,
        default_handler,
    ):
        ctx_writer = ContextWritingInterceptor("writer", "trace_id", "trace-123")
        chain = InterceptorChain(interceptors=[ctx_writer])

        received_ctx = {}

        def reading_handler(ctx: RequestContext) -> Response:
            received_ctx["trace_id"] = ctx.get("trace_id")
            received_ctx["writer_before"] = ctx.get("writer_before")
            return Response(status_code=200)

        chain.execute(sample_request, reading_handler)
        assert received_ctx["trace_id"] == "trace-123"

    def test_context_isolation_between_requests(
        self,
        sample_request: Request,
        default_handler,
    ):
        counter = {"count": 0}

        class CountingInterceptor:
            name = "counter"

            def before_request(self, ctx: RequestContext) -> None:
                counter["count"] += 1
                ctx.set("request_num", counter["count"])

            def after_request(self, ctx: RequestContext) -> None:
                pass

        chain = InterceptorChain(interceptors=[CountingInterceptor()])

        seen = []

        def capturing_handler(ctx: RequestContext) -> Response:
            seen.append(ctx.get("request_num"))
            return Response(status_code=200, body=str(ctx.get("request_num")))

        chain.execute(sample_request, capturing_handler)
        chain.execute(sample_request, capturing_handler)

        assert seen == [1, 2]
        assert counter["count"] == 2

    def test_context_dict_methods(
        self,
        sample_request: Request,
    ):
        ctx = RequestContext(request=sample_request)

        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"
        assert ctx.has("key1") is True
        assert ctx.has("key2") is False
        assert "key1" in ctx
        assert ctx["key1"] == "value1"
        ctx["key2"] = "value2"
        assert ctx["key2"] == "value2"
        assert ctx.remove("key1") == "value1"
        assert ctx.has("key1") is False
        assert ctx.to_dict() == {"key2": "value2"}
        assert ctx.request is sample_request


class TestShortCircuit:
    def test_short_circuit_stops_chain(
        self,
        sample_request: Request,
        default_handler,
    ):
        itc_before = RecordingInterceptor("before_sc")
        short_circuit = ShortCircuitInterceptor(
            "sc",
            Response(status_code=403, body="Blocked")
        )
        itc_after = RecordingInterceptor("after_sc")

        handler_called = {"called": False}

        def handler(ctx: RequestContext) -> Response:
            handler_called["called"] = True
            return Response(status_code=200)

        chain = InterceptorChain(interceptors=[itc_before, short_circuit, itc_after])
        response = chain.execute(sample_request, handler)

        assert response.status_code == 403
        assert response.body == "Blocked"
        assert handler_called["called"] is False
        assert itc_before.before_called is True
        assert itc_before.after_called is True
        assert itc_after.before_called is False
        assert itc_after.after_called is False
        assert short_circuit.after_called is True

    def test_short_circuit_second_of_three(
        self,
        sample_request: Request,
        default_handler,
    ):
        itc1 = RecordingInterceptor("first")
        sc = ShortCircuitInterceptor("sc_middle")
        itc3 = RecordingInterceptor("third")
        handler_called = {"called": False}

        def handler(ctx: RequestContext) -> Response:
            handler_called["called"] = True
            return Response(status_code=200)

        chain = InterceptorChain(interceptors=[itc1, sc, itc3])
        response = chain.execute(sample_request, handler)

        assert itc1.before_called is True
        assert itc1.after_called is True
        assert sc.after_called is True
        assert itc3.before_called is False
        assert itc3.after_called is False
        assert handler_called["called"] is False
        assert response.status_code == 403

    def test_short_circuit_context_flags(
        self,
        sample_request: Request,
    ):
        sc = ShortCircuitInterceptor("sc_interceptor")
        chain = InterceptorChain(interceptors=[sc])

        captured_ctx = {}

        def handler(ctx: RequestContext) -> Response:
            return Response(status_code=200)

        chain.execute(sample_request, handler)
        assert True
        captured = {}

        class CaptureContextInterceptor:
            name = "capture"

            def before_request(self, ctx: RequestContext) -> None:
                pass

            def after_request(self, ctx: RequestContext) -> None:
                captured["short_circuited"] = ctx.short_circuited
                captured["short_circuit_by"] = ctx.short_circuit_by

        itc_capture = CaptureContextInterceptor()
        sc2 = ShortCircuitInterceptor("sc2")
        chain2 = InterceptorChain(interceptors=[itc_capture, sc2])
        chain2.execute(sample_request, lambda ctx: Response(status_code=200))
        assert captured["short_circuited"] is True
        assert captured["short_circuit_by"] == "sc2"


class TestExceptionHandling:
    def test_interceptor_exception_stops_chain(
        self,
        sample_request: Request,
    ):
        itc_before = RecordingInterceptor("before")
        exc_itc = ExceptionInterceptor("exc", ValueError("boom"))
        itc_after = RecordingInterceptor("after")
        handler_called = {"called": False}

        def handler(ctx: RequestContext) -> Response:
            handler_called["called"] = True
            return Response(status_code=200)

        chain = InterceptorChain(interceptors=[itc_before, exc_itc, itc_after])

        with pytest.raises(ValueError, match="boom"):
            chain.execute(sample_request, handler)

        assert itc_before.before_called is True
        assert itc_before.after_called is True
        assert itc_after.before_called is False
        assert itc_after.after_called is False
        assert handler_called["called"] is False
        assert exc_itc.after_called is False

    def test_exception_after_called_only_for_executed_before(
        self,
        sample_request: Request,
    ):
        itc1 = RecordingInterceptor("first")
        itc2 = RecordingInterceptor("second")
        exc = ExceptionInterceptor("exc", RuntimeError("fail"))
        itc3 = RecordingInterceptor("third")
        itc4 = RecordingInterceptor("fourth")
        handler_called = {"called": False}

        def handler(ctx: RequestContext) -> Response:
            handler_called["called"] = True
            return Response(status_code=200)

        chain = InterceptorChain(interceptors=[itc1, itc2, exc, itc3, itc4])

        with pytest.raises(RuntimeError):
            chain.execute(sample_request, handler)

        assert itc1.after_called is True
        assert itc2.after_called is True
        assert exc.after_called is False
        assert itc3.before_called is False
        assert itc3.after_called is False
        assert itc4.before_called is False
        assert itc4.after_called is False
        assert handler_called["called"] is False

    def test_handler_exception_propagates(
        self,
        sample_request: Request,
    ):
        itc = RecordingInterceptor("auth")

        def failing_handler(ctx: RequestContext) -> Response:
            raise TypeError("handler error")

        chain = InterceptorChain(interceptors=[itc])

        with pytest.raises(TypeError, match="handler error"):
            chain.execute(sample_request, failing_handler)

        assert itc.before_called is True
        assert itc.after_called is True

    def test_context_state_preserved_after_exception(
        self,
        sample_request: Request,
    ):
        writer = ContextWritingInterceptor("writer", "user_id", "user-456")
        exc = ExceptionInterceptor("fail", ValueError("oops"))

        chain = InterceptorChain(interceptors=[writer, exc])

        captured_after = {}

        class CaptureAfterInterceptor:
            name = "capture_after"

            def before_request(self, ctx: RequestContext) -> None:
                pass

            def after_request(self, ctx: RequestContext) -> None:
                captured_after["user_id"] = ctx.get("user_id")

        capture_after = CaptureAfterInterceptor()
        chain2 = InterceptorChain(interceptors=[writer, capture_after, exc])

        with pytest.raises(ValueError):
            chain2.execute(sample_request, lambda ctx: Response(status_code=200))

        assert capture_after.after_called if hasattr(capture_after, "after_called") else True
        assert captured_after["user_id"] == "user-456"

    def test_exception_in_after_request_does_not_affect_other_after(
        self,
        sample_request: Request,
    ):
        itc1 = RecordingInterceptor("first")

        class BadAfterInterceptor:
            name = "bad_after"

            def before_request(self, ctx: RequestContext) -> None:
                pass

            def after_request(self, ctx: RequestContext) -> None:
                raise RuntimeError("after failed")

        itc2 = RecordingInterceptor("third")
        handler_called = {"called": False}

        def handler(ctx: RequestContext) -> Response:
            handler_called["called"] = True
            return Response(status_code=200)

        chain = InterceptorChain(interceptors=[itc1, BadAfterInterceptor(), itc2])

        response = chain.execute(sample_request, handler)
        assert response.status_code == 200
        assert handler_called["called"] is True
        assert itc1.before_called is True
        assert itc1.after_called is True
        assert itc2.before_called is True
        assert itc2.after_called is True


class TestResponseObject:
    def test_response_defaults(self):
        resp = Response()
        assert resp.status_code == 200
        assert resp.headers == {}
        assert resp.body is None
        assert resp.is_success() is True

    def test_response_failure_status(self):
        resp = Response(status_code=500)
        assert resp.is_success() is False

    def test_response_with_body_and_headers(self):
        resp = Response(status_code=201, body={"id": 1}, headers={"Location": "/x"})
        assert resp.status_code == 201
        assert resp.body == {"id": 1}
        assert resp.headers["Location"] == "/x"


class TestEdgeCases:
    def test_short_circuit_no_response_provided(
        self,
        sample_request: Request,
    ):
        sc = ShortCircuitInterceptor("sc_none", response=None)
        chain = InterceptorChain(interceptors=[sc])
        response = chain.execute(sample_request, lambda ctx: Response(status_code=200))
        assert response.status_code == 403

    def test_very_long_chain_order(
        self,
        sample_request: Request,
        default_handler,
    ):
        num = 10
        interceptors = [RecordingInterceptor(f"itc_{i}") for i in range(num)]
        chain = InterceptorChain(interceptors=interceptors)
        response = chain.execute(sample_request, default_handler)
        assert response.status_code == 200
        for i, itc in enumerate(interceptors):
            assert itc.before_called is True
            assert itc.after_called is True
            assert itc.call_order == [f"itc_{i}:before", f"itc_{i}:after"]

    def test_insert_middle_preserves_order(
        self,
        sample_request: Request,
        default_handler,
    ):
        itc1 = RecordingInterceptor("a")
        itc2 = RecordingInterceptor("b")
        itc3 = RecordingInterceptor("c")
        chain = InterceptorChain(interceptors=[itc1, itc3])
        chain.add(itc2, index=1)
        chain.execute(sample_request, default_handler)
        assert chain.size == 3
        assert chain.get(0).name == "a"
        assert chain.get(1).name == "b"
        assert chain.get(2).name == "c"
