from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from .exceptions import ShortCircuitError


@dataclass
class Request:
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None

    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class RequestContext:
    def __init__(self, request: Request) -> None:
        self._request: Request = request
        self._response: Optional[Response] = None
        self._data: Dict[str, Any] = {}
        self._short_circuited: bool = False
        self._short_circuit_by: Optional[str] = None

    @property
    def request(self) -> Request:
        return self._request

    @property
    def response(self) -> Optional[Response]:
        return self._response

    @response.setter
    def response(self, value: Response) -> None:
        self._response = value

    @property
    def short_circuited(self) -> bool:
        return self._short_circuited

    @property
    def short_circuit_by(self) -> Optional[str]:
        return self._short_circuit_by

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def has(self, key: str) -> bool:
        return key in self._data

    def remove(self, key: str) -> Any:
        return self._data.pop(key, None)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def short_circuit(self, interceptor_name: str, response: Optional[Response] = None) -> None:
        self._short_circuited = True
        self._short_circuit_by = interceptor_name
        if response is not None:
            self._response = response
        raise ShortCircuitError(interceptor_name=interceptor_name, response=self._response)


@runtime_checkable
class Interceptor(Protocol):
    name: str

    def before_request(self, ctx: RequestContext) -> None: ...

    def after_request(self, ctx: RequestContext) -> None: ...


Handler = Callable[[RequestContext], Response]


class BaseInterceptor:
    name: str = "base"

    def before_request(self, ctx: RequestContext) -> None:
        pass

    def after_request(self, ctx: RequestContext) -> None:
        pass
