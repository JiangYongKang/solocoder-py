from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import (
    InvalidSessionConfigError,
    InvalidUserIdError,
    SessionExpiredError,
    SessionForciblyLoggedOutError,
    SessionIdleTimeoutError,
    SessionLimitExceededError,
    SessionNotFoundError,
)
from .models import (
    Clock,
    EvictionStrategy,
    Session,
    SessionCreateConfig,
    SessionInfo,
    generate_session_id,
)


def _validate_user_id(user_id: str) -> None:
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise InvalidUserIdError("user_id must be a non-empty string")


def _validate_config(config: SessionCreateConfig) -> None:
    if config.ttl <= 0:
        raise InvalidSessionConfigError("ttl must be positive")
    if config.idle_timeout <= 0:
        raise InvalidSessionConfigError("idle_timeout must be positive")
    if config.idle_timeout > config.ttl:
        raise InvalidSessionConfigError(
            "idle_timeout must be less than or equal to ttl"
        )
    if config.max_concurrent_sessions <= 0:
        raise InvalidSessionConfigError(
            "max_concurrent_sessions must be positive"
        )


@dataclass
class _UserSessions:
    sessions: "OrderedDict[str, Session]" = field(
        default_factory=OrderedDict
    )


class SessionStore:
    _sessions_by_id: Dict[str, Session]
    _sessions_by_user: Dict[str, _UserSessions]
    _default_config: SessionCreateConfig
    _lock: threading.RLock
    _clock: Clock

    def __init__(
        self,
        default_config: Optional[SessionCreateConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if default_config is None:
            default_config = SessionCreateConfig(
                ttl=3600.0,
                idle_timeout=1800.0,
                max_concurrent_sessions=5,
                eviction_strategy=EvictionStrategy.EVICT_OLDEST,
            )
        _validate_config(default_config)

        self._sessions_by_id = {}
        self._sessions_by_user = {}
        self._default_config = default_config
        self._lock = threading.RLock()
        self._clock = clock or Clock()

    def create_session(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        config: Optional[SessionCreateConfig] = None,
    ) -> SessionInfo:
        _validate_user_id(user_id)
        if config is None:
            config = self._default_config
        _validate_config(config)

        session_data = dict(data) if data else {}

        with self._lock:
            user_sessions = self._sessions_by_user.get(user_id)
            if user_sessions is None:
                user_sessions = _UserSessions()
                self._sessions_by_user[user_id] = user_sessions

            if len(user_sessions.sessions) >= config.max_concurrent_sessions:
                if config.eviction_strategy == EvictionStrategy.REJECT:
                    raise SessionLimitExceededError(
                        f"max concurrent sessions ({config.max_concurrent_sessions}) "
                        f"exceeded for user {user_id}"
                    )
                elif config.eviction_strategy == EvictionStrategy.EVICT_OLDEST:
                    oldest_id, oldest_session = next(
                        iter(user_sessions.sessions.items())
                    )
                    oldest_session.forcibly_logged_out = True
                    oldest_session.forced_logout_reason = (
                        "evicted due to concurrent session limit"
                    )
                    del user_sessions.sessions[oldest_id]

            for _ in range(100):
                session_id = generate_session_id()
                if session_id not in self._sessions_by_id:
                    break
            else:
                raise RuntimeError("failed to generate unique session id")

            now = self._clock.now()
            session = Session(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                expires_at=now + config.ttl,
                idle_expires_at=now + config.idle_timeout,
                ttl=config.ttl,
                idle_timeout=config.idle_timeout,
                data=session_data,
                forcibly_logged_out=False,
                forced_logout_reason=None,
            )

            self._sessions_by_id[session_id] = session
            user_sessions.sessions[session_id] = session

            return self._make_session_info(session)

    def get_session(self, session_id: str) -> SessionInfo:
        if not session_id or not isinstance(session_id, str):
            raise SessionNotFoundError("session_id must be a non-empty string")

        with self._lock:
            session = self._sessions_by_id.get(session_id)
            if session is None:
                raise SessionNotFoundError(
                    f"session not found: {session_id}"
                )

            if session.forcibly_logged_out:
                raise SessionForciblyLoggedOutError(
                    session.forced_logout_reason
                    or "session has been forcibly logged out"
                )

            now = self._clock.now()

            if now >= session.expires_at:
                del self._sessions_by_id[session_id]
                user_sessions = self._sessions_by_user.get(session.user_id)
                if user_sessions and session_id in user_sessions.sessions:
                    del user_sessions.sessions[session_id]
                raise SessionExpiredError("session has expired")

            if now >= session.idle_expires_at:
                del self._sessions_by_id[session_id]
                user_sessions = self._sessions_by_user.get(session.user_id)
                if user_sessions and session_id in user_sessions.sessions:
                    del user_sessions.sessions[session_id]
                raise SessionIdleTimeoutError(
                    "session has timed out due to inactivity"
                )

            session.expires_at = now + session.ttl
            session.idle_expires_at = now + session.idle_timeout

            user_sessions = self._sessions_by_user.get(session.user_id)
            if user_sessions and session_id in user_sessions.sessions:
                user_sessions.sessions.move_to_end(session_id)

            return self._make_session_info(session)

    def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
    ) -> SessionInfo:
        if not session_id or not isinstance(session_id, str):
            raise SessionNotFoundError("session_id must be a non-empty string")

        with self._lock:
            session = self._sessions_by_id.get(session_id)
            if session is None:
                raise SessionNotFoundError(
                    f"session not found: {session_id}"
                )

            if session.forcibly_logged_out:
                raise SessionForciblyLoggedOutError(
                    session.forced_logout_reason
                    or "session has been forcibly logged out"
                )

            now = self._clock.now()

            if now >= session.expires_at:
                del self._sessions_by_id[session_id]
                user_sessions = self._sessions_by_user.get(session.user_id)
                if user_sessions and session_id in user_sessions.sessions:
                    del user_sessions.sessions[session_id]
                raise SessionExpiredError("session has expired")

            if now >= session.idle_expires_at:
                del self._sessions_by_id[session_id]
                user_sessions = self._sessions_by_user.get(session.user_id)
                if user_sessions and session_id in user_sessions.sessions:
                    del user_sessions.sessions[session_id]
                raise SessionIdleTimeoutError(
                    "session has timed out due to inactivity"
                )

            session.data.update(data)
            session.expires_at = now + session.ttl
            session.idle_expires_at = now + session.idle_timeout

            user_sessions = self._sessions_by_user.get(session.user_id)
            if user_sessions and session_id in user_sessions.sessions:
                user_sessions.sessions.move_to_end(session_id)

            return self._make_session_info(session)

    def delete_session(self, session_id: str) -> bool:
        if not session_id or not isinstance(session_id, str):
            return False

        with self._lock:
            session = self._sessions_by_id.pop(session_id, None)
            if session is None:
                return False

            user_sessions = self._sessions_by_user.get(session.user_id)
            if user_sessions and session_id in user_sessions.sessions:
                del user_sessions.sessions[session_id]
                if not user_sessions.sessions:
                    del self._sessions_by_user[session.user_id]

            return True

    def list_sessions_by_user(self, user_id: str) -> List[SessionInfo]:
        _validate_user_id(user_id)

        with self._lock:
            user_sessions = self._sessions_by_user.get(user_id)
            if user_sessions is None:
                return []

            now = self._clock.now()
            result = []
            expired_ids = []

            for session_id, session in user_sessions.sessions.items():
                if session.forcibly_logged_out:
                    continue
                if now >= session.expires_at or now >= session.idle_expires_at:
                    expired_ids.append(session_id)
                    continue
                result.append(self._make_session_info(session))

            for expired_id in expired_ids:
                del user_sessions.sessions[expired_id]
                del self._sessions_by_id[expired_id]
            if not user_sessions.sessions:
                del self._sessions_by_user[user_id]

            return result

    def logout_all_sessions(self, user_id: str, reason: Optional[str] = None) -> int:
        _validate_user_id(user_id)

        with self._lock:
            user_sessions = self._sessions_by_user.get(user_id)
            if user_sessions is None:
                return 0

            count = 0
            for session in user_sessions.sessions.values():
                session.forcibly_logged_out = True
                session.forced_logout_reason = reason or "user logged out all sessions"
                count += 1

            del self._sessions_by_user[user_id]

            return count

    def clear(self) -> None:
        with self._lock:
            self._sessions_by_id.clear()
            self._sessions_by_user.clear()

    def _make_session_info(self, session: Session) -> SessionInfo:
        return SessionInfo(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            idle_expires_at=session.idle_expires_at,
            ttl=session.ttl,
            idle_timeout=session.idle_timeout,
            data=dict(session.data),
            forcibly_logged_out=session.forcibly_logged_out,
            forced_logout_reason=session.forced_logout_reason,
        )
