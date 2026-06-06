from datetime import datetime, timedelta
import time

import pytest

from solocoder_py.queue import (
    DuplicateMessageError,
    Message,
    MessageNotFoundError,
    MessageQueue,
    MessageStatus,
    QueueError,
)


class TestPriorityEnqueueDequeue:
    def test_higher_priority_dequeued_first(self, queue: MessageQueue):
        queue.enqueue("q", "low", priority=1)
        queue.enqueue("q", "high", priority=10)
        queue.enqueue("q", "medium", priority=5)

        msg1 = queue.dequeue("q")
        assert msg1.body == "high"
        assert msg1.priority == 10

        msg2 = queue.dequeue("q")
        assert msg2.body == "medium"
        assert msg2.priority == 5

        msg3 = queue.dequeue("q")
        assert msg3.body == "low"
        assert msg3.priority == 1

    def test_same_priority_fifo_order(self, queue: MessageQueue):
        queue.enqueue("q", "first", priority=5)
        queue.enqueue("q", "second", priority=5)
        queue.enqueue("q", "third", priority=5)

        assert queue.dequeue("q").body == "first"
        assert queue.dequeue("q").body == "second"
        assert queue.dequeue("q").body == "third"

    def test_default_priority_is_zero(self, queue: MessageQueue):
        msg = queue.enqueue("q", "default")
        assert msg.priority == 0

    def test_mixed_priority_and_default(self, queue: MessageQueue):
        queue.enqueue("q", "default")
        queue.enqueue("q", "high", priority=10)
        queue.enqueue("q", "low", priority=-1)

        assert queue.dequeue("q").body == "high"
        assert queue.dequeue("q").body == "default"
        assert queue.dequeue("q").body == "low"


class TestMessageAcknowledge:
    def test_acknowledge_removes_message(self, queue: MessageQueue):
        msg = queue.enqueue("q", "body")
        dequeued = queue.dequeue("q")
        assert dequeued.id == msg.id

        queue.acknowledge(dequeued.id)

        assert queue.dequeue("q") is None
        assert queue.get_queue_size("q") == 0

    def test_acknowledge_nonexistent_raises(self, queue: MessageQueue):
        with pytest.raises(MessageNotFoundError):
            queue.acknowledge("nonexistent-id")


class TestDelayedDelivery:
    def test_delayed_message_not_visible_before_time(self, queue: MessageQueue):
        future = datetime.now() + timedelta(seconds=2)
        queue.enqueue("q", "delayed", deliver_at=future)
        queue.enqueue("q", "now")

        msg = queue.dequeue("q")
        assert msg.body == "now"
        assert queue.dequeue("q") is None

    def test_delayed_message_visible_after_time(self, queue: MessageQueue):
        past = datetime.now() + timedelta(milliseconds=10)
        queue.enqueue("q", "delayed", deliver_at=past)

        time.sleep(0.05)

        msg = queue.dequeue("q")
        assert msg is not None
        assert msg.body == "delayed"

    def test_delayed_with_priority(self, queue: MessageQueue):
        future = datetime.now() + timedelta(seconds=2)
        queue.enqueue("q", "high-but-delayed", priority=100, deliver_at=future)
        queue.enqueue("q", "low-now", priority=1)

        msg = queue.dequeue("q")
        assert msg.body == "low-now"


class TestVisibilityTimeout:
    def test_message_invisible_after_dequeue(self, queue: MessageQueue):
        queue.enqueue("q", "msg1")
        queue.enqueue("q", "msg2")

        msg1 = queue.dequeue("q", visibility_timeout=timedelta(seconds=10))
        assert msg1 is not None
        assert msg1.status == MessageStatus.IN_FLIGHT

        msg2 = queue.dequeue("q")
        assert msg2.body == "msg2"

        assert queue.dequeue("q") is None

    def test_message_visible_after_timeout(self, queue: MessageQueue):
        queue.enqueue("q", "only", visibility_timeout=timedelta(milliseconds=50))

        msg1 = queue.dequeue("q")
        assert msg1 is not None
        assert queue.dequeue("q") is None

        time.sleep(0.1)

        msg2 = queue.dequeue("q")
        assert msg2 is not None
        assert msg2.id == msg1.id
        assert msg2.receive_count == 2

    def test_retry_makes_visible_immediately(self, queue: MessageQueue):
        queue.enqueue("q", "msg", visibility_timeout=timedelta(seconds=30))

        msg = queue.dequeue("q")
        assert msg is not None
        assert queue.dequeue("q") is None

        queue.retry(msg.id)

        msg2 = queue.dequeue("q")
        assert msg2 is not None
        assert msg2.id == msg.id

    def test_retry_not_inflight_raises(self, queue: MessageQueue):
        msg = queue.enqueue("q", "body")
        with pytest.raises(QueueError):
            queue.retry(msg.id)

    def test_retry_nonexistent_raises(self, queue: MessageQueue):
        with pytest.raises(MessageNotFoundError):
            queue.retry("nonexistent")


class TestDeadLetterAndRetry:
    def test_exceeds_max_retries_goes_to_dlq(self, queue: MessageQueue):
        queue.enqueue("q", "bad", max_retry_count=2, visibility_timeout=timedelta(milliseconds=10))

        queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")
        time.sleep(0.02)

        msg = queue.dequeue("q")
        assert msg is None

        dlq = queue.peek_dead_letters("q")
        assert len(dlq) == 1
        assert dlq[0].body == "bad"
        assert dlq[0].status == MessageStatus.DEAD_LETTER
        assert dlq[0].receive_count == 3

    def test_dead_letter_count(self, queue: MessageQueue):
        queue.enqueue("q", "a", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))
        queue.enqueue("q", "b", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))

        queue.dequeue("q")
        queue.dequeue("q")
        time.sleep(0.02)

        queue.dequeue("q")
        queue.dequeue("q")

        assert queue.get_dead_letter_count("q") == 2

    def test_acknowledge_removes_from_dlq(self, queue: MessageQueue):
        queue.enqueue("q", "x", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))
        queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")

        assert queue.get_dead_letter_count("q") == 1
        dlq = queue.peek_dead_letters("q")
        queue.acknowledge(dlq[0].id)
        assert queue.get_dead_letter_count("q") == 0

    def test_max_retries_zero(self, queue: MessageQueue):
        queue.enqueue("q", "once", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))
        queue.dequeue("q")
        time.sleep(0.02)
        msg = queue.dequeue("q")
        assert msg is None
        assert queue.get_dead_letter_count("q") == 1


class TestDeduplication:
    def test_duplicate_id_within_window_raises(self, queue: MessageQueue):
        queue.enqueue("q", "first", message_id="same-id", dedup_window=timedelta(minutes=1))
        with pytest.raises(DuplicateMessageError):
            queue.enqueue("q", "second", message_id="same-id", dedup_window=timedelta(minutes=1))

    def test_different_queues_same_id_allowed(self, queue: MessageQueue):
        queue.enqueue("q1", "body", message_id="same-id")
        msg = queue.enqueue("q2", "body", message_id="same-id")
        assert msg.id == "same-id"

    def test_duplicate_after_window_allowed(self, queue: MessageQueue):
        queue.enqueue("q", "first", message_id="dup-id", dedup_window=timedelta(milliseconds=10))
        time.sleep(0.05)
        msg = queue.enqueue("q", "second", message_id="dup-id", dedup_window=timedelta(minutes=1))
        assert msg.body == "second"

    def test_duplicate_id_already_exists_raises(self, queue: MessageQueue):
        queue.enqueue("q", "first", message_id="exists-id", dedup_window=timedelta(seconds=0))
        with pytest.raises(DuplicateMessageError):
            queue.enqueue("q", "second", message_id="exists-id")


class TestBoundaryConditions:
    def test_dequeue_empty_queue_returns_none(self, queue: MessageQueue):
        assert queue.dequeue("nonexistent") is None

    def test_get_size_empty_queue(self, queue: MessageQueue):
        assert queue.get_queue_size("empty") == 0

    def test_all_messages_delayed(self, queue: MessageQueue):
        future = datetime.now() + timedelta(hours=1)
        queue.enqueue("q", "d1", deliver_at=future)
        queue.enqueue("q", "d2", deliver_at=future)
        assert queue.dequeue("q") is None
        assert queue.get_queue_size("q") == 0

    def test_clear_resets_everything(self, queue: MessageQueue):
        queue.enqueue("q", "a")
        queue.enqueue("q", "b", max_retry_count=0)
        m = queue.dequeue("q")
        time.sleep(0.01)
        queue.dequeue("q")

        queue.clear()

        assert queue.get_queue_size("q") == 0
        assert queue.get_dead_letter_count("q") == 0
        assert queue.dequeue("q") is None

    def test_peek_dead_letters_empty(self, queue: MessageQueue):
        assert queue.peek_dead_letters("q") == []

    def test_message_model_validation(self):
        with pytest.raises(ValueError):
            Message(id="", body="x", queue_name="q")
        with pytest.raises(ValueError):
            Message(id="1", body="x", queue_name="")
        with pytest.raises(ValueError):
            Message(id="1", body="x", queue_name="q", max_retry_count=-1)
        with pytest.raises(ValueError):
            Message(id="1", body="x", queue_name="q", receive_count=-1)

    def test_message_negative_priority_allowed(self):
        msg = Message(id="1", body="x", queue_name="q", priority=-100)
        assert msg.priority == -100


class TestMessageLifecycle:
    def test_full_message_lifecycle(self, queue: MessageQueue):
        msg = queue.enqueue(
            "orders",
            {"order_id": "123"},
            priority=5,
            max_retry_count=2,
            visibility_timeout=timedelta(milliseconds=20),
        )
        assert msg.status == MessageStatus.PENDING
        assert msg.receive_count == 0

        received = queue.dequeue("orders")
        assert received.status == MessageStatus.IN_FLIGHT
        assert received.receive_count == 1
        assert received.is_visible is False

        queue.retry(received.id)
        assert received.is_visible is True
        assert received.status == MessageStatus.PENDING

        received2 = queue.dequeue("orders")
        assert received2.receive_count == 2

        time.sleep(0.03)

        received3 = queue.dequeue("orders")
        assert received3 is None
        assert queue.get_dead_letter_count("orders") == 1

        dlq = queue.peek_dead_letters("orders")
        assert dlq[0].id == msg.id
        assert dlq[0].status == MessageStatus.DEAD_LETTER

        queue.acknowledge(dlq[0].id)
        assert queue.get_dead_letter_count("orders") == 0


class TestGetQueueSizeAccuracy:
    def test_excludes_in_flight_messages(self, queue: MessageQueue):
        queue.enqueue("q", "pending-1")
        queue.enqueue("q", "pending-2")
        assert queue.get_queue_size("q") == 2

        queue.dequeue("q", visibility_timeout=timedelta(seconds=30))
        assert queue.get_queue_size("q") == 1

    def test_excludes_dead_letter_messages(self, queue: MessageQueue):
        queue.enqueue("q", "ok", visibility_timeout=timedelta(milliseconds=5))
        queue.enqueue("q", "bad", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))

        queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")

        assert queue.get_dead_letter_count("q") == 1
        assert queue.get_queue_size("q") == 1

    def test_excludes_delayed_messages(self, queue: MessageQueue):
        future = datetime.now() + timedelta(hours=1)
        queue.enqueue("q", "delayed", deliver_at=future)
        queue.enqueue("q", "ready")
        assert queue.get_queue_size("q") == 1

    def test_mixed_states(self, queue: MessageQueue):
        future = datetime.now() + timedelta(hours=1)
        queue.enqueue("q", "ready-1", visibility_timeout=timedelta(milliseconds=5))
        queue.enqueue("q", "ready-2")
        queue.enqueue("q", "delayed", deliver_at=future)
        queue.enqueue("q", "will-fail", max_retry_count=0, visibility_timeout=timedelta(milliseconds=5))

        queue.dequeue("q")
        in_flight = queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")

        assert queue.get_queue_size("q") == 1
        queue.retry(in_flight.id)
        assert queue.get_queue_size("q") == 2


class TestDeadLetterDuplicateCleanup:
    def test_requeuing_same_id_cleans_dlq(self, queue: MessageQueue):
        queue.enqueue("q", "old-body", message_id="msg-1", max_retry_count=0,
                      dedup_window=timedelta(milliseconds=5), visibility_timeout=timedelta(milliseconds=5))
        queue.dequeue("q")
        time.sleep(0.02)
        queue.dequeue("q")

        assert queue.get_dead_letter_count("q") == 1
        dlq = queue.peek_dead_letters("q")
        assert dlq[0].body == "old-body"

        time.sleep(0.05)
        new_msg = queue.enqueue("q", "new-body", message_id="msg-1",
                                dedup_window=timedelta(minutes=1))

        assert new_msg.body == "new-body"
        assert queue.get_dead_letter_count("q") == 0
        dlq_after = queue.peek_dead_letters("q")
        assert len(dlq_after) == 0

        consumed = queue.dequeue("q")
        assert consumed.id == "msg-1"
        assert consumed.body == "new-body"

    def test_requeuing_same_id_cleans_in_flight(self, queue: MessageQueue):
        queue.enqueue("q", "old", message_id="msg-2", visibility_timeout=timedelta(seconds=30),
                      dedup_window=timedelta(milliseconds=5))
        queue.dequeue("q")
        assert queue.get_queue_size("q") == 0

        time.sleep(0.05)
        queue.enqueue("q", "new", message_id="msg-2")

        assert queue.get_queue_size("q") == 1
        msg = queue.dequeue("q")
        assert msg.body == "new"
