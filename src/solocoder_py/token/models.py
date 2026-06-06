from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TokenStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class AccessToken:
    token: str
    user_id: str
    family_id: str
    issued_at: datetime
    expires_at: datetime
    status: TokenStatus = TokenStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == TokenStatus.ACTIVE and self.expires_at > datetime.now()

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now()


@dataclass
class RefreshToken:
    token: str
    user_id: str
    family_id: str
    generation: int
    issued_at: datetime
    expires_at: datetime
    status: TokenStatus = TokenStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == TokenStatus.ACTIVE and self.expires_at > datetime.now()

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now()


@dataclass
class TokenPair:
    access_token: AccessToken
    refresh_token: RefreshToken


@dataclass
class TokenFamily:
    family_id: str
    user_id: str
    created_at: datetime
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    generations: list[RefreshToken] = field(default_factory=list)
    access_tokens: list[AccessToken] = field(default_factory=list)
    latest_generation: int = 0

    def revoke_all(self) -> None:
        self.revoked = True
        self.revoked_at = datetime.now()
        for rt in self.generations:
            rt.status = TokenStatus.REVOKED
        for at in self.access_tokens:
            at.status = TokenStatus.REVOKED
