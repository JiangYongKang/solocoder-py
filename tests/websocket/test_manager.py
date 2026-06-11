from __future__ import annotations

import pytest

from solocoder_py.websocket import (
    HeartbeatConfig,
    ManualClock,
    ReconnectConfig,
    ReorderConfig,
    SessionManager,
    SessionNotFoundError,
    SessionState,
    SimulatedWebSocketConnection,
)


class TestSessionManagerCreateAndGet:
    def test_create_session_with_id(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        session = manager.create_session(session_id="sess-1")
        assert session.session_id == "sess-1"
        assert manager.has_session("sess-1")
        assert manager.session_count == 1

    def test_create_session_auto_generated_id(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        session = manager.create_session()
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert manager.session_count == 1

    def test_get_existing_session(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        manager.create_session(session_id="sess-1")
        session = manager.get_session("sess-1")
        assert session.session_id == "sess-1"

    def test_get_nonexistent_session_raises(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        with pytest.raises(SessionNotFoundError) as exc_info:
            manager.get_session("nonexistent")
        assert exc_info.value.session_id == "nonexistent"

    def test_has_session(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        assert not manager.has_session("sess-1")
        manager.create_session(session_id="sess-1")
        assert manager.has_session("sess-1")

    def test_create_multiple_sessions(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(5):
            manager.create_session(session_id=f"sess-{i}")

        assert manager.session_count == 5
        for i in range(5):
            assert manager.has_session(f"sess-{i}")


class TestSessionManagerRemove:
    def test_remove_session(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        manager.create_session(session_id="sess-1")
        assert manager.session_count == 1

        manager.remove_session("sess-1")
        assert manager.session_count == 0
        assert not manager.has_session("sess-1")

    def test_remove_nonexistent_session_noop(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        manager.remove_session("nonexistent")
        assert manager.session_count == 0

    def test_close_session(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        manager.create_session(session_id="sess-1", connection=conn)

        session = manager.get_session("sess-1")
        assert session.is_connected

        manager.close_session("sess-1")
        assert session.is_closed


class TestSessionManagerTick:
    def test_tick_all_sessions(self):
        clock = ManualClock()
        heartbeat_config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)
        manager = SessionManager(heartbeat_config=heartbeat_config, clock=clock)

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        assert manager.connected_count == 3

        clock.advance(10.0)
        manager.tick_all()

        for i in range(3):
            session = manager.get_session(f"sess-{i}")
            assert session.heartbeat_status.ping_count >= 1

    def test_tick_removes_permanently_closed(self):
        clock = ManualClock()
        reconnect_config = ReconnectConfig(initial_delay=1.0, max_attempts=1)
        manager = SessionManager(reconnect_config=reconnect_config, clock=clock)

        class AlwaysFailingConnection(SimulatedWebSocketConnection):
            def connect(self):
                raise RuntimeError("fail")

        conn = AlwaysFailingConnection("test")
        manager.create_session(session_id="sess-1", connection=conn)

        assert manager.session_count == 1

        clock.advance(2.0)
        manager.tick_all()

        assert manager.session_count == 0


class TestSessionManagerBroadcast:
    def test_broadcast_to_connected_sessions(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        results = manager.broadcast("hello")
        assert len(results) == 3
        assert all(v is True for v in results.values())

    def test_broadcast_skips_disconnected(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        conn1 = SimulatedWebSocketConnection("conn-1")
        conn1.connect()
        manager.create_session(session_id="sess-1", connection=conn1)

        conn2 = SimulatedWebSocketConnection("conn-2")
        manager.create_session(session_id="sess-2", connection=conn2)

        results = manager.broadcast("hello")
        assert results["sess-1"] is True
        assert results["sess-2"] is False


class TestSessionManagerTopics:
    def test_subscribe_all(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        manager.subscribe_all("news")
        subscribed = manager.get_subscribed_sessions("news")
        assert len(subscribed) == 3

    def test_unsubscribe_all(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        manager.subscribe_all("news")
        manager.unsubscribe_all("news")
        subscribed = manager.get_subscribed_sessions("news")
        assert len(subscribed) == 0

    def test_publish_to_topic(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        manager.get_session("sess-0").subscribe("news")
        manager.get_session("sess-1").subscribe("news")

        results = manager.publish_to_topic("news", "breaking news")
        assert len(results) == 2
        assert "sess-0" in results
        assert "sess-1" in results
        assert "sess-2" not in results


class TestSessionManagerCloseAll:
    def test_close_all(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(5):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        assert manager.session_count == 5

        manager.close_all()
        assert manager.session_count == 0


class TestSessionManagerConfig:
    def test_custom_config_applied_to_new_sessions(self):
        clock = ManualClock()
        heartbeat_config = HeartbeatConfig(ping_interval=15.0, pong_timeout=8.0, max_missed_pongs=5)
        reconnect_config = ReconnectConfig(initial_delay=2.0, max_delay=30.0, max_attempts=10)
        reorder_config = ReorderConfig(max_buffer_size=50, wait_timeout=10.0)

        manager = SessionManager(
            heartbeat_config=heartbeat_config,
            reconnect_config=reconnect_config,
            reorder_config=reorder_config,
            clock=clock,
        )

        session = manager.create_session(session_id="sess-1")
        assert session.reorder_buffer_size == 0


class TestSessionManagerQuery:
    def test_get_all_sessions(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        for i in range(3):
            manager.create_session(session_id=f"sess-{i}")

        all_sessions = manager.get_all_sessions()
        assert len(all_sessions) == 3

    def test_get_sessions_by_state(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        conn = SimulatedWebSocketConnection("conn-1")
        conn.connect()
        manager.create_session(session_id="connected", connection=conn)
        manager.create_session(session_id="disconnected")

        connected = manager.get_sessions_by_state(SessionState.CONNECTED)
        assert len(connected) == 1
        assert connected[0].session_id == "connected"

        disconnected = manager.get_sessions_by_state(SessionState.DISCONNECTED)
        assert len(disconnected) == 1
        assert disconnected[0].session_id == "disconnected"

    def test_connected_count(self):
        clock = ManualClock()
        manager = SessionManager(clock=clock)

        assert manager.connected_count == 0

        for i in range(3):
            conn = SimulatedWebSocketConnection(f"conn-{i}")
            if i < 2:
                conn.connect()
            manager.create_session(session_id=f"sess-{i}", connection=conn)

        assert manager.connected_count == 2
