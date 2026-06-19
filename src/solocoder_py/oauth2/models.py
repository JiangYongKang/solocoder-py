from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class CodeChallengeMethod(str, Enum):
    PLAIN = "plain"
    S256 = "S256"


@dataclass
class AuthorizationSession:
    session_id: str
    code_challenge: str
    code_challenge_method: CodeChallengeMethod
    state: Optional[str] = None
    state_verified: bool = False
    state_consumed: bool = False
    authorization_code: Optional[str] = None
    authorization_code_created_at: Optional[datetime] = None
    authorization_code_expires_at: Optional[datetime] = None
    authorization_code_consumed: bool = False
    authorization_code_consumed_at: Optional[datetime] = None
    client_id: Optional[str] = None
    redirect_uri: Optional[str] = None
    scope: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.code_challenge:
            raise ValueError("code_challenge cannot be empty")
        if not isinstance(self.code_challenge_method, CodeChallengeMethod):
            raise ValueError("code_challenge_method must be a CodeChallengeMethod enum")

    def set_authorization_code(
        self,
        code: str,
        expires_in: timedelta,
    ) -> None:
        self.authorization_code = code
        self.authorization_code_created_at = datetime.now()
        self.authorization_code_expires_at = self.authorization_code_created_at + expires_in
        self.authorization_code_consumed = False
        self.authorization_code_consumed_at = None

    def is_code_expired(self) -> bool:
        if self.authorization_code_expires_at is None:
            return True
        return datetime.now() >= self.authorization_code_expires_at

    def is_code_consumed(self) -> bool:
        return self.authorization_code_consumed

    def mark_code_consumed(self) -> None:
        self.authorization_code_consumed = True
        self.authorization_code_consumed_at = datetime.now()
