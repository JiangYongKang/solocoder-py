from __future__ import annotations

import threading
from typing import List, Optional

from .clock import Clock, SystemClock
from .connection_pool import ConnectionPool, PooledConnection
from .exceptions import (
    AllUpstreamsFailedError,
    ConnectionPoolError,
    ProxyError,
    RewriterError,
    UpstreamError,
)
from .failover import UpstreamManager
from .filter import HeaderFilter
from .mock_server import MockServerRegistry
from .models import ProxyConfig, ProxyStats, Request, Response, UpstreamServer
from .rewriter import RewriterChain


class HttpForwardProxy:
    def __init__(
        self,
        upstreams: List[UpstreamServer],
        config: Optional[ProxyConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config or ProxyConfig()
        self._clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._rewriter_chain = RewriterChain()
        self._request_header_filter: Optional[HeaderFilter] = None
        self._response_header_filter: Optional[HeaderFilter] = None
        self._upstream_manager = UpstreamManager(upstreams, self._config, self._clock)
        self._connection_pool = ConnectionPool(self._config, self._clock)
        self._server_registry = MockServerRegistry()
        self._stats = ProxyStats()
        self._closed = False

    def register_mock_server(self, server) -> None:
        self._server_registry.register(server)

    def set_request_header_filter(self, filter: Optional[HeaderFilter]) -> None:
        self._request_header_filter = filter

    def set_response_header_filter(self, filter: Optional[HeaderFilter]) -> None:
        self._response_header_filter = filter

    @property
    def rewriter_chain(self) -> RewriterChain:
        return self._rewriter_chain

    @property
    def upstream_manager(self) -> UpstreamManager:
        return self._upstream_manager

    @property
    def connection_pool(self) -> ConnectionPool:
        return self._connection_pool

    @property
    def stats(self) -> ProxyStats:
        with self._lock:
            return ProxyStats(
                total_requests=self._stats.total_requests,
                forwarded_requests=self._stats.forwarded_requests,
                failed_requests=self._stats.failed_requests,
                failover_count=self._stats.failover_count,
                active_connections=self._connection_pool.get_active_connections(),
                reused_connections=self._stats.reused_connections,
            )

    def _increment_stat(self, name: str) -> None:
        with self._lock:
            current = getattr(self._stats, name, 0)
            setattr(self._stats, name, current + 1)

    def _execute_with_retry(
        self, request: Request, max_connection_retries: int = 2
    ) -> Response:
        last_error: Optional[Exception] = None
        tried_upstreams: set = set()

        while True:
            try:
                failover_result = self._upstream_manager.get_upstream(
                    exclude=tried_upstreams
                )
                if failover_result.failed_over:
                    self._increment_stat("failover_count")

                upstream = failover_result.upstream
                upstream_id = upstream.address

                if upstream_id in tried_upstreams:
                    raise AllUpstreamsFailedError(
                        "All upstream servers have been tried and failed"
                    )

                conn = None
                upstream_failed = False

                try:
                    conn = self._connection_pool.acquire(upstream.address)

                    if conn.reuse_count > 1:
                        self._increment_stat("reused_connections")

                    for attempt in range(max_connection_retries):
                        try:
                            response = self._server_registry.handle(
                                upstream.address, request
                            )
                            self._upstream_manager.mark_success(upstream)
                            self._connection_pool.release(conn)
                            return response
                        except UpstreamError as e:
                            last_error = e
                            if attempt < max_connection_retries - 1:
                                self._connection_pool.invalidate(conn)
                                conn = self._connection_pool.acquire(upstream.address)
                                continue
                            upstream_failed = True
                            break

                    if upstream_failed:
                        if conn:
                            self._connection_pool.invalidate(conn)
                        self._upstream_manager.mark_failure(upstream)
                        tried_upstreams.add(upstream_id)
                        continue

                except ConnectionPoolError as e:
                    if conn:
                        self._connection_pool.invalidate(conn)
                    last_error = e
                    raise

                except Exception as e:
                    if conn:
                        self._connection_pool.release(conn)
                    last_error = e
                    raise

            except AllUpstreamsFailedError as e:
                last_error = e
                raise

        if last_error:
            raise last_error
        raise ProxyError("No response received from any upstream")

    def forward(self, request: Request) -> Response:
        if self._closed:
            raise ProxyError("Proxy is closed")

        self._increment_stat("total_requests")

        try:
            modified_request = self._rewriter_chain.rewrite_request(request)

            if self._request_header_filter:
                modified_request = self._request_header_filter.filter_request_headers(
                    modified_request
                )

            response = self._execute_with_retry(modified_request)

            modified_response = self._rewriter_chain.rewrite_response(
                response, modified_request
            )

            if self._response_header_filter:
                modified_response = self._response_header_filter.filter_response_headers(
                    modified_response
                )

            self._increment_stat("forwarded_requests")
            return modified_response

        except RewriterError:
            self._increment_stat("failed_requests")
            raise

        except UpstreamError:
            self._increment_stat("failed_requests")
            raise

        except Exception:
            self._increment_stat("failed_requests")
            raise

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._connection_pool.close_all()
            self._server_registry.clear_all()

    def __enter__(self) -> "HttpForwardProxy":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
