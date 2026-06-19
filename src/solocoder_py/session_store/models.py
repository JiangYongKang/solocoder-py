from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .exceptions import (
    InvalidSessionConfigError,
    InvalidSessionIdError,
    InvalidUserIdError,
)


class EvictionStrategy(str, Enum):
    REJECT = "reject"
    EVICT_OLDEST = "evict_oldest"


class Clock:
    def now(self) -> float:
        return time.time()


def generate_session_id() -> str:
    return "sess_" + secrets.token_hex(16)


def validate_session_id(session_id: str) -> None:
    if not session_id or not isinstance(session_id, str):
        raise InvalidSessionIdError("session_id must be a non-empty string")


def validate_user_id(user_id: str) -> None:
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise InvalidUserIdError("user_id must be a non-empty string")


def validate_session_config(
    ttl: float,
    idle_timeout: float,
    max_concurrent_sessions: Optional[int] = None,
) -> None:
    if ttl <= 0:
        raise InvalidSessionConfigError("ttl must be positive")
    if idle_timeout <= 0:
        raise InvalidSessionConfigError("idle_timeout must be positive")
    if idle_timeout > ttl:
        raise InvalidSessionConfigError(
            "idle_timeout must be less than or equal to ttl"
        )
    if max_concurrent_sessions is not None and max_concurrent_sessions <= 0:
        raise InvalidSessionConfigError(
            "max_concurrent_sessions must be positive"
        )


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
        validate_session_id(self.session_id)
        validate_user_id(self.user_id)
        validate_session_config(self.ttl, self.idle_timeout)


@dataclass
class SessionCreateConfig:
    ttl: float
    idle_timeout: float
    max_concurrent_sessions: int = 5
    eviction_strategy: EvictionStrategy = EvictionStrategy.EVICT_OLDEST

    def __post_init__(self) -> None:
        validate_session_config(
            self.ttl, self.idle_timeout, self.max_concurrent_sessions
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
