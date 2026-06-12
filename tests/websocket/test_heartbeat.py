from __future__ import annotations

import pytest

from solocoder_py.websocket import (
    HeartbeatConfig,
    ManualClock,
    MessageType,
    SessionState,
    SimulatedWebSocketConnection,
    WebSocketSession,
    create_connected_pair,
)


class TestHeartbeatNormalFlow:
    def test_heartbeat_ping_sent_periodically(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=10.0, pong_timeout=5.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test-session",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        assert session.heartbeat_status.ping_count == 0

        clock.advance(9.9)
        session.tick()
        assert session.heartbeat_status.ping_count == 0

        clock.advance(0.2)
        session.tick()
        assert session.heartbeat_status.ping_count == 1
        assert conn.outgoing_queue_size == 1

        ping_msg = conn.pop_outgoing()
        assert ping_msg is not None
        assert ping_msg.type == MessageType.PING

    def test_pong_reply_resets_missed_count(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=10.0, pong_timeout=5.0, max_missed_pongs=3)
        client, server = create_connected_pair("client", "server")
        session = WebSocketSession(
            session_id="test",
            connection=client,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(10.0)
        session.tick()
        assert session.heartbeat_status.ping_count == 1

        clock.advance(10.0)
        session.tick()
        assert session.heartbeat_status.ping_count == 2
        assert session.heartbeat_status.missed_pongs == 1

        server.send_pong()
        session.tick()
        assert session.heartbeat_status.pong_count == 1
        assert session.heartbeat_status.missed_pongs == 0

    def test_session_stays_alive_with_pongs(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=3.0, max_missed_pongs=3)
        client, server = create_connected_pair()
        session = WebSocketSession(
            session_id="test",
            connection=client,
            heartbeat_config=config,
            clock=clock,
        )

        for i in range(10):
            clock.advance(5.0)
            session.tick()
            server.send_pong()
            session.tick()

        assert session.is_connected
        assert session.heartbeat_status.ping_count == 10
        assert session.heartbeat_status.pong_count == 10
        assert session.heartbeat_status.missed_pongs == 0

    def test_heartbeat_disabled_not_triggered(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=100.0, pong_timeout=50.0, max_missed_pongs=10)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(50.0)
        session.tick()
        assert session.heartbeat_status.ping_count == 0
        assert session.is_connected


class TestHeartbeatTimeout:
    def test_single_missed_pong_not_enough(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=10.0, pong_timeout=5.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(10.0)
        session.tick()
        assert session.heartbeat_status.missed_pongs == 0
        assert session.is_connected

        clock.advance(10.0)
        session.tick()
        assert session.heartbeat_status.missed_pongs == 1
        assert session.is_connected

    def test_heartbeat_timeout_disconnects(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(5.0)
        session.tick()
        assert session.is_connected

        clock.advance(5.0)
        session.tick()
        assert session.heartbeat_status.missed_pongs == 1

        clock.advance(5.0)
        session.tick()
        assert session.heartbeat_status.missed_pongs == 2

        clock.advance(5.0)
        session.tick()
        assert session.heartbeat_status.missed_pongs >= 3
        assert not session.is_connected
        assert session.state == SessionState.RECONNECTING

    def test_max_missed_pongs_one_disconnects_quickly(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=1.0, max_missed_pongs=1)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(5.0)
        session.tick()
        assert session.is_connected

        clock.advance(6.0)
        session.tick()
        assert not session.is_connected
        assert session.state == SessionState.RECONNECTING


class TestHeartbeatStatus:
    def test_heartbeat_status_initial(self):
        clock = ManualClock(start_time=100.0)
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        status = session.heartbeat_status
        assert status.ping_count == 0
        assert status.pong_count == 0
        assert status.missed_pongs == 0
        assert status.last_ping_sent_at == 100.0
        assert status.last_pong_received_at == 100.0

    def test_heartbeat_status_is_snapshot(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        status1 = session.heartbeat_status
        clock.advance(10.0)
        session.tick()
        status2 = session.heartbeat_status

        assert status1.ping_count == 0
        assert status2.ping_count == 1


class TestHeartbeatEdgeCases:
    def test_ping_on_disconnected_session_noop(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=1.0, pong_timeout=1.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        assert session.state == SessionState.DISCONNECTED
        clock.advance(10.0)
        session.tick()
        assert session.heartbeat_status.ping_count == 0

    def test_session_connect_resets_heartbeat(self):
        clock = ManualClock()
        config = HeartbeatConfig(ping_interval=5.0, pong_timeout=2.0, max_missed_pongs=3)
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            heartbeat_config=config,
            clock=clock,
        )

        clock.advance(10.0)
        session.connect()
        assert session.is_connected
        assert session.heartbeat_status.ping_count == 0
        assert session.heartbeat_status.missed_pongs == 0
