from __future__ import annotations

from typing import List

import pytest

from solocoder_py.interceptor import (
    InterceptorChain,
    Request,
    RequestContext,
    Response,
)
from solocoder_py.interceptor.models import BaseInterceptor


class RecordingInterceptor(BaseInterceptor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.before_called: bool = False
        self.after_called: bool = False
        self.call_order: List[str] = []

    def before_request(self, ctx: RequestContext) -> None:
        self.before_called = True
        self.call_order.append(f"{self.name}:before")
        ctx.set(f"{self.name}_before", True)

    def after_request(self, ctx: RequestContext) -> None:
        self.after_called = True
        self.call_order.append(f"{self.name}:after")
        ctx.set(f"{self.name}_after", True)


class ShortCircuitInterceptor(BaseInterceptor):
    def __init__(
        self,
        name: str,
        response: Response | None = None,
    ) -> None:
        self.name = name
        self.after_called: bool = False
        self.response = response or Response(status_code=403, body="Forbidden")

    def before_request(self, ctx: RequestContext) -> None:
        ctx.short_circuit(self.name, self.response)

    def after_request(self, ctx: RequestContext) -> None:
        self.after_called = True


class ExceptionInterceptor(BaseInterceptor):
    def __init__(self, name: str, exc: Exception) -> None:
        self.name = name
        self.after_called: bool = False
        self.exc = exc

    def before_request(self, ctx: RequestContext) -> None:
        raise self.exc

    def after_request(self, ctx: RequestContext) -> None:
        self.after_called = True


class ContextWritingInterceptor(BaseInterceptor):
    def __init__(self, name: str, key: str, value: object) -> None:
        self.name = name
        self.key = key
        self.value = value
        self.after_called: bool = False

    def before_request(self, ctx: RequestContext) -> None:
        ctx.set(self.key, self.value)

    def after_request(self, ctx: RequestContext) -> None:
        self.after_called = True


@pytest.fixture
def sample_request() -> Request:
    return Request(
        method="GET",
        path="/api/test",
        headers={"Content-Type": "application/json"},
        body=None,
        params={"id": "123"},
    )


@pytest.fixture
def default_handler():
    def handler(ctx: RequestContext) -> Response:
        return Response(status_code=200, body="OK", headers={"X-Handler": "called"})
    return handler


@pytest.fixture
def empty_chain() -> InterceptorChain:
    return InterceptorChain()


@pytest.fixture
def single_interceptor_chain() -> tuple[InterceptorChain, RecordingInterceptor]:
    itc = RecordingInterceptor("auth")
    chain = InterceptorChain(interceptors=[itc])
    return chain, itc


@pytest.fixture
def three_interceptor_chain() -> tuple[InterceptorChain, List[RecordingInterceptor]]:
    itc1 = RecordingInterceptor("first")
    itc2 = RecordingInterceptor("second")
    itc3 = RecordingInterceptor("third")
    chain = InterceptorChain(interceptors=[itc1, itc2, itc3])
    return chain, [itc1, itc2, itc3]
