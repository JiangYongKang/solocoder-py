from __future__ import annotations

import pytest

from solocoder_py.websocket import (
    ManualClock,
    ReconnectConfig,
    ReconnectionFailedError,
    SessionState,
    SimulatedWebSocketConnection,
    WebSocketSession,
)


class TestReconnectionNormalFlow:
    def test_reconnect_succeeds_on_first_attempt(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=5,
        )
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.disconnect()
        assert session.state == SessionState.DISCONNECTED

        session.tick()
        assert session.state == SessionState.RECONNECTING
        assert session.reconnect_status.attempt_count == 0
        assert session.reconnect_status.next_attempt_at == 1.0

        clock.advance(1.0)
        session.tick()
        assert session.state == SessionState.CONNECTED
        assert session.reconnect_status.attempt_count == 1
        assert session.is_connected

    def test_reconnect_succeeds_after_multiple_failures(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=5,
        )

        class FailingConnection(SimulatedWebSocketConnection):
            def __init__(self, cid, fail_count):
                super().__init__(cid)
                self.fail_count = fail_count
                self.reconnect_attempts = 0
                self._initial_connected = False

            def connect(self):
                if not self._initial_connected:
                    self._initial_connected = True
                    super().connect()
                    return
                self.reconnect_attempts += 1
                if self.reconnect_attempts <= self.fail_count:
                    raise RuntimeError("simulated failure")
                super().connect()

        conn = FailingConnection("test", fail_count=2)
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.disconnect()

        clock.advance(1.0)
        session.tick()
        assert session.state == SessionState.RECONNECTING
        assert session.reconnect_status.attempt_count == 1

        clock.advance(2.0)
        session.tick()
        assert session.state == SessionState.RECONNECTING
        assert session.reconnect_status.attempt_count == 2

        clock.advance(4.0)
        session.tick()
        assert session.state == SessionState.CONNECTED
        assert session.reconnect_status.attempt_count == 3
        assert conn.reconnect_attempts == 3

    def test_exponential_backoff_timing(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=10,
        )

        class AlwaysFailingConnection(SimulatedWebSocketConnection):
            def connect(self):
                raise RuntimeError("always fails")

        conn = AlwaysFailingConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.tick()
        assert session.reconnect_status.next_attempt_at == 1.0

        clock.advance(1.0)
        session.tick()
        assert session.reconnect_status.attempt_count == 1
        assert session.reconnect_status.next_attempt_at == 3.0

        clock.advance(2.0)
        session.tick()
        assert session.reconnect_status.attempt_count == 2
        assert session.reconnect_status.next_attempt_at == 7.0

        clock.advance(4.0)
        session.tick()
        assert session.reconnect_status.attempt_count == 3
        assert session.reconnect_status.next_attempt_at == 15.0

    def test_reconnect_preserves_session_context(self):
        clock = ManualClock()
        config = ReconnectConfig(initial_delay=1.0, max_attempts=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test-session",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.subscribe("topic-1")
        session.subscribe("topic-2")
        session.set_metadata("user", "alice")

        session.disconnect()
        assert session.state == SessionState.DISCONNECTED

        assert session.is_subscribed("topic-1")
        assert session.is_subscribed("topic-2")
        assert session.get_metadata("user") == "alice"
        assert session.context.session_id == "test-session"

        clock.advance(1.0)
        session.tick()
        assert session.is_connected

        assert session.is_subscribed("topic-1")
        assert session.is_subscribed("topic-2")
        assert session.get_metadata("user") == "alice"
        assert session.context.session_id == "test-session"


class TestReconnectionMaxAttempts:
    def test_max_attempts_stops_reconnection(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=3,
        )

        class AlwaysFailingConnection(SimulatedWebSocketConnection):
            def connect(self):
                raise RuntimeError("always fails")

        conn = AlwaysFailingConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.tick()
        clock.advance(1.0)
        session.tick()
        assert session.reconnect_status.attempt_count == 1

        clock.advance(2.0)
        session.tick()
        assert session.reconnect_status.attempt_count == 2

        clock.advance(4.0)
        with pytest.raises(ReconnectionFailedError) as exc_info:
            session.tick()
        assert exc_info.value.attempts == 3
        assert session.state == SessionState.PERMANENTLY_CLOSED
        assert session.is_closed

    def test_max_attempts_zero_permanently_closed(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            max_attempts=0,
        )
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        assert session.state == SessionState.PERMANENTLY_CLOSED
        assert session.is_closed

    def test_max_attempts_zero_disconnect_becomes_permanent(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            max_attempts=0,
        )
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        assert session.is_connected
        session.disconnect()
        assert session.state == SessionState.PERMANENTLY_CLOSED
        assert session.is_closed

    def test_max_delay_capping(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=5.0,
            max_attempts=10,
        )

        class AlwaysFailingConnection(SimulatedWebSocketConnection):
            def connect(self):
                raise RuntimeError("always fails")

        conn = AlwaysFailingConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        delays = []
        session.tick()

        for i in range(8):
            next_attempt = session.reconnect_status.next_attempt_at
            current_time = clock.now()
            wait_time = next_attempt - current_time
            delays.append(wait_time)
            clock.advance(wait_time)
            try:
                session.tick()
            except ReconnectionFailedError:
                break

        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
        assert delays[3] == 5.0
        assert delays[4] == 5.0


class TestReconnectionCallbacks:
    def test_on_disconnect_callback(self):
        clock = ManualClock()
        config = ReconnectConfig(initial_delay=1.0, max_attempts=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()

        disconnect_called = [0]

        def on_disconnect():
            disconnect_called[0] += 1

        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
            on_disconnect=on_disconnect,
        )

        session.disconnect()
        assert disconnect_called[0] == 1

    def test_on_reconnect_callback(self):
        clock = ManualClock()
        config = ReconnectConfig(initial_delay=1.0, max_attempts=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()

        reconnect_called = [0]

        def on_reconnect():
            reconnect_called[0] += 1

        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
            on_reconnect=on_reconnect,
        )

        session.disconnect()
        assert reconnect_called[0] == 0

        clock.advance(1.0)
        session.tick()
        assert reconnect_called[0] == 1


class TestReconnectionEdgeCases:
    def test_reconnect_while_already_connected_noop(self):
        clock = ManualClock()
        config = ReconnectConfig(initial_delay=1.0, max_attempts=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        assert session.is_connected
        session.tick()
        assert session.is_connected
        assert session.reconnect_status.attempt_count == 0

    def test_disconnect_during_reconnection_resets(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=2.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=5,
        )

        class FailingConnection(SimulatedWebSocketConnection):
            def __init__(self, cid):
                super().__init__(cid)
                self.connect_calls = 0
                self._initial = True

            def connect(self):
                if self._initial:
                    self._initial = False
                    super().connect()
                    return
                self.connect_calls += 1
                super().connect()

        conn = FailingConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.disconnect()
        session.tick()
        assert session.state == SessionState.RECONNECTING
        assert session.reconnect_status.next_attempt_at == 2.0

        clock.advance(1.0)
        session.disconnect()
        assert session.state == SessionState.DISCONNECTED

        session.tick()
        assert session.state == SessionState.RECONNECTING
        assert session.reconnect_status.next_attempt_at == 3.0

        clock.advance(2.0)
        session.tick()
        assert session.is_connected
        assert conn.connect_calls == 1

    def test_reconnect_success_then_disconnect_again(self):
        clock = ManualClock()
        config = ReconnectConfig(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            max_attempts=5,
        )
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        session.disconnect()
        clock.advance(1.0)
        session.tick()
        assert session.is_connected
        assert session.reconnect_status.attempt_count == 1

        session.disconnect()
        assert session.state == SessionState.DISCONNECTED
        assert session.reconnect_status.attempt_count == 0

        clock.advance(1.0)
        session.tick()
        assert session.is_connected
        assert session.reconnect_status.attempt_count == 1

    def test_reconnect_status_snapshot(self):
        clock = ManualClock()
        config = ReconnectConfig(initial_delay=1.0, max_attempts=3)
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            reconnect_config=config,
            clock=clock,
        )

        status1 = session.reconnect_status
        session.tick()
        status2 = session.reconnect_status

        assert status1.attempt_count == 0
        assert status2.attempt_count == 0
        assert status2.next_attempt_at == 1.0
