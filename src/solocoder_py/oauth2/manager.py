from __future__ import annotations

import base64
import hashlib
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from .exceptions import (
    AuthorizationCodeAlreadyConsumedError,
    AuthorizationCodeExpiredError,
    AuthorizationCodeNotFoundError,
    AuthorizationSessionNotFoundError,
    CodeVerifierMismatchError,
    InvalidParameterError,
    StateAlreadyUsedError,
    StateInvalidError,
    StateMissingError,
    UnsupportedChallengeMethodError,
)
from .models import AuthorizationSession, CodeChallengeMethod


@dataclass
class OAuth2StateManager:
    _sessions: Dict[str, AuthorizationSession] = field(default_factory=dict)
    _code_to_session: Dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    default_code_expires_in: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    default_session_id_length: int = 32
    default_authorization_code_length: int = 32
    default_state_length: int = 32

    def __post_init__(self) -> None:
        if self.default_code_expires_in.total_seconds() <= 0:
            raise ValueError("default_code_expires_in must be positive")
        if self.default_session_id_length <= 0:
            raise ValueError("default_session_id_length must be positive")
        if self.default_authorization_code_length <= 0:
            raise ValueError("default_authorization_code_length must be positive")
        if self.default_state_length <= 0:
            raise ValueError("default_state_length must be positive")

    @staticmethod
    def _generate_random_string(length: int) -> str:
        if length <= 0:
            raise ValueError("length must be positive")
        num_bytes = length
        return secrets.token_urlsafe(num_bytes)[:length]

    @staticmethod
    def parse_code_challenge_method(method: str) -> CodeChallengeMethod:
        if not method:
            raise InvalidParameterError("code_challenge_method cannot be empty")
        try:
            return CodeChallengeMethod(method)
        except ValueError:
            raise UnsupportedChallengeMethodError(
                f"Unsupported code_challenge_method: {method}"
            )

    @staticmethod
    def compute_s256_challenge(code_verifier: str) -> str:
        if not code_verifier:
            raise InvalidParameterError("code_verifier cannot be empty")
        hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(hashed).rstrip(b"=").decode("ascii")

    def verify_pkce(
        self,
        session_id: str,
        code_verifier: str,
    ) -> None:
        if not session_id:
            raise InvalidParameterError("session_id cannot be empty")
        if not code_verifier:
            raise InvalidParameterError("code_verifier cannot be empty")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AuthorizationSessionNotFoundError(
                    f"Authorization session not found: {session_id}"
                )

            self._verify_pkce_internal(session, code_verifier)

    @staticmethod
    def _verify_pkce_internal(
        session: AuthorizationSession,
        code_verifier: str,
    ) -> None:
        if session.code_challenge_method == CodeChallengeMethod.PLAIN:
            computed_challenge = code_verifier
        elif session.code_challenge_method == CodeChallengeMethod.S256:
            computed_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)
        else:
            raise UnsupportedChallengeMethodError(
                f"Unsupported code_challenge_method: {session.code_challenge_method}"
            )

        if not secrets.compare_digest(computed_challenge, session.code_challenge):
            raise CodeVerifierMismatchError("code_verifier does not match code_challenge")

    def create_authorization_session(
        self,
        code_challenge: str,
        code_challenge_method: str,
        state: Optional[str] = None,
        auto_generate_state: bool = True,
        client_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scope: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        if not code_challenge:
            raise InvalidParameterError("code_challenge cannot be empty")

        method = self.parse_code_challenge_method(code_challenge_method)

        if state is None and auto_generate_state:
            state = self._generate_random_string(self.default_state_length)

        if not state:
            raise InvalidParameterError("state cannot be empty")

        with self._lock:
            sid = (
                session_id
                if session_id
                else self._generate_random_string(self.default_session_id_length)
            )
            while sid in self._sessions:
                sid = self._generate_random_string(self.default_session_id_length)

            session = AuthorizationSession(
                session_id=sid,
                code_challenge=code_challenge,
                code_challenge_method=method,
                state=state,
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope,
            )
            self._sessions[sid] = session

            return sid, state

    def verify_state(self, session_id: str, state: str) -> None:
        if not session_id:
            raise InvalidParameterError("session_id cannot be empty")
        if not state:
            raise StateMissingError("state parameter is missing or empty")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AuthorizationSessionNotFoundError(
                    f"Authorization session not found: {session_id}"
                )

            if session.state_consumed:
                raise StateAlreadyUsedError(
                    "state has already been verified and consumed for this session"
                )

            if session.state is None or not secrets.compare_digest(state, session.state):
                raise StateInvalidError("state parameter does not match stored state")

            session.state_verified = True
            session.state_consumed = True

    def generate_authorization_code(
        self,
        session_id: str,
        expires_in: Optional[timedelta] = None,
    ) -> str:
        if not session_id:
            raise InvalidParameterError("session_id cannot be empty")

        duration = expires_in if expires_in is not None else self.default_code_expires_in
        if duration.total_seconds() <= 0:
            raise InvalidParameterError("expires_in must be positive")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise AuthorizationSessionNotFoundError(
                    f"Authorization session not found: {session_id}"
                )

            code = self._generate_random_string(self.default_authorization_code_length)
            while code in self._code_to_session:
                code = self._generate_random_string(self.default_authorization_code_length)

            session.set_authorization_code(code, duration)
            self._code_to_session[code] = session_id

            return code

    def consume_authorization_code(
        self,
        code: str,
        code_verifier: str,
    ) -> AuthorizationSession:
        if not code:
            raise InvalidParameterError("authorization code cannot be empty")
        if not code_verifier:
            raise InvalidParameterError("code_verifier cannot be empty")

        with self._lock:
            session_id = self._code_to_session.get(code)
            if session_id is None:
                raise AuthorizationCodeNotFoundError(
                    f"Authorization code not found: {code}"
                )

            session = self._sessions.get(session_id)
            if session is None or session.authorization_code != code:
                raise AuthorizationCodeNotFoundError(
                    f"Authorization code not found: {code}"
                )

            if session.is_code_expired():
                raise AuthorizationCodeExpiredError(
                    f"Authorization code has expired: {code}"
                )

            if session.is_code_consumed():
                raise AuthorizationCodeAlreadyConsumedError(
                    f"Authorization code has already been consumed: {code}"
                )

            self._verify_pkce_internal(session, code_verifier)

            session.mark_code_consumed()

            return session

    def get_session(self, session_id: str) -> Optional[AuthorizationSession]:
        if not session_id:
            raise InvalidParameterError("session_id cannot be empty")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return AuthorizationSession(
                session_id=session.session_id,
                code_challenge=session.code_challenge,
                code_challenge_method=session.code_challenge_method,
                state=session.state,
                state_verified=session.state_verified,
                state_consumed=session.state_consumed,
                authorization_code=session.authorization_code,
                authorization_code_created_at=session.authorization_code_created_at,
                authorization_code_expires_at=session.authorization_code_expires_at,
                authorization_code_consumed=session.authorization_code_consumed,
                authorization_code_consumed_at=session.authorization_code_consumed_at,
                client_id=session.client_id,
                redirect_uri=session.redirect_uri,
                scope=session.scope,
                created_at=session.created_at,
            )

    def get_session_by_code(self, code: str) -> Optional[AuthorizationSession]:
        if not code:
            raise InvalidParameterError("authorization code cannot be empty")
        with self._lock:
            session_id = self._code_to_session.get(code)
            if session_id is None:
                return None
            return self.get_session(session_id)

    def invalidate_session(self, session_id: str) -> bool:
        if not session_id:
            raise InvalidParameterError("session_id cannot be empty")
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                return False
            if session.authorization_code:
                self._code_to_session.pop(session.authorization_code, None)
            return True

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._code_to_session.clear()

    def count_sessions(self) -> int:
        with self._lock:
            return len(self._sessions)

    def cleanup_expired(self) -> int:
        now = datetime.now()
        with self._lock:
            expired_ids = []
            for session_id, session in self._sessions.items():
                code_expired = (
                    session.authorization_code_expires_at is not None
                    and now >= session.authorization_code_expires_at
                )
                if code_expired and session.authorization_code and not session.is_code_consumed():
                    expired_ids.append(session_id)

            for sid in expired_ids:
                session = self._sessions.pop(sid, None)
                if session and session.authorization_code:
                    self._code_to_session.pop(session.authorization_code, None)

            return len(expired_ids)
