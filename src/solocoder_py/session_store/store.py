from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
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
    validate_session_config,
    validate_session_id,
    validate_user_id,
)


@dataclass
class _UserSessions:
    sessions: "OrderedDict[str, Session]" = field(default_factory=OrderedDict)


_Tombstone = Tuple[str, float]


class SessionStore:
    _sessions_by_id: Dict[str, Session]
    _sessions_by_user: Dict[str, _UserSessions]
    _tombstones: Dict[str, _Tombstone]
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
        validate_session_config(
            default_config.ttl,
            default_config.idle_timeout,
            default_config.max_concurrent_sessions,
        )

        self._sessions_by_id = {}
        self._sessions_by_user = {}
        self._tombstones = {}
        self._default_config = default_config
        self._lock = threading.RLock()
        self._clock = clock or Clock()

    def create_session(
        self,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        config: Optional[SessionCreateConfig] = None,
    ) -> SessionInfo:
        validate_user_id(user_id)
        if config is None:
            config = self._default_config
        validate_session_config(
            config.ttl, config.idle_timeout, config.max_concurrent_sessions
        )

        session_data = dict(data) if data else {}

        with self._lock:
            self._cleanup_expired_tombstones()

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
                    self._forcibly_logout_session(
                        oldest_id,
                        oldest_session,
                        "evicted due to concurrent session limit",
                    )

            for _ in range(100):
                session_id = generate_session_id()
                if (
                    session_id not in self._sessions_by_id
                    and session_id not in self._tombstones
                ):
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
        validate_session_id(session_id)

        with self._lock:
            self._cleanup_expired_tombstones()

            session = self._sessions_by_id.get(session_id)
            if session is None:
                tombstone = self._tombstones.get(session_id)
                if tombstone is not None:
                    raise SessionForciblyLoggedOutError(tombstone[0])
                raise SessionNotFoundError(f"session not found: {session_id}")

            if session.forcibly_logged_out:
                raise SessionForciblyLoggedOutError(
                    session.forced_logout_reason
                    or "session has been forcibly logged out"
                )

            now = self._clock.now()

            if now >= session.expires_at:
                self._remove_session(session_id)
                raise SessionExpiredError("session has expired")

            if now >= session.idle_expires_at:
                self._remove_session(session_id)
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
        validate_session_id(session_id)

        with self._lock:
            self._cleanup_expired_tombstones()

            session = self._sessions_by_id.get(session_id)
            if session is None:
                tombstone = self._tombstones.get(session_id)
                if tombstone is not None:
                    raise SessionForciblyLoggedOutError(tombstone[0])
                raise SessionNotFoundError(f"session not found: {session_id}")

            if session.forcibly_logged_out:
                raise SessionForciblyLoggedOutError(
                    session.forced_logout_reason
                    or "session has been forcibly logged out"
                )

            now = self._clock.now()

            if now >= session.expires_at:
                self._remove_session(session_id)
                raise SessionExpiredError("session has expired")

            if now >= session.idle_expires_at:
                self._remove_session(session_id)
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
            return self._remove_session(session_id)

    def list_sessions_by_user(self, user_id: str) -> List[SessionInfo]:
        validate_user_id(user_id)

        with self._lock:
            self._cleanup_expired_tombstones()

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
                self._remove_session(expired_id)

            return result

    def logout_all_sessions(
        self, user_id: str, reason: Optional[str] = None
    ) -> int:
        validate_user_id(user_id)

        with self._lock:
            self._cleanup_expired_tombstones()

            user_sessions = self._sessions_by_user.get(user_id)
            if user_sessions is None:
                return 0

            count = 0
            final_reason = reason or "user logged out all sessions"
            session_items = list(user_sessions.sessions.items())
            for session_id, session in session_items:
                self._forcibly_logout_session(session_id, session, final_reason)
                count += 1

            return count

    def clear(self) -> None:
        with self._lock:
            self._sessions_by_id.clear()
            self._sessions_by_user.clear()
            self._tombstones.clear()

    def _forcibly_logout_session(
        self,
        session_id: str,
        session: Session,
        reason: str,
    ) -> None:
        user_sessions = self._sessions_by_user.get(session.user_id)
        if user_sessions and session_id in user_sessions.sessions:
            del user_sessions.sessions[session_id]
            if not user_sessions.sessions:
                del self._sessions_by_user[session.user_id]

        if session_id in self._sessions_by_id:
            del self._sessions_by_id[session_id]

        tombstone_ttl = session.ttl
        expires_at = self._clock.now() + tombstone_ttl
        self._tombstones[session_id] = (reason, expires_at)

    def _remove_session(self, session_id: str) -> bool:
        session = self._sessions_by_id.pop(session_id, None)
        if session is None:
            return False

        user_sessions = self._sessions_by_user.get(session.user_id)
        if user_sessions and session_id in user_sessions.sessions:
            del user_sessions.sessions[session_id]
            if not user_sessions.sessions:
                del self._sessions_by_user[session.user_id]

        return True

    def _cleanup_expired_tombstones(self) -> None:
        now = self._clock.now()
        expired_ids = [
            sid for sid, (_, exp) in self._tombstones.items() if now >= exp
        ]
        for sid in expired_ids:
            del self._tombstones[sid]

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
