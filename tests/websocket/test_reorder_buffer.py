from __future__ import annotations

import pytest

from solocoder_py.websocket import (
    ManualClock,
    Message,
    MessageType,
    ReorderBuffer,
    ReorderConfig,
    ReorderBufferOverflowError,
)


class TestReorderBufferNormalFlow:
    def test_in_order_messages_delivered_immediately(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        msg0 = Message(sequence=0, payload="msg-0", type=MessageType.DATA)
        msg1 = Message(sequence=1, payload="msg-1", type=MessageType.DATA)
        msg2 = Message(sequence=2, payload="msg-2", type=MessageType.DATA)

        delivered0 = buffer.receive(msg0)
        assert len(delivered0) == 1
        assert delivered0[0].sequence == 0
        assert buffer.next_expected == 1
        assert buffer.buffer_size == 0

        delivered1 = buffer.receive(msg1)
        assert len(delivered1) == 1
        assert delivered1[0].sequence == 1
        assert buffer.next_expected == 2

        delivered2 = buffer.receive(msg2)
        assert len(delivered2) == 1
        assert delivered2[0].sequence == 2
        assert buffer.next_expected == 3

    def test_out_of_order_messages_reordered(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        msg0 = Message(sequence=0, payload="msg-0", type=MessageType.DATA)
        msg1 = Message(sequence=1, payload="msg-1", type=MessageType.DATA)
        msg2 = Message(sequence=2, payload="msg-2", type=MessageType.DATA)

        delivered1 = buffer.receive(msg1)
        assert len(delivered1) == 0
        assert buffer.buffer_size == 1
        assert buffer.next_expected == 0

        delivered2 = buffer.receive(msg2)
        assert len(delivered2) == 0
        assert buffer.buffer_size == 2
        assert buffer.next_expected == 0

        delivered0 = buffer.receive(msg0)
        assert len(delivered0) == 3
        assert [m.sequence for m in delivered0] == [0, 1, 2]
        assert buffer.next_expected == 3
        assert buffer.buffer_size == 0

    def test_partial_gap_fill(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        msg0 = Message(sequence=0, payload="msg-0", type=MessageType.DATA)
        msg2 = Message(sequence=2, payload="msg-2", type=MessageType.DATA)
        msg3 = Message(sequence=3, payload="msg-3", type=MessageType.DATA)

        buffer.receive(msg2)
        buffer.receive(msg3)
        assert buffer.buffer_size == 2

        delivered = buffer.receive(msg0)
        assert len(delivered) == 1
        assert delivered[0].sequence == 0
        assert buffer.next_expected == 1
        assert buffer.buffer_size == 2

    def test_buffer_empty_receive_next_expected_delivers(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock, initial_next_expected=5)

        msg = Message(sequence=5, payload="msg-5", type=MessageType.DATA)
        delivered = buffer.receive(msg)
        assert len(delivered) == 1
        assert delivered[0].sequence == 5
        assert buffer.buffer_size == 0

    def test_old_messages_ignored(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock, initial_next_expected=5)

        msg = Message(sequence=2, payload="old", type=MessageType.DATA)
        delivered = buffer.receive(msg)
        assert len(delivered) == 0
        assert buffer.buffer_size == 0
        assert buffer.next_expected == 5


class TestReorderBufferTimeout:
    def test_timeout_skips_gap_and_delivers(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        msg2 = Message(sequence=2, payload="msg-2", type=MessageType.DATA)
        msg3 = Message(sequence=3, payload="msg-3", type=MessageType.DATA)

        buffer.receive(msg2)
        buffer.receive(msg3)
        assert buffer.buffer_size == 2

        clock.advance(4.9)
        delivered = buffer.check_timeout()
        assert len(delivered) == 0
        assert buffer.buffer_size == 2

        clock.advance(0.2)
        delivered = buffer.check_timeout()
        assert len(delivered) == 2
        assert [m.sequence for m in delivered] == [2, 3]
        assert buffer.next_expected == 4
        assert buffer.buffer_size == 0

    def test_no_timeout_when_buffer_empty(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        clock.advance(10.0)
        delivered = buffer.check_timeout()
        assert len(delivered) == 0

    def test_timeout_resets_after_gap_filled_and_new_gap(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        msg1 = Message(sequence=1, payload="msg-1", type=MessageType.DATA)
        msg3 = Message(sequence=3, payload="msg-3", type=MessageType.DATA)

        buffer.receive(msg1)
        clock.advance(3.0)

        msg0 = Message(sequence=0, payload="msg-0", type=MessageType.DATA)
        buffer.receive(msg0)
        assert buffer.buffer_size == 0
        assert buffer.next_expected == 2

        buffer.receive(msg3)
        assert buffer.buffer_size == 1

        clock.advance(3.0)
        delivered = buffer.check_timeout()
        assert len(delivered) == 0

        clock.advance(3.0)
        delivered = buffer.check_timeout()
        assert len(delivered) == 1
        assert delivered[0].sequence == 3


class TestReorderBufferOverflow:
    def test_buffer_overflow_raises_error(self, clock):
        config = ReorderConfig(max_buffer_size=3, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        buffer.receive(Message(sequence=1, payload="1", type=MessageType.DATA))
        buffer.receive(Message(sequence=2, payload="2", type=MessageType.DATA))
        buffer.receive(Message(sequence=3, payload="3", type=MessageType.DATA))
        assert buffer.buffer_size == 3

        with pytest.raises(ReorderBufferOverflowError):
            buffer.receive(Message(sequence=4, payload="4", type=MessageType.DATA))

    def test_large_sequence_jump_causes_overflow(self, clock):
        config = ReorderConfig(max_buffer_size=5, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        for i in range(1, 6):
            buffer.receive(Message(sequence=i, payload=f"msg-{i}", type=MessageType.DATA))

        assert buffer.buffer_size == 5

        with pytest.raises(ReorderBufferOverflowError):
            buffer.receive(Message(sequence=100, payload="far", type=MessageType.DATA))


class TestReorderBufferSequenceOverflow:
    def test_sequence_wraparound_handling(self, clock):
        max_seq = 99
        config = ReorderConfig(max_buffer_size=20, wait_timeout=5.0, max_sequence=max_seq)
        buffer = ReorderBuffer(config=config, clock=clock, initial_next_expected=95)

        msg95 = Message(sequence=95, payload="95", type=MessageType.DATA)
        msg96 = Message(sequence=96, payload="96", type=MessageType.DATA)
        msg97 = Message(sequence=97, payload="97", type=MessageType.DATA)
        msg98 = Message(sequence=98, payload="98", type=MessageType.DATA)
        msg99 = Message(sequence=99, payload="99", type=MessageType.DATA)
        msg0 = Message(sequence=0, payload="0", type=MessageType.DATA)
        msg1 = Message(sequence=1, payload="1", type=MessageType.DATA)

        d = buffer.receive(msg95)
        assert len(d) == 1 and d[0].sequence == 95

        d = buffer.receive(msg96)
        assert len(d) == 1 and d[0].sequence == 96

        buffer.receive(msg98)
        buffer.receive(msg99)
        buffer.receive(msg0)
        buffer.receive(msg1)
        assert buffer.buffer_size == 4

        d = buffer.receive(msg97)
        assert len(d) == 5
        seqs = [m.sequence for m in d]
        assert seqs == [97, 98, 99, 0, 1]
        assert buffer.next_expected == 2

    def test_wraparound_gap_timeout(self, clock):
        max_seq = 99
        config = ReorderConfig(max_buffer_size=20, wait_timeout=5.0, max_sequence=max_seq)
        buffer = ReorderBuffer(config=config, clock=clock, initial_next_expected=97)

        buffer.receive(Message(sequence=99, payload="99", type=MessageType.DATA))
        buffer.receive(Message(sequence=0, payload="0", type=MessageType.DATA))
        buffer.receive(Message(sequence=1, payload="1", type=MessageType.DATA))
        assert buffer.buffer_size == 3

        clock.advance(6.0)
        delivered = buffer.check_timeout()
        assert len(delivered) == 3
        seqs = [m.sequence for m in delivered]
        assert seqs == [99, 0, 1]
        assert buffer.next_expected == 2


class TestReorderBufferEdgeCases:
    def test_initial_next_expected_custom_value(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock, initial_next_expected=42)

        assert buffer.next_expected == 42

        msg = Message(sequence=42, payload="x", type=MessageType.DATA)
        delivered = buffer.receive(msg)
        assert len(delivered) == 1
        assert buffer.next_expected == 43

    def test_reset_buffer(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        buffer.receive(Message(sequence=2, payload="2", type=MessageType.DATA))
        buffer.receive(Message(sequence=3, payload="3", type=MessageType.DATA))
        assert buffer.buffer_size == 2

        buffer.reset(next_expected=10)
        assert buffer.buffer_size == 0
        assert buffer.next_expected == 10

        msg = Message(sequence=10, payload="10", type=MessageType.DATA)
        delivered = buffer.receive(msg)
        assert len(delivered) == 1
        assert delivered[0].sequence == 10

    def test_force_flush_empty_buffer(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        delivered = buffer.force_flush()
        assert len(delivered) == 0

    def test_force_flush_delivers_all_buffered(self, clock):
        config = ReorderConfig(max_buffer_size=10, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        buffer.receive(Message(sequence=3, payload="3", type=MessageType.DATA))
        buffer.receive(Message(sequence=1, payload="1", type=MessageType.DATA))
        buffer.receive(Message(sequence=2, payload="2", type=MessageType.DATA))

        delivered = buffer.force_flush()
        assert len(delivered) == 3
        assert [m.sequence for m in delivered] == [1, 2, 3]
        assert buffer.buffer_size == 0

    def test_max_buffer_size_1(self, clock):
        config = ReorderConfig(max_buffer_size=1, wait_timeout=5.0)
        buffer = ReorderBuffer(config=config, clock=clock)

        buffer.receive(Message(sequence=1, payload="1", type=MessageType.DATA))
        assert buffer.buffer_size == 1

        with pytest.raises(ReorderBufferOverflowError):
            buffer.receive(Message(sequence=2, payload="2", type=MessageType.DATA))

        msg0 = Message(sequence=0, payload="0", type=MessageType.DATA)
        delivered = buffer.receive(msg0)
        assert len(delivered) == 2
        assert [m.sequence for m in delivered] == [0, 1]
        assert buffer.buffer_size == 0
