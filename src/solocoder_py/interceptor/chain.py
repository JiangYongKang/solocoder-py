from __future__ import annotations

from typing import Any, Callable, List, Optional

from .exceptions import InterceptorError, ShortCircuitError
from .models import Handler, Interceptor, Request, RequestContext, Response


class InterceptorChain:
    def __init__(self, interceptors: Optional[List[Interceptor]] = None) -> None:
        self._interceptors: List[Interceptor] = list(interceptors) if interceptors else []

    @property
    def interceptors(self) -> List[Interceptor]:
        return list(self._interceptors)

    @property
    def size(self) -> int:
        return len(self._interceptors)

    def add(self, interceptor: Interceptor, index: Optional[int] = None) -> None:
        if index is None:
            self._interceptors.append(interceptor)
        else:
            if index < 0 or index > len(self._interceptors):
                raise IndexError(
                    f"Index {index} out of range for chain of size {len(self._interceptors)}"
                )
            self._interceptors.insert(index, interceptor)

    def add_first(self, interceptor: Interceptor) -> None:
        self._interceptors.insert(0, interceptor)

    def add_last(self, interceptor: Interceptor) -> None:
        self._interceptors.append(interceptor)

    def remove(self, interceptor: Interceptor) -> bool:
        if interceptor in self._interceptors:
            self._interceptors.remove(interceptor)
            return True
        return False

    def remove_at(self, index: int) -> Interceptor:
        if index < 0 or index >= len(self._interceptors):
            raise IndexError(
                f"Index {index} out of range for chain of size {len(self._interceptors)}"
            )
        return self._interceptors.pop(index)

    def remove_by_name(self, name: str) -> Optional[Interceptor]:
        for i, itc in enumerate(self._interceptors):
            if itc.name == name:
                return self._interceptors.pop(i)
        return None

    def clear(self) -> None:
        self._interceptors.clear()

    def contains(self, interceptor: Interceptor) -> bool:
        return interceptor in self._interceptors

    def contains_name(self, name: str) -> bool:
        return any(itc.name == name for itc in self._interceptors)

    def get(self, index: int) -> Interceptor:
        if index < 0 or index >= len(self._interceptors):
            raise IndexError(
                f"Index {index} out of range for chain of size {len(self._interceptors)}"
            )
        return self._interceptors[index]

    def index_of(self, interceptor: Interceptor) -> int:
        try:
            return self._interceptors.index(interceptor)
        except ValueError:
            return -1

    def execute(self, request: Request, handler: Handler) -> Response:
        ctx = RequestContext(request=request)
        executed: List[Interceptor] = []
        caught_exception: Optional[Exception] = None

        try:
            for itc in self._interceptors:
                try:
                    itc.before_request(ctx)
                    executed.append(itc)
                except ShortCircuitError:
                    executed.append(itc)
                    raise
                except Exception as exc:
                    caught_exception = exc
                    break

            if caught_exception is None and not ctx.short_circuited:
                try:
                    ctx.response = handler(ctx)
                except Exception as exc:
                    caught_exception = exc
        except ShortCircuitError:
            pass

        for itc in reversed(executed):
            try:
                itc.after_request(ctx)
            except Exception:
                pass

        if ctx.response is None:
            ctx.response = Response(status_code=500, body="Internal Server Error")

        if caught_exception is not None:
            raise caught_exception

        return ctx.response
