from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import uuid

from .exceptions import ConnectionClosedError, HealthCheckFailedError
from .models import ConnectionState


@dataclass
class MockTCPConnection:
    host: str
    port: int
    conn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: ConnectionState = ConnectionState.IDLE
    created_at: float = 0.0
    last_idle_start: float = 0.0
    last_borrowed_at: float = 0.0
    borrow_count: int = 0
    _healthy: bool = True
    _closed: bool = False

    def connect(self) -> None:
        if self._closed:
            raise ConnectionClosedError(f"Connection {self.conn_id} is already closed")
        self._healthy = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._healthy = False
        self.state = ConnectionState.CLOSED

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def is_healthy(self) -> bool:
        if self._closed:
            return False
        return self._healthy

    def set_unhealthy(self) -> None:
        self._healthy = False

    def set_healthy(self) -> None:
        if not self._closed:
            self._healthy = True

    def health_check(self, timeout: Optional[float] = None) -> bool:
        if self._closed:
            return False
        return self._healthy

    def send(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionClosedError(f"Connection {self.conn_id} is closed")
        if not self._healthy:
            raise HealthCheckFailedError(f"Connection {self.conn_id} is unhealthy")

    def recv(self, size: int = 1024) -> bytes:
        if self._closed:
            raise ConnectionClosedError(f"Connection {self.conn_id} is closed")
        if not self._healthy:
            raise HealthCheckFailedError(f"Connection {self.conn_id} is unhealthy")
        return b"mock-response"

    def __hash__(self) -> int:
        return hash(self.conn_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MockTCPConnection):
            return NotImplemented
        return self.conn_id == other.conn_id
