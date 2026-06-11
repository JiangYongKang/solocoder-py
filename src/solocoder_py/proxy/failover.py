from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .clock import Clock, SystemClock
from .exceptions import AllUpstreamsFailedError, UpstreamError
from .models import ProxyConfig, UpstreamServer, UpstreamStatus


@dataclass
class FailoverResult:
    upstream: UpstreamServer
    failed_over: bool
    previous_upstream: Optional[UpstreamServer] = None


class UpstreamManager:
    def __init__(
        self,
        upstreams: List[UpstreamServer],
        config: Optional[ProxyConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if not upstreams:
            raise UpstreamError("At least one upstream server is required")
        self._upstreams = list(upstreams)
        self._config = config or ProxyConfig()
        self._clock = clock or SystemClock()
        self._current_index = 0
        self._primary_index = self._find_primary_index()
        self._last_failback_check = 0.0

    def _find_primary_index(self) -> int:
        for i, upstream in enumerate(self._upstreams):
            if upstream.is_primary:
                return i
        return 0

    def _is_recovered(self, upstream: UpstreamServer) -> bool:
        if upstream.status != UpstreamStatus.UNHEALTHY:
            return True
        if upstream.last_failure_time is None:
            return True
        elapsed = self._clock.now() - upstream.last_failure_time
        return elapsed >= self._config.failure_timeout

    def _should_failback(self) -> bool:
        if not self._config.auto_failback:
            return False
        if self._current_index == self._primary_index:
            return False
        elapsed = self._clock.now() - self._last_failback_check
        if elapsed < self._config.failback_interval:
            return False
        primary = self._upstreams[self._primary_index]
        return self._is_recovered(primary)

    def _check_failback(self) -> None:
        if self._should_failback():
            primary = self._upstreams[self._primary_index]
            primary.mark_healthy(self._clock.now())
            self._current_index = self._primary_index
            self._last_failback_check = self._clock.now()

    def get_upstream(self, exclude: Optional[set] = None) -> FailoverResult:
        self._check_failback()

        exclude = exclude or set()
        start_index = self._current_index
        failed_over = False
        previous_upstream: Optional[UpstreamServer] = None

        for i in range(len(self._upstreams)):
            idx = (start_index + i) % len(self._upstreams)
            upstream = self._upstreams[idx]

            if upstream.address in exclude:
                continue

            if self._is_recovered(upstream):
                if idx != start_index:
                    failed_over = True
                    previous_upstream = self._upstreams[start_index]
                self._current_index = idx
                return FailoverResult(
                    upstream=upstream,
                    failed_over=failed_over,
                    previous_upstream=previous_upstream,
                )

        raise AllUpstreamsFailedError("All upstream servers are unavailable")

    def mark_failure(self, upstream: UpstreamServer) -> None:
        timestamp = self._clock.now()
        upstream.mark_failed(timestamp)
        if upstream.failure_count >= self._config.max_failures:
            upstream.status = UpstreamStatus.UNHEALTHY

    def mark_success(self, upstream: UpstreamServer) -> None:
        timestamp = self._clock.now()
        upstream.mark_healthy(timestamp)

    def get_healthy_upstreams(self) -> List[UpstreamServer]:
        return [u for u in self._upstreams if self._is_recovered(u)]

    def get_unhealthy_upstreams(self) -> List[UpstreamServer]:
        return [u for u in self._upstreams if not self._is_recovered(u)]

    @property
    def current_upstream(self) -> UpstreamServer:
        return self._upstreams[self._current_index]

    @property
    def upstreams(self) -> List[UpstreamServer]:
        return list(self._upstreams)

    @property
    def primary_upstream(self) -> UpstreamServer:
        return self._upstreams[self._primary_index]
