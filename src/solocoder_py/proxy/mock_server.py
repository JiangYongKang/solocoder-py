from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import UpstreamError
from .models import Request, Response
from .rewriter import ResponseRewriter


@dataclass
class MockRoute:
    method: Optional[str] = None
    path_pattern: Optional[str] = None
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    delay: float = 0.0
    should_fail: bool = False
    failure_probability: float = 0.0
    handler: Optional[Callable[[Request], Response]] = None


class MockUpstreamServer:
    def __init__(self, name: str, host: str, port: int) -> None:
        self._name = name
        self._host = host
        self._port = port
        self._routes: List[MockRoute] = []
        self._lock = threading.RLock()
        self._request_count = 0
        self._response_count = 0
        self._available = True
        self._unavailable_until: float = 0.0
        self._default_response = Response(
            status_code=200,
            headers={"Content-Type": "text/plain"},
            body=b"OK",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return f"{self._host}:{self._port}"

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def response_count(self) -> int:
        return self._response_count

    def add_route(
        self,
        method: Optional[str] = None,
        path_pattern: Optional[str] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        body: bytes = b"",
        delay: float = 0.0,
        should_fail: bool = False,
        failure_probability: float = 0.0,
        handler: Optional[Callable[[Request], Response]] = None,
    ) -> "MockUpstreamServer":
        with self._lock:
            self._routes.append(
                MockRoute(
                    method=method,
                    path_pattern=path_pattern,
                    status_code=status_code,
                    headers=dict(headers or {}),
                    body=body,
                    delay=delay,
                    should_fail=should_fail,
                    failure_probability=failure_probability,
                    handler=handler,
                )
            )
        return self

    def set_unavailable(self, duration: float = 0.0) -> None:
        with self._lock:
            self._available = False
            if duration > 0:
                self._unavailable_until = time.monotonic() + duration

    def set_available(self) -> None:
        with self._lock:
            self._available = True
            self._unavailable_until = 0.0

    def set_default_response(self, response: Response) -> None:
        self._default_response = response.copy()

    def _check_available(self) -> None:
        with self._lock:
            if not self._available:
                if self._unavailable_until > 0:
                    if time.monotonic() < self._unavailable_until:
                        raise UpstreamError(f"Server {self._name} is unavailable")
                    else:
                        self._available = True
                        self._unavailable_until = 0.0
                else:
                    raise UpstreamError(f"Server {self._name} is unavailable")

    def _match_route(self, request: Request) -> Optional[MockRoute]:
        with self._lock:
            for route in reversed(self._routes):
                if route.method and request.method != route.method:
                    continue
                if route.path_pattern:
                    if route.path_pattern not in request.url:
                        continue
                return route
        return None

    def handle_request(self, request: Request) -> Response:
        self._check_available()

        with self._lock:
            self._request_count += 1

        route = self._match_route(request)

        if route and route.should_fail:
            raise UpstreamError(f"Route failure on {self._name}")

        if route and route.failure_probability > 0:
            import random

            if random.random() < route.failure_probability:
                raise UpstreamError(f"Random failure on {self._name}")

        if route and route.delay > 0:
            time.sleep(route.delay)

        if route and route.handler:
            response = route.handler(request)
        elif route:
            response = Response(
                status_code=route.status_code,
                headers=dict(route.headers),
                body=route.body,
            )
        else:
            response = self._default_response.copy()

        response.headers.setdefault("X-Upstream-Server", self._name)
        response.headers.setdefault("Content-Length", str(len(response.body)))

        with self._lock:
            self._response_count += 1

        return response

    def reset_stats(self) -> None:
        with self._lock:
            self._request_count = 0
            self._response_count = 0

    def clear_routes(self) -> None:
        with self._lock:
            self._routes.clear()


class MockServerRegistry:
    def __init__(self) -> None:
        self._servers: Dict[str, MockUpstreamServer] = {}
        self._lock = threading.RLock()

    def register(self, server: MockUpstreamServer) -> None:
        with self._lock:
            self._servers[server.address] = server

    def unregister(self, address: str) -> None:
        with self._lock:
            self._servers.pop(address, None)

    def get(self, address: str) -> Optional[MockUpstreamServer]:
        with self._lock:
            return self._servers.get(address)

    def handle(self, address: str, request: Request) -> Response:
        server = self.get(address)
        if server is None:
            raise UpstreamError(f"No mock server registered at {address}")
        return server.handle_request(request)

    def set_server_unavailable(self, address: str, duration: float = 0.0) -> None:
        server = self.get(address)
        if server:
            server.set_unavailable(duration)

    def set_server_available(self, address: str) -> None:
        server = self.get(address)
        if server:
            server.set_available()

    def clear_all(self) -> None:
        with self._lock:
            self._servers.clear()
