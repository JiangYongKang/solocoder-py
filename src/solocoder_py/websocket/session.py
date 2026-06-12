from __future__ import annotations

from typing import Any, Callable, Optional

from .clock import Clock, SystemClock
from .connection import SimulatedWebSocketConnection
from .exceptions import (
    ConnectionClosedError,
    SessionClosedError,
)
from .models import (
    HeartbeatConfig,
    HeartbeatStatus,
    Message,
    MessageType,
    ReconnectConfig,
    ReconnectStatus,
    ReorderConfig,
    SessionContext,
    SessionState,
)
from .reorder_buffer import ReorderBuffer


class WebSocketSession:
    def __init__(
        self,
        session_id: str,
        connection: Optional[SimulatedWebSocketConnection] = None,
        heartbeat_config: Optional[HeartbeatConfig] = None,
        reconnect_config: Optional[ReconnectConfig] = None,
        reorder_config: Optional[ReorderConfig] = None,
        clock: Optional[Clock] = None,
        on_message: Optional[Callable[[Message], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_reconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        self._session_id = session_id
        self._connection = connection or SimulatedWebSocketConnection(session_id)
        self._heartbeat_config = heartbeat_config or HeartbeatConfig()
        self._reconnect_config = reconnect_config or ReconnectConfig()
        self._reorder_config = reorder_config or ReorderConfig()
        self._clock = clock or SystemClock()
        self._on_message = on_message
        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect

        self._context = SessionContext(session_id=session_id)
        self._state: str = SessionState.DISCONNECTED

        self._heartbeat_status = HeartbeatStatus()
        self._reconnect_status = ReconnectStatus()

        self._send_sequence: int = 0
        self._reorder_buffer = ReorderBuffer(
            config=reorder_config,
            clock=self._clock,
        )

        self._delivered_messages: list[Message] = []
        self._closed: bool = False
        self._disconnected_at: float = 0.0
        self._current_ping_counted_for_timeout: int = 0

        if self._connection.is_connected:
            self._state = SessionState.CONNECTED
            self._reset_heartbeat_state()
        else:
            self._disconnected_at = self._clock.now()
            if self._reconnect_config.max_attempts == 0:
                self._state = SessionState.PERMANENTLY_CLOSED
                self._closed = True

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == SessionState.CONNECTED

    @property
    def is_closed(self) -> bool:
        return self._closed or self._state == SessionState.PERMANENTLY_CLOSED

    @property
    def context(self) -> SessionContext:
        return self._context.clone()

    @property
    def heartbeat_status(self) -> HeartbeatStatus:
        return HeartbeatStatus(
            last_ping_sent_at=self._heartbeat_status.last_ping_sent_at,
            last_pong_received_at=self._heartbeat_status.last_pong_received_at,
            missed_pongs=self._heartbeat_status.missed_pongs,
            ping_count=self._heartbeat_status.ping_count,
            pong_count=self._heartbeat_status.pong_count,
        )

    @property
    def reconnect_status(self) -> ReconnectStatus:
        return ReconnectStatus(
            attempt_count=self._reconnect_status.attempt_count,
            current_delay=self._reconnect_status.current_delay,
            last_attempt_at=self._reconnect_status.last_attempt_at,
            next_attempt_at=self._reconnect_status.next_attempt_at,
        )

    @property
    def send_sequence(self) -> int:
        return self._send_sequence

    @property
    def reorder_buffer_size(self) -> int:
        return self._reorder_buffer.buffer_size

    @property
    def connection(self) -> SimulatedWebSocketConnection:
        return self._connection

    def connect(self) -> None:
        if self._closed:
            raise SessionClosedError(self._session_id)
        self._connection.connect()
        self._state = SessionState.CONNECTED
        self._reset_heartbeat_state()
        self._reconnect_status = ReconnectStatus()

    def disconnect(self) -> None:
        if self._closed:
            return
        self._connection.disconnect()
        if self._state not in (SessionState.PERMANENTLY_CLOSED, SessionState.DISCONNECTED):
            self._state = SessionState.DISCONNECTED
            self._disconnected_at = self._clock.now()
            self._reconnect_status = ReconnectStatus()
            if self._on_disconnect:
                self._on_disconnect()
            if self._reconnect_config.max_attempts == 0:
                self._state = SessionState.PERMANENTLY_CLOSED
                self._closed = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._connection.send_close() if self._connection.is_connected else self._connection.disconnect()
        self._state = SessionState.PERMANENTLY_CLOSED

    def send(self, payload: Any) -> int:
        if self._closed:
            raise SessionClosedError(self._session_id)
        if not self.is_connected:
            raise ConnectionClosedError("Session is not connected")

        seq = self._send_sequence
        self._send_sequence = (self._send_sequence + 1) % (self._reorder_config.max_sequence + 1)

        msg = Message(
            sequence=seq,
            payload=payload,
            type=MessageType.DATA,
            timestamp=self._clock.now(),
        )
        self._connection.send(msg)
        return seq

    def receive(self) -> list[Message]:
        if self._closed:
            raise SessionClosedError(self._session_id)

        delivered = self._reorder_buffer.check_timeout()

        while True:
            msg = self._connection.receive()
            if msg is None:
                break

            if msg.type == MessageType.PONG:
                self._handle_pong()
            elif msg.type == MessageType.PING:
                self._handle_ping()
            elif msg.type == MessageType.CLOSE:
                self._handle_close_frame()
            elif msg.type == MessageType.DATA:
                new_delivered = self._reorder_buffer.receive(msg)
                delivered.extend(new_delivered)

        if delivered and self._on_message:
            for msg in delivered:
                self._on_message(msg)

        self._delivered_messages.extend(delivered)
        return delivered

    def _handle_ping(self) -> None:
        if self.is_connected:
            self._connection.send_pong()

    def _handle_pong(self) -> None:
        self._heartbeat_status.last_pong_received_at = self._clock.now()
        self._heartbeat_status.pong_count += 1
        self._heartbeat_status.missed_pongs = 0

    def _handle_close_frame(self) -> None:
        if self._state not in (SessionState.PERMANENTLY_CLOSED, SessionState.DISCONNECTED):
            self._state = SessionState.DISCONNECTED
            self._connection.disconnect()
            self._disconnected_at = self._clock.now()
            self._reconnect_status = ReconnectStatus()
            if self._on_disconnect:
                self._on_disconnect()
            if self._reconnect_config.max_attempts == 0:
                self._state = SessionState.PERMANENTLY_CLOSED
                self._closed = True

    def tick(self) -> None:
        if self._closed:
            return

        self.receive()

        if self._closed:
            return

        if self._state == SessionState.CONNECTED:
            self._tick_heartbeat()

        if self._state in (SessionState.DISCONNECTED, SessionState.RECONNECTING):
            self._tick_reconnect()

        if self._closed:
            return

        self.receive()

    def _tick_heartbeat(self) -> None:
        now = self._clock.now()
        config = self._heartbeat_config

        time_since_ping = now - self._heartbeat_status.last_ping_sent_at
        if time_since_ping >= config.ping_interval:
            self._send_ping()

        ping_count = self._heartbeat_status.ping_count
        if ping_count > 0 and ping_count > self._current_ping_counted_for_timeout:
            time_since_pong = now - self._heartbeat_status.last_pong_received_at
            if time_since_pong >= config.ping_interval + config.pong_timeout:
                self._heartbeat_status.missed_pongs += 1
                self._current_ping_counted_for_timeout = ping_count

        if self._heartbeat_status.missed_pongs >= config.max_missed_pongs:
            self._on_heartbeat_timeout()

    def _send_ping(self) -> None:
        try:
            self._connection.send_ping()
            self._heartbeat_status.last_ping_sent_at = self._clock.now()
            self._heartbeat_status.ping_count += 1
        except ConnectionClosedError:
            self._state = SessionState.DISCONNECTED
            self._disconnected_at = self._clock.now()
            self._reconnect_status = ReconnectStatus()
            if self._on_disconnect:
                self._on_disconnect()
            if self._reconnect_config.max_attempts == 0:
                self._state = SessionState.PERMANENTLY_CLOSED
                self._closed = True

    def _reset_heartbeat_state(self) -> None:
        now = self._clock.now()
        self._heartbeat_status = HeartbeatStatus(
            last_ping_sent_at=now,
            last_pong_received_at=now,
            missed_pongs=0,
            ping_count=0,
            pong_count=0,
        )
        self._current_ping_counted_for_timeout = 0

    def _on_heartbeat_timeout(self) -> None:
        self._connection.disconnect()
        self._state = SessionState.DISCONNECTED
        self._disconnected_at = self._clock.now()
        self._reconnect_status = ReconnectStatus()
        if self._on_disconnect:
            self._on_disconnect()
        if self._reconnect_config.max_attempts == 0:
            self._state = SessionState.PERMANENTLY_CLOSED
            self._closed = True

    def _tick_reconnect(self) -> None:
        if self._reconnect_config.max_attempts == 0:
            self._state = SessionState.PERMANENTLY_CLOSED
            self._closed = True
            return

        now = self._clock.now()
        status = self._reconnect_status
        config = self._reconnect_config

        if self._state == SessionState.DISCONNECTED:
            self._state = SessionState.RECONNECTING
            status.attempt_count = 0
            first_delay = config.calculate_delay(1)
            first_attempt_at = self._disconnected_at + first_delay
            status.current_delay = first_delay
            status.next_attempt_at = first_attempt_at

            if now >= first_attempt_at:
                success = self._attempt_reconnect()
                status.attempt_count = 1
                status.last_attempt_at = now

                if success:
                    self._state = SessionState.CONNECTED
                    self._reset_heartbeat_state()
                    status.next_attempt_at = None
                    status.current_delay = 0.0
                    if self._on_reconnect:
                        self._on_reconnect()
                    return

                if status.attempt_count >= config.max_attempts:
                    self._state = SessionState.PERMANENTLY_CLOSED
                    self._closed = True
                    status.next_attempt_at = None
                    return

                status.current_delay = config.calculate_delay(status.attempt_count + 1)
                status.next_attempt_at = now + status.current_delay
            return

        if status.next_attempt_at is not None and now >= status.next_attempt_at:
            success = self._attempt_reconnect()
            status.attempt_count += 1
            status.last_attempt_at = now

            if success:
                self._state = SessionState.CONNECTED
                self._reset_heartbeat_state()
                status.next_attempt_at = None
                status.current_delay = 0.0
                if self._on_reconnect:
                    self._on_reconnect()
                return

            if status.attempt_count >= config.max_attempts:
                self._state = SessionState.PERMANENTLY_CLOSED
                self._closed = True
                status.next_attempt_at = None
                return

            status.current_delay = config.calculate_delay(status.attempt_count + 1)
            status.next_attempt_at = now + status.current_delay

    def _attempt_reconnect(self) -> bool:
        try:
            self._connection.connect()
            return True
        except Exception:
            return False

    def subscribe(self, topic: str) -> None:
        self._context.subscribed_topics.add(topic)

    def unsubscribe(self, topic: str) -> None:
        self._context.subscribed_topics.discard(topic)

    def is_subscribed(self, topic: str) -> bool:
        return topic in self._context.subscribed_topics

    def set_metadata(self, key: str, value: Any) -> None:
        self._context.metadata[key] = value

    def get_metadata(self, key: str) -> Any:
        return self._context.metadata.get(key)

    def flush_reorder_buffer(self) -> list[Message]:
        messages = self._reorder_buffer.force_flush()
        if messages and self._on_message:
            for msg in messages:
                self._on_message(msg)
        return messages
