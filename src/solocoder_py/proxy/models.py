from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import InvalidConfigError


class FilterMode(str, Enum):
    WHITELIST = "WHITELIST"
    BLACKLIST = "BLACKLIST"


class UpstreamStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"


class ConnectionStatus(str, Enum):
    IDLE = "IDLE"
    IN_USE = "IN_USE"
    CLOSED = "CLOSED"


@dataclass
class Request:
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = field(default=b"")
    stream: bool = False

    def copy(self) -> "Request":
        return Request(
            method=self.method,
            url=self.url,
            headers=dict(self.headers),
            body=self.body,
            stream=self.stream,
        )


@dataclass
class Response:
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = field(default=b"")
    stream: bool = False

    def copy(self) -> "Response":
        return Response(
            status_code=self.status_code,
            headers=dict(self.headers),
            body=self.body,
            stream=self.stream,
        )


@dataclass
class UpstreamServer:
    name: str
    host: str
    port: int
    is_primary: bool = False
    status: UpstreamStatus = UpstreamStatus.HEALTHY
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def mark_failed(self, timestamp: float) -> None:
        self.failure_count += 1
        self.last_failure_time = timestamp

    def mark_healthy(self, timestamp: float) -> None:
        self.status = UpstreamStatus.HEALTHY
        self.failure_count = 0
        self.last_success_time = timestamp


@dataclass
class ProxyConfig:
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    max_failures: int = 3
    failure_timeout: float = 60.0
    auto_failback: bool = True
    failback_interval: float = 30.0
    max_idle_time: float = 60.0
    max_reuse_count: int = 100
    max_pool_size: int = 10

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.connect_timeout <= 0:
            raise InvalidConfigError("connect_timeout must be positive")
        if self.read_timeout <= 0:
            raise InvalidConfigError("read_timeout must be positive")
        if self.max_failures <= 0:
            raise InvalidConfigError("max_failures must be positive")
        if self.failure_timeout <= 0:
            raise InvalidConfigError("failure_timeout must be positive")
        if self.failback_interval <= 0:
            raise InvalidConfigError("failback_interval must be positive")
        if self.max_idle_time <= 0:
            raise InvalidConfigError("max_idle_time must be positive")
        if self.max_reuse_count <= 0:
            raise InvalidConfigError("max_reuse_count must be positive")
        if self.max_pool_size <= 0:
            raise InvalidConfigError("max_pool_size must be positive")


@dataclass
class ConnectionInfo:
    id: str
    upstream_address: str
    status: ConnectionStatus
    created_at: float
    last_used_at: float
    reuse_count: int


@dataclass
class ProxyStats:
    total_requests: int = 0
    forwarded_requests: int = 0
    failed_requests: int = 0
    failover_count: int = 0
    active_connections: int = 0
    reused_connections: int = 0
