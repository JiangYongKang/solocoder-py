from __future__ import annotations

import pytest

from solocoder_py.websocket import (
    HeartbeatConfig,
    ManualClock,
    Message,
    MessageType,
    ReconnectConfig,
    ReorderConfig,
    SessionClosedError,
    SessionState,
    SimulatedWebSocketConnection,
    WebSocketSession,
    create_connected_pair,
)


class TestSessionMessageFlow:
    def test_send_and_receive_in_order(self):
        clock = ManualClock()
        client, server = create_connected_pair("client", "server")
        session = WebSocketSession(
            session_id="test",
            connection=client,
            clock=clock,
        )

        seq0 = session.send("msg-0")
        seq1 = session.send("msg-1")
        seq2 = session.send("msg-2")

        assert seq0 == 0
        assert seq1 == 1
        assert seq2 == 2
        assert session.send_sequence == 3

        assert server.incoming_queue_size == 3

        msg0 = server.receive()
        assert msg0 is not None
        assert msg0.sequence == 0
        assert msg0.payload == "msg-0"
        assert msg0.type == MessageType.DATA

    def test_receive_reordered_messages(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        session = WebSocketSession(
            session_id="test",
            connection=client,
            reorder_config=ReorderConfig(max_buffer_size=10, wait_timeout=30.0),
            clock=clock,
        )

        server.send_data(sequence=2, payload="msg-2")
        server.send_data(sequence=0, payload="msg-0")

        delivered = session.receive()
        assert len(delivered) == 1
        assert delivered[0].sequence == 0
        assert delivered[0].payload == "msg-0"
        assert session.reorder_buffer_size == 1

        server.send_data(sequence=1, payload="msg-1")
        delivered = session.receive()
        assert len(delivered) == 2
        seqs = [m.sequence for m in delivered]
        assert seqs == [1, 2]
        assert session.reorder_buffer_size == 0

    def test_on_message_callback(self):
        clock = ManualClock()
        client, server = create_connected_pair()

        received = []

        def on_message(msg):
            received.append(msg)

        session = WebSocketSession(
            session_id="test",
            connection=client,
            clock=clock,
            on_message=on_message,
        )

        server.send_data(sequence=0, payload="hello")
        session.receive()

        assert len(received) == 1
        assert received[0].payload == "hello"
        assert received[0].sequence == 0


class TestSessionStateTransitions:
    def test_initial_disconnected_state(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )
        assert session.state == SessionState.DISCONNECTED
        assert not session.is_connected
        assert not session.is_closed

    def test_connect_transitions_to_connected(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.connect()
        assert session.state == SessionState.CONNECTED
        assert session.is_connected
        assert not session.is_closed

    def test_disconnect_transitions_to_disconnected(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.disconnect()
        assert session.state == SessionState.DISCONNECTED
        assert not session.is_connected
        assert not session.is_closed

    def test_close_permanently_closes(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.close()
        assert session.state == SessionState.PERMANENTLY_CLOSED
        assert session.is_closed
        assert not session.is_connected


class TestSessionClosedError:
    def test_send_on_closed_session_raises(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.close()
        with pytest.raises(SessionClosedError) as exc_info:
            session.send("test")
        assert exc_info.value.session_id == "test"

    def test_receive_on_closed_session_raises(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="my-session",
            connection=conn,
            clock=clock,
        )

        session.close()
        with pytest.raises(SessionClosedError) as exc_info:
            session.receive()
        assert exc_info.value.session_id == "my-session"

    def test_connect_on_closed_session_raises(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.close()
        with pytest.raises(SessionClosedError):
            session.connect()


class TestSessionContext:
    def test_subscribe_unsubscribe(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        assert not session.is_subscribed("topic-1")

        session.subscribe("topic-1")
        assert session.is_subscribed("topic-1")

        session.subscribe("topic-2")
        assert session.is_subscribed("topic-2")

        session.unsubscribe("topic-1")
        assert not session.is_subscribed("topic-1")
        assert session.is_subscribed("topic-2")

    def test_metadata(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        assert session.get_metadata("key") is None

        session.set_metadata("key", "value")
        assert session.get_metadata("key") == "value"

        session.set_metadata("num", 42)
        assert session.get_metadata("num") == 42

    def test_context_clone_is_independent(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.subscribe("topic-1")
        ctx = session.context
        ctx.subscribed_topics.add("topic-2")

        assert not session.is_subscribed("topic-2")
        assert "topic-1" in ctx.subscribed_topics


class TestSessionSequenceOverflow:
    def test_send_sequence_wraparound(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        reorder_config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0, max_sequence=9)
        session = WebSocketSession(
            session_id="test",
            connection=client,
            reorder_config=reorder_config,
            clock=clock,
        )

        for i in range(10):
            seq = session.send(f"msg-{i}")
            assert seq == i

        seq10 = session.send("msg-10")
        assert seq10 == 0

    def test_receive_sequence_wraparound(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        reorder_config = ReorderConfig(max_buffer_size=10, wait_timeout=30.0, max_sequence=99)
        session = WebSocketSession(
            session_id="test",
            connection=client,
            reorder_config=reorder_config,
            clock=clock,
        )

        for i in range(95):
            server.send_data(sequence=i, payload=f"msg-{i}")

        delivered = session.receive()
        assert len(delivered) == 95

        server.send_data(sequence=96, payload="msg-96")
        server.send_data(sequence=98, payload="msg-98")
        server.send_data(sequence=0, payload="msg-0-wrap")
        server.send_data(sequence=95, payload="msg-95")
        server.send_data(sequence=97, payload="msg-97")
        server.send_data(sequence=99, payload="msg-99")

        delivered = session.receive()
        assert len(delivered) == 6
        seqs = [m.sequence for m in delivered]
        assert seqs == [95, 96, 97, 98, 99, 0]


class TestSessionReorderTimeout:
    def test_reorder_timeout_skips_missing(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        reorder_config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        session = WebSocketSession(
            session_id="test",
            connection=client,
            reorder_config=reorder_config,
            clock=clock,
        )

        server.send_data(sequence=1, payload="msg-1")
        server.send_data(sequence=2, payload="msg-2")
        delivered = session.receive()
        assert len(delivered) == 0
        assert session.reorder_buffer_size == 2

        clock.advance(6.0)
        delivered = session.receive()
        assert len(delivered) == 2
        seqs = [m.sequence for m in delivered]
        assert seqs == [1, 2]
        assert session.reorder_buffer_size == 0


class TestSessionEdgeCases:
    def test_send_sequence_starts_at_zero(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        session = WebSocketSession(
            session_id="test",
            connection=client,
            clock=clock,
        )
        assert session.send_sequence == 0

    def test_flush_reorder_buffer(self):
        clock = ManualClock()
        client, server = create_connected_pair()
        reorder_config = ReorderConfig(max_buffer_size=10, wait_timeout=30.0)
        session = WebSocketSession(
            session_id="test",
            connection=client,
            reorder_config=reorder_config,
            clock=clock,
        )

        server.send_data(sequence=2, payload="msg-2")
        server.send_data(sequence=3, payload="msg-3")
        session.receive()
        assert session.reorder_buffer_size == 2

        flushed = session.flush_reorder_buffer()
        assert len(flushed) == 2
        assert session.reorder_buffer_size == 0

    def test_double_close_is_safe(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.close()
        session.close()
        assert session.is_closed

    def test_tick_on_closed_session_noop(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        conn.connect()
        session = WebSocketSession(
            session_id="test",
            connection=conn,
            clock=clock,
        )

        session.close()
        session.tick()
        assert session.is_closed

    def test_session_id_preserved(self):
        clock = ManualClock()
        conn = SimulatedWebSocketConnection("test")
        session = WebSocketSession(
            session_id="my-custom-id",
            connection=conn,
            clock=clock,
        )
        assert session.session_id == "my-custom-id"
        assert session.context.session_id == "my-custom-id"
