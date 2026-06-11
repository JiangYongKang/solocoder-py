from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class SessionState:
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    PERMANENTLY_CLOSED = "permanently_closed"


class MessageType:
    DATA = "data"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"


@dataclass
class HeartbeatConfig:
    ping_interval: float = 30.0
    pong_timeout: float = 10.0
    max_missed_pongs: int = 3

    def __post_init__(self) -> None:
        if self.ping_interval <= 0:
            raise ValueError("ping_interval must be positive")
        if self.pong_timeout <= 0:
            raise ValueError("pong_timeout must be positive")
        if self.max_missed_pongs < 1:
            raise ValueError("max_missed_pongs must be at least 1")


@dataclass
class ReconnectConfig:
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be >= 0")

    def calculate_delay(self, attempt: int) -> float:
        if attempt < 1:
            return 0.0
        exponent = attempt - 1
        raw_delay = self.initial_delay * (self.backoff_multiplier ** exponent)
        return min(raw_delay, self.max_delay)


@dataclass
class ReorderConfig:
    max_buffer_size: int = 100
    wait_timeout: float = 5.0
    max_sequence: int = 2**32 - 1

    def __post_init__(self) -> None:
        if self.max_buffer_size < 1:
            raise ValueError("max_buffer_size must be at least 1")
        if self.wait_timeout <= 0:
            raise ValueError("wait_timeout must be positive")
        if self.max_sequence < 1:
            raise ValueError("max_sequence must be at least 1")


@dataclass
class Message:
    sequence: int
    payload: Any
    type: str = MessageType.DATA
    timestamp: float = 0.0


@dataclass
class SessionContext:
    session_id: str
    subscribed_topics: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> SessionContext:
        return SessionContext(
            session_id=self.session_id,
            subscribed_topics=set(self.subscribed_topics),
            metadata=dict(self.metadata),
        )


@dataclass
class HeartbeatStatus:
    last_ping_sent_at: float = 0.0
    last_pong_received_at: float = 0.0
    missed_pongs: int = 0
    ping_count: int = 0
    pong_count: int = 0


@dataclass
class ReconnectStatus:
    attempt_count: int = 0
    current_delay: float = 0.0
    last_attempt_at: float = 0.0
    next_attempt_at: Optional[float] = None
