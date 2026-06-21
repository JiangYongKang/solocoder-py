import time

import pytest

from solocoder_py.cmd_queue import (
    Command,
    CommandNotFoundError,
    CommandQueue,
    CommandStatus,
    DuplicateCommandError,
    InvalidTtlError,
)


class TestFifoOrder:
    def test_commands_dequeued_in_fifo_order(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("first", command_id="cmd-1")
        cmd_queue.enqueue("second", command_id="cmd-2")
        cmd_queue.enqueue("third", command_id="cmd-3")

        cmd1 = cmd_queue.dequeue()
        assert cmd1 is not None
        assert cmd1.id == "cmd-1"
        assert cmd1.payload == "first"
        assert cmd1.status == CommandStatus.SENT

        cmd2 = cmd_queue.dequeue()
        assert cmd2 is not None
        assert cmd2.id == "cmd-2"
        assert cmd2.payload == "second"
        assert cmd2.status == CommandStatus.SENT

        cmd3 = cmd_queue.dequeue()
        assert cmd3 is not None
        assert cmd3.id == "cmd-3"
        assert cmd3.payload == "third"
        assert cmd3.status == CommandStatus.SENT

    def test_enqueue_dequeue_interleaved(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd1 = cmd_queue.dequeue()
        assert cmd1.id == "a"

        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.enqueue("c", command_id="c")

        cmd2 = cmd_queue.dequeue()
        assert cmd2.id == "b"

        cmd3 = cmd_queue.dequeue()
        assert cmd3.id == "c"

    def test_large_number_of_commands_fifo(self, cmd_queue: CommandQueue):
        n = 1000
        for i in range(n):
            cmd_queue.enqueue(f"cmd-{i}", command_id=f"id-{i}")

        assert cmd_queue.size() == n

        for i in range(n):
            cmd = cmd_queue.dequeue()
            assert cmd is not None
            assert cmd.id == f"id-{i}"
            assert cmd.payload == f"cmd-{i}"

        assert cmd_queue.dequeue() is None
        assert cmd_queue.size() == 0


class TestStatusTransition:
    def test_pending_to_sent_on_dequeue(self, cmd_queue: CommandQueue):
        cmd = cmd_queue.enqueue("test", command_id="cmd-1")
        assert cmd.status == CommandStatus.PENDING

        dequeued = cmd_queue.dequeue()
        assert dequeued is not None
        assert dequeued.status == CommandStatus.SENT
        assert dequeued.sent_at is not None

    def test_sent_to_delivered(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd = cmd_queue.dequeue()
        assert cmd is not None
        assert cmd.status == CommandStatus.SENT

        result = cmd_queue.mark_delivered("cmd-1")
        assert result is True

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.DELIVERED

        cmd_obj = cmd_queue.get_command("cmd-1")
        assert cmd_obj.delivered_at is not None

    def test_repeat_deliver_is_idempotent(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd_queue.dequeue()

        first = cmd_queue.mark_delivered("cmd-1")
        assert first is True

        second = cmd_queue.mark_delivered("cmd-1")
        assert second is False

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.DELIVERED

    def test_timeout_status(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd_queue.dequeue()

        result = cmd_queue.mark_timeout("cmd-1")
        assert result is True

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.TIMEOUT

        cmd_obj = cmd_queue.get_command("cmd-1")
        assert cmd_obj.timed_out_at is not None

    def test_repeat_timeout_is_idempotent(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd_queue.dequeue()

        first = cmd_queue.mark_timeout("cmd-1")
        assert first is True

        second = cmd_queue.mark_timeout("cmd-1")
        assert second is False

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.TIMEOUT

    def test_delivered_cannot_be_timed_out(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd_queue.dequeue()
        cmd_queue.mark_delivered("cmd-1")

        result = cmd_queue.mark_timeout("cmd-1")
        assert result is False

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.DELIVERED

    def test_timeout_cannot_be_delivered(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd_queue.dequeue()
        cmd_queue.mark_timeout("cmd-1")

        result = cmd_queue.mark_delivered("cmd-1")
        assert result is False

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.TIMEOUT


class TestBatchQuery:
    def test_list_by_status_pending(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.enqueue("c", command_id="c")
        cmd_queue.dequeue()

        pending = cmd_queue.list_by_status(CommandStatus.PENDING)
        assert len(pending) == 2
        pending_ids = {cmd.id for cmd in pending}
        assert pending_ids == {"b", "c"}

    def test_list_by_status_sent(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.dequeue()
        cmd_queue.dequeue()
        cmd_queue.mark_delivered("a")

        sent = cmd_queue.list_by_status(CommandStatus.SENT)
        assert len(sent) == 1
        assert sent[0].id == "b"

    def test_list_by_status_delivered(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.dequeue()
        cmd_queue.dequeue()
        cmd_queue.mark_delivered("a")
        cmd_queue.mark_delivered("b")

        delivered = cmd_queue.list_by_status(CommandStatus.DELIVERED)
        assert len(delivered) == 2
        delivered_ids = {cmd.id for cmd in delivered}
        assert delivered_ids == {"a", "b"}

    def test_list_by_status_timeout(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.dequeue()
        cmd_queue.dequeue()
        cmd_queue.mark_timeout("a")

        timed_out = cmd_queue.list_by_status(CommandStatus.TIMEOUT)
        assert len(timed_out) == 1
        assert timed_out[0].id == "a"

    def test_list_by_status_empty(self, cmd_queue: CommandQueue):
        result = cmd_queue.list_by_status(CommandStatus.PENDING)
        assert result == []


class TestTtlNormal:
    def test_ttl_not_expired_dequeue_normal(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1", ttl=10.0)

        cmd = cmd_queue.dequeue()
        assert cmd is not None
        assert cmd.id == "cmd-1"
        assert cmd.status == CommandStatus.SENT

    def test_no_ttl_never_expires(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1")
        cmd = cmd_queue.get_command("cmd-1")
        assert cmd.is_expired is False

    def test_ttl_property_on_command(self):
        cmd = Command(id="test", payload="data", ttl=5.0)
        assert cmd.ttl == 5.0
        assert cmd.is_expired is False


class TestTtlBoundary:
    def test_ttl_zero_expires_immediately(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1", ttl=0)

        cmd = cmd_queue.dequeue()
        assert cmd is None

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.TIMEOUT

    def test_all_commands_expired(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a", ttl=0)
        cmd_queue.enqueue("b", command_id="b", ttl=0)
        cmd_queue.enqueue("c", command_id="c", ttl=0)

        assert cmd_queue.dequeue() is None
        assert cmd_queue.size() == 0

        timed_out = cmd_queue.list_by_status(CommandStatus.TIMEOUT)
        assert len(timed_out) == 3

    def test_expired_commands_skipped_in_dequeue(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("expired", command_id="expired", ttl=0)
        cmd_queue.enqueue("valid", command_id="valid", ttl=100)

        cmd = cmd_queue.dequeue()
        assert cmd is not None
        assert cmd.id == "valid"
        assert cmd.status == CommandStatus.SENT

    def test_partial_expired(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a", ttl=0)
        cmd_queue.enqueue("b", command_id="b", ttl=100)
        cmd_queue.enqueue("c", command_id="c", ttl=0)
        cmd_queue.enqueue("d", command_id="d", ttl=100)

        cmd1 = cmd_queue.dequeue()
        assert cmd1 is not None
        assert cmd1.id == "b"

        cmd2 = cmd_queue.dequeue()
        assert cmd2 is not None
        assert cmd2.id == "d"

        assert cmd_queue.dequeue() is None

        timed_out = cmd_queue.list_by_status(CommandStatus.TIMEOUT)
        assert len(timed_out) == 2
        timed_out_ids = {cmd.id for cmd in timed_out}
        assert timed_out_ids == {"a", "c"}

    def test_get_status_triggers_expiry_check(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1", ttl=0)

        status = cmd_queue.get_status("cmd-1")
        assert status == CommandStatus.TIMEOUT

    def test_list_by_status_triggers_expiry_check(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("test", command_id="cmd-1", ttl=0)

        pending = cmd_queue.list_by_status(CommandStatus.PENDING)
        assert len(pending) == 0

        timed_out = cmd_queue.list_by_status(CommandStatus.TIMEOUT)
        assert len(timed_out) == 1


class TestEmptyQueue:
    def test_dequeue_empty_returns_none(self, cmd_queue: CommandQueue):
        assert cmd_queue.dequeue() is None

    def test_size_empty_is_zero(self, cmd_queue: CommandQueue):
        assert cmd_queue.size() == 0

    def test_total_count_empty_is_zero(self, cmd_queue: CommandQueue):
        assert cmd_queue.total_count() == 0


class TestExceptionBranches:
    def test_query_nonexistent_command_status(self, cmd_queue: CommandQueue):
        with pytest.raises(CommandNotFoundError):
            cmd_queue.get_status("nonexistent")

    def test_get_nonexistent_command(self, cmd_queue: CommandQueue):
        with pytest.raises(CommandNotFoundError):
            cmd_queue.get_command("nonexistent")

    def test_mark_delivered_nonexistent(self, cmd_queue: CommandQueue):
        with pytest.raises(CommandNotFoundError):
            cmd_queue.mark_delivered("nonexistent")

    def test_mark_timeout_nonexistent(self, cmd_queue: CommandQueue):
        with pytest.raises(CommandNotFoundError):
            cmd_queue.mark_timeout("nonexistent")

    def test_negative_ttl_raises(self, cmd_queue: CommandQueue):
        with pytest.raises(InvalidTtlError):
            cmd_queue.enqueue("test", command_id="cmd-1", ttl=-1)

    def test_duplicate_command_id_raises(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("first", command_id="same-id")
        with pytest.raises(DuplicateCommandError):
            cmd_queue.enqueue("second", command_id="same-id")

    def test_command_empty_id_raises(self):
        with pytest.raises(ValueError):
            Command(id="", payload="test")

    def test_command_negative_ttl_raises(self):
        with pytest.raises(InvalidTtlError):
            Command(id="test", payload="data", ttl=-5)


class TestQueueSize:
    def test_size_reflects_pending_only(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.enqueue("c", command_id="c")

        assert cmd_queue.size() == 3

        cmd_queue.dequeue()
        assert cmd_queue.size() == 2

        cmd_queue.dequeue()
        assert cmd_queue.size() == 1

        cmd_queue.dequeue()
        assert cmd_queue.size() == 0

    def test_total_count_includes_all(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.dequeue()
        cmd_queue.mark_delivered("a")

        assert cmd_queue.size() == 1
        assert cmd_queue.total_count() == 2


class TestClear:
    def test_clear_resets_queue(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("a", command_id="a")
        cmd_queue.enqueue("b", command_id="b")
        cmd_queue.dequeue()

        cmd_queue.clear()

        assert cmd_queue.size() == 0
        assert cmd_queue.total_count() == 0
        assert cmd_queue.dequeue() is None


class TestTtlLazyExpiry:
    def test_expiry_checked_lazily_on_dequeue(self, cmd_queue: CommandQueue):
        cmd = cmd_queue.enqueue("test", command_id="cmd-1", ttl=0.05)

        initial_status = cmd_queue.get_status("cmd-1")
        assert initial_status == CommandStatus.PENDING

        time.sleep(0.1)

        result = cmd_queue.dequeue()
        assert result is None

        final_status = cmd_queue.get_status("cmd-1")
        assert final_status == CommandStatus.TIMEOUT

    def test_short_ttl_expires(self, cmd_queue: CommandQueue):
        cmd_queue.enqueue("short", command_id="short", ttl=0.05)
        cmd_queue.enqueue("long", command_id="long", ttl=100)

        time.sleep(0.1)

        cmd = cmd_queue.dequeue()
        assert cmd is not None
        assert cmd.id == "long"
