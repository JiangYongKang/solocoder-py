from __future__ import annotations

import uuid
from typing import Callable, Dict, Optional

from .clock import Clock, SystemClock
from .connection import SimulatedWebSocketConnection
from .exceptions import SessionNotFoundError
from .models import (
    HeartbeatConfig,
    ReconnectConfig,
    ReorderConfig,
    SessionState,
)
from .session import WebSocketSession


class SessionManager:
    def __init__(
        self,
        heartbeat_config: Optional[HeartbeatConfig] = None,
        reconnect_config: Optional[ReconnectConfig] = None,
        reorder_config: Optional[ReorderConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._heartbeat_config = heartbeat_config or HeartbeatConfig()
        self._reconnect_config = reconnect_config or ReconnectConfig()
        self._reorder_config = reorder_config or ReorderConfig()
        self._clock = clock or SystemClock()
        self._sessions: Dict[str, WebSocketSession] = {}

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def connected_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_connected)

    def create_session(
        self,
        session_id: Optional[str] = None,
        connection: Optional[SimulatedWebSocketConnection] = None,
        on_message: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_reconnect: Optional[Callable] = None,
    ) -> WebSocketSession:
        sid = session_id or str(uuid.uuid4())

        session = WebSocketSession(
            session_id=sid,
            connection=connection,
            heartbeat_config=self._heartbeat_config,
            reconnect_config=self._reconnect_config,
            reorder_config=self._reorder_config,
            clock=self._clock,
            on_message=on_message,
            on_disconnect=on_disconnect,
            on_reconnect=on_reconnect,
        )

        self._sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> WebSocketSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def remove_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.close()
            del self._sessions[session_id]

    def close_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        session.close()

    def tick_all(self) -> None:
        for session in list(self._sessions.values()):
            if not session.is_closed:
                try:
                    session.tick()
                except Exception:
                    pass

        self._cleanup_closed_sessions()

    def _cleanup_closed_sessions(self) -> None:
        to_remove = [sid for sid, s in self._sessions.items() if s.is_closed]
        for sid in to_remove:
            del self._sessions[sid]

    def get_all_sessions(self) -> list[WebSocketSession]:
        return list(self._sessions.values())

    def get_sessions_by_state(self, state: str) -> list[WebSocketSession]:
        return [s for s in self._sessions.values() if s.state == state]

    def broadcast(self, payload) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for session_id, session in self._sessions.items():
            if session.is_connected:
                try:
                    session.send(payload)
                    results[session_id] = True
                except Exception:
                    results[session_id] = False
            else:
                results[session_id] = False
        return results

    def subscribe_all(self, topic: str) -> None:
        for session in self._sessions.values():
            session.subscribe(topic)

    def unsubscribe_all(self, topic: str) -> None:
        for session in self._sessions.values():
            session.unsubscribe(topic)

    def get_subscribed_sessions(self, topic: str) -> list[WebSocketSession]:
        return [s for s in self._sessions.values() if s.is_subscribed(topic)]

    def publish_to_topic(self, topic: str, payload) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for session in self._sessions.values():
            if session.is_subscribed(topic) and session.is_connected:
                try:
                    session.send(payload)
                    results[session.session_id] = True
                except Exception:
                    results[session.session_id] = False
        return results

    def close_all(self) -> None:
        for session in self._sessions.values():
            session.close()
        self._sessions.clear()
