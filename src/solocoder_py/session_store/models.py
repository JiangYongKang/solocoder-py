from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .exceptions import InvalidSessionConfigError


class EvictionStrategy(str, Enum):
    REJECT = "reject"
    EVICT_OLDEST = "evict_oldest"


class Clock:
    def now(self) -> float:
        return time.time()


def generate_session_id() -> str:
    return "sess_" + secrets.token_hex(16)


@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: float
    expires_at: float
    idle_expires_at: float
    ttl: float
    idle_timeout: float
    data: Dict[str, Any] = field(default_factory=dict)
    forcibly_logged_out: bool = False
    forced_logout_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if self.ttl <= 0:
            raise InvalidSessionConfigError("ttl must be positive")
        if self.idle_timeout <= 0:
            raise InvalidSessionConfigError("idle_timeout must be positive")
        if self.idle_timeout > self.ttl:
            raise InvalidSessionConfigError(
                "idle_timeout must be less than or equal to ttl"
            )


@dataclass
class SessionCreateConfig:
    ttl: float
    idle_timeout: float
    max_concurrent_sessions: int = 5
    eviction_strategy: EvictionStrategy = EvictionStrategy.EVICT_OLDEST

    def __post_init__(self) -> None:
        if self.ttl <= 0:
            raise InvalidSessionConfigError("ttl must be positive")
        if self.idle_timeout <= 0:
            raise InvalidSessionConfigError("idle_timeout must be positive")
        if self.idle_timeout > self.ttl:
            raise InvalidSessionConfigError(
                "idle_timeout must be less than or equal to ttl"
            )
        if self.max_concurrent_sessions <= 0:
            raise InvalidSessionConfigError(
                "max_concurrent_sessions must be positive"
            )


@dataclass
class SessionInfo:
    session_id: str
    user_id: str
    created_at: float
    expires_at: float
    idle_expires_at: float
    ttl: float
    idle_timeout: float
    data: Dict[str, Any]
    forcibly_logged_out: bool
    forced_logout_reason: Optional[str]
