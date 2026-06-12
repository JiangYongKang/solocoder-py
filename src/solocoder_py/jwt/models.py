from __future__ import annotations

import dataclasses
import datetime
import secrets
from dataclasses import dataclass, field
from typing import Any, Optional

from ..seat.clock import Clock, SystemClock

HMAC_ALGORITHMS: set[str] = {
    "HS256",
    "HS384",
    "HS512",
}


def _generate_kid() -> str:
    return secrets.token_urlsafe(16)


def _generate_secret(length: int = 32) -> bytes:
    return secrets.token_bytes(length)


@dataclass(frozen=True)
class SigningKey:
    kid: str
    secret: bytes
    algorithm: str
    created_at: float
    retire_at: float
    is_active: bool = False

    def __post_init__(self) -> None:
        if self.algorithm not in HMAC_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        if not self.kid:
            raise ValueError("kid must not be empty")
        if not self.secret:
            raise ValueError("secret must not be empty")


@dataclass
class JWTConfig:
    issuer: str
    audiences: list[str] = field(default_factory=list)
    allowed_algorithms: set[str] = field(default_factory=lambda: {"HS256", "HS384", "HS512"})
    default_algorithm: str = "HS256"
    default_expire_seconds: int = 3600
    key_retire_seconds: int = 86400
    current_service_id: Optional[str] = None
    allowed_issuers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.issuer:
            raise ValueError("issuer must not be empty")
        for alg in self.allowed_algorithms:
            if alg not in HMAC_ALGORITHMS:
                raise ValueError(f"Unsupported algorithm in whitelist: {alg}")
        if self.default_algorithm not in self.allowed_algorithms:
            raise ValueError(
                f"Default algorithm '{self.default_algorithm}' not in allowed algorithms"
            )
        if self.key_retire_seconds <= 0:
            raise ValueError("key_retire_seconds must be positive")
        if self.default_expire_seconds < 0:
            raise ValueError("default_expire_seconds must be non-negative")
        if not self.allowed_issuers:
            self.allowed_issuers = [self.issuer]


@dataclass
class DecodedJWT:
    header: dict[str, Any]
    payload: dict[str, Any]
    signature: bytes
    signing_input: bytes


@dataclass
class VerifiedJWT:
    header: dict[str, Any]
    payload: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.payload[key]

    def __contains__(self, key: str) -> bool:
        return key in self.payload


@dataclass
class SignOptions:
    algorithm: Optional[str] = None
    expire_seconds: Optional[int] = None
    include_iat: bool = True
    include_jti: bool = True
    extra_headers: dict[str, Any] = field(default_factory=dict)


class JWTClock:
    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._clock: Clock = clock or SystemClock()

    def now(self) -> float:
        return self._clock.now()

    def now_utc_datetime(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.now(), tz=datetime.timezone.utc)

    @classmethod
    def from_clock(cls, clock: Clock) -> "JWTClock":
        return cls(clock=clock)


__all__ = [
    "HMAC_ALGORITHMS",
    "SigningKey",
    "JWTConfig",
    "DecodedJWT",
    "VerifiedJWT",
    "SignOptions",
    "JWTClock",
    "_generate_kid",
    "_generate_secret",
]
