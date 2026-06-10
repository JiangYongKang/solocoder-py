import threading
import time
from typing import List

import pytest

from solocoder_py.pubsub import (
    BackpressureStrategy,
    DeliveryStatus,
    DuplicateSubscriptionError,
    Message,
    PubSubBroker,
    Subscriber,
    SubscriberNotFoundError,
    TopicAlreadyExistsError,
    TopicNotFoundError,
    TopicStats,
)


class TestTopicManagement:
    def test_create_topic(self, broker: PubSubBroker):
        broker.create_topic("orders")
        assert broker.topic_exists("orders") is True
        assert "orders" in broker.list_topics()

    def test_create_duplicate_topic_raises(self, broker: PubSubBroker):
        broker.create_topic("orders")
        with pytest.raises(TopicAlreadyExistsError):
            broker.create_topic("orders")

    def test_create_empty_topic_name_raises(self, broker: PubSubBroker):
        with pytest.raises(ValueError):
            broker.create_topic("")

    def test_delete_topic(self, broker_with_topic: PubSubBroker):
        broker_with_topic.delete_topic("test-topic")
        assert broker_with_topic.topic_exists("test-topic") is False

    def test_delete_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.delete_topic("nonexistent")

    def test_topic_exists_false_for_unknown(self, broker: PubSubBroker):
        assert broker.topic_exists("unknown") is False

    def test_list_topics_empty(self, broker: PubSubBroker):
        assert broker.list_topics() == []

    def test_list_topics_multiple(self, broker: PubSubBroker):
        broker.create_topic("t1")
        broker.create_topic("t2")
        broker.create_topic("t3")
        topics = broker.list_topics()
        assert len(topics) == 3
        assert set(topics) == {"t1", "t2", "t3"}

    def test_get_topic_stats(self, broker_with_topic: PubSubBroker):
        stats = broker_with_topic.get_topic_stats("test-topic")
        assert isinstance(stats, TopicStats)
        assert stats.name == "test-topic"
        assert stats.subscriber_count == 0
        assert stats.message_published_count == 0

    def test_get_topic_stats_nonexistent_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.get_topic_stats("nonexistent")


class TestSubscribeUnsubscribe:
    def test_subscribe_success(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        sub = broker_with_topic.subscribe(
            "test-topic",
            lambda msg: received.append(msg),
            subscriber_id="sub-1",
        )
        assert isinstance(sub, Subscriber)
        assert sub.id == "sub-1"
        assert broker_with_topic.is_subscribed("test-topic", "sub-1") is True

    def test_subscribe_generates_id(self, broker_with_topic: PubSubBroker):
        sub = broker_with_topic.subscribe("test-topic", lambda m: None)
        assert sub.id is not None
        assert len(sub.id) > 0

    def test_subscribe_duplicate_raises(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: None,
            subscriber_id="sub-1",
        )
        with pytest.raises(DuplicateSubscriptionError):
            broker_with_topic.subscribe(
                "test-topic",
                lambda m: None,
                subscriber_id="sub-1",
            )

    def test_subscribe_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.subscribe("nonexistent", lambda m: None)

    def test_subscribe_none_handler_raises(self, broker_with_topic: PubSubBroker):
        with pytest.raises(ValueError):
            broker_with_topic.subscribe("test-topic", None)

    def test_unsubscribe_success(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: None,
            subscriber_id="sub-1",
        )
        broker_with_topic.unsubscribe("test-topic", "sub-1")
        assert broker_with_topic.is_subscribed("test-topic", "sub-1") is False

    def test_unsubscribe_nonexistent_subscriber_raises(self, broker_with_topic: PubSubBroker):
        with pytest.raises(SubscriberNotFoundError):
            broker_with_topic.unsubscribe("test-topic", "nonexistent")

    def test_unsubscribe_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.unsubscribe("nonexistent", "sub-1")

    def test_get_subscribers_empty(self, broker_with_topic: PubSubBroker):
        assert broker_with_topic.get_subscribers("test-topic") == []

    def test_get_subscribers_multiple(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s2"
        )
        subs = broker_with_topic.get_subscribers("test-topic")
        assert len(subs) == 2
        ids = {s.id for s in subs}
        assert ids == {"s1", "s2"}

    def test_get_subscribers_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.get_subscribers("nonexistent")

    def test_is_subscribed_false_for_unknown_topic(self, broker: PubSubBroker):
        assert broker.is_subscribed("unknown", "sub-1") is False

    def test_subscriber_custom_buffer_and_strategy(self, broker_with_topic: PubSubBroker):
        sub = broker_with_topic.subscribe(
            "test-topic",
            lambda m: None,
            subscriber_id="sub-1",
            buffer_size=50,
            backpressure_strategy=BackpressureStrategy.DROP_NEWEST,
        )
        assert sub.buffer_size == 50
        assert sub.backpressure_strategy == BackpressureStrategy.DROP_NEWEST


class TestMessagePublishAndDispatch:
    def test_publish_single_subscriber_receives(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic",
            lambda msg: received.append(msg),
            subscriber_id="sub-1",
        )

        msg = broker_with_topic.publish("test-topic", {"order_id": "123"})

        time.sleep(0.1)
        assert len(received) == 1
        assert received[0].id == msg.id
        assert received[0].payload == {"order_id": "123"}
        assert received[0].topic == "test-topic"

    def test_publish_multiple_subscribers_all_receive(self, broker_with_topic: PubSubBroker):
        received1: List[Message] = []
        received2: List[Message] = []
        received3: List[Message] = []

        broker_with_topic.subscribe(
            "test-topic", lambda m: received1.append(m), subscriber_id="s1"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: received2.append(m), subscriber_id="s2"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: received3.append(m), subscriber_id="s3"
        )

        broker_with_topic.publish("test-topic", "hello")
        time.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        assert len(received3) == 1
        assert received1[0].payload == "hello"
        assert received2[0].payload == "hello"
        assert received3[0].payload == "hello"

    def test_publish_empty_subscribers_no_error(self, broker_with_topic: PubSubBroker):
        msg = broker_with_topic.publish("test-topic", "orphan")
        assert msg is not None
        assert msg.payload == "orphan"

    def test_publish_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.publish("nonexistent", "data")

    def test_publish_with_custom_message_id(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic", lambda m: received.append(m), subscriber_id="s1"
        )

        msg = broker_with_topic.publish(
            "test-topic", "payload", message_id="custom-msg-1"
        )
        time.sleep(0.1)

        assert msg.id == "custom-msg-1"
        assert received[0].id == "custom-msg-1"

    def test_publish_with_publisher_id(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic", lambda m: received.append(m), subscriber_id="s1"
        )

        broker_with_topic.publish(
            "test-topic", "payload", publisher_id="pub-service"
        )
        time.sleep(0.1)

        assert received[0].publisher_id == "pub-service"

    def test_publish_batch(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic", lambda m: received.append(m), subscriber_id="s1"
        )

        messages = broker_with_topic.publish_batch(
            "test-topic", ["a", "b", "c", "d", "e"]
        )
        time.sleep(0.1)

        assert len(messages) == 5
        assert len(received) == 5
        payloads = [m.payload for m in received]
        assert payloads == ["a", "b", "c", "d", "e"]

    def test_message_order_preserved(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic", lambda m: received.append(m), subscriber_id="s1"
        )

        for i in range(20):
            broker_with_topic.publish("test-topic", i)

        time.sleep(0.2)

        assert len(received) == 20
        payloads = [m.payload for m in received]
        assert payloads == list(range(20))

    def test_topic_stats_updated_after_publish(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s2"
        )

        for _ in range(5):
            broker_with_topic.publish("test-topic", "x")

        stats = broker_with_topic.get_topic_stats("test-topic")
        assert stats.subscriber_count == 2
        assert stats.message_published_count == 5


class TestBackpressureIsolation:
    def test_slow_subscriber_does_not_block_others(self, broker_with_topic: PubSubBroker):
        fast_received: List[Message] = []
        slow_received: List[Message] = []

        def slow_handler(msg: Message) -> None:
            time.sleep(0.05)
            slow_received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            slow_handler,
            subscriber_id="slow",
            buffer_size=10,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: fast_received.append(m),
            subscriber_id="fast",
        )

        published = []
        for i in range(20):
            msg = broker_with_topic.publish("test-topic", i)
            published.append(msg)

        time.sleep(1.5)

        assert len(fast_received) == 20
        fast_payloads = [m.payload for m in fast_received]
        assert fast_payloads == list(range(20))

        fast_records = broker_with_topic.get_delivery_records(subscriber_id="fast")
        assert len(fast_records) == 20
        for r in fast_records:
            assert r.status == DeliveryStatus.SUCCESS

    def test_drop_oldest_drops_correct_message_ids(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        event = threading.Event()

        def handler(msg: Message) -> None:
            event.wait()
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="sub-1",
            buffer_size=3,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )

        published = []
        for i in range(8):
            msg = broker_with_topic.publish("test-topic", i, message_id=f"msg-{i}")
            published.append(msg)

        event.set()
        time.sleep(0.3)

        records = broker_with_topic.get_delivery_records(subscriber_id="sub-1")

        dropped_records = [r for r in records if r.status == DeliveryStatus.DROPPED]
        success_records = [r for r in records if r.status == DeliveryStatus.SUCCESS]

        assert len(dropped_records) + len(success_records) == 8

        dropped_ids = {r.message_id for r in dropped_records}
        success_ids = {r.message_id for r in success_records}

        assert dropped_ids.isdisjoint(success_ids)
        assert dropped_ids | success_ids == {f"msg-{i}" for i in range(8)}

        expected_dropped_payloads = {i for i in range(5)}
        actual_dropped_payloads = set()
        for r in dropped_records:
            for p in published:
                if p.id == r.message_id:
                    actual_dropped_payloads.add(p.payload)
                    break
        assert actual_dropped_payloads <= expected_dropped_payloads
        for r in dropped_records:
            assert "dropped oldest" in (r.error_message or "").lower()

    def test_drop_newest_drops_correct_message_ids(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        event = threading.Event()

        def handler(msg: Message) -> None:
            event.wait()
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="sub-1",
            buffer_size=3,
            backpressure_strategy=BackpressureStrategy.DROP_NEWEST,
        )

        published = []
        for i in range(8):
            msg = broker_with_topic.publish("test-topic", i, message_id=f"msg-{i}")
            published.append(msg)

        event.set()
        time.sleep(0.3)

        records = broker_with_topic.get_delivery_records(subscriber_id="sub-1")

        dropped_records = [r for r in records if r.status == DeliveryStatus.DROPPED]
        success_records = [r for r in records if r.status == DeliveryStatus.SUCCESS]

        assert len(dropped_records) + len(success_records) == 8

        dropped_ids = {r.message_id for r in dropped_records}
        success_ids = {r.message_id for r in success_records}

        assert dropped_ids.isdisjoint(success_ids)
        assert dropped_ids | success_ids == {f"msg-{i}" for i in range(8)}

        expected_success_payloads = {0, 1, 2}
        actual_success_payloads = set()
        for r in success_records:
            for p in published:
                if p.id == r.message_id:
                    actual_success_payloads.add(p.payload)
                    break
        assert expected_success_payloads <= actual_success_payloads
        for r in dropped_records:
            assert "dropped newest" in (r.error_message or "").lower()

    def test_single_message_cannot_be_both_success_and_dropped(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        handler_event = threading.Event()

        def slow_handler(msg: Message) -> None:
            handler_event.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            slow_handler,
            subscriber_id="sub-1",
            buffer_size=2,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )

        for i in range(10):
            broker_with_topic.publish("test-topic", i, message_id=f"msg-{i}")

        handler_event.set()
        time.sleep(0.3)

        for i in range(10):
            records = broker_with_topic.get_delivery_records(
                message_id=f"msg-{i}", subscriber_id="sub-1"
            )
            assert len(records) >= 1, f"No records for msg-{i}"
            statuses = {r.status for r in records}
            assert not (
                DeliveryStatus.SUCCESS in statuses and DeliveryStatus.DROPPED in statuses
            ), f"msg-{i} has both SUCCESS and DROPPED"
            assert len(statuses) == 1, f"msg-{i} has multiple statuses: {statuses}"

    def test_each_message_has_exactly_one_final_status_per_subscriber(self, broker_with_topic: PubSubBroker):
        received1: List[Message] = []
        received2: List[Message] = []
        handler_event = threading.Event()

        def slow_handler(msg: Message) -> None:
            handler_event.wait(timeout=5.0)
            received1.append(msg)

        def fast_handler(msg: Message) -> None:
            received2.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            slow_handler,
            subscriber_id="s1",
            buffer_size=3,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )
        broker_with_topic.subscribe(
            "test-topic",
            fast_handler,
            subscriber_id="s2",
        )

        for i in range(15):
            broker_with_topic.publish("test-topic", i, message_id=f"m{i}")

        handler_event.set()
        time.sleep(0.3)

        for subscriber_id in ["s1", "s2"]:
            for i in range(15):
                records = broker_with_topic.get_delivery_records(
                    message_id=f"m{i}", subscriber_id=subscriber_id
                )
                assert len(records) == 1, (
                    f"Expected 1 record for m{i}/{subscriber_id}, got {len(records)}"
                )
                assert records[0].status in (
                    DeliveryStatus.SUCCESS,
                    DeliveryStatus.FAILED,
                    DeliveryStatus.DROPPED,
                )

    def test_block_strategy_bounds_buffer(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        can_proceed = threading.Event()
        handler_started = threading.Event()
        BUFFER_SIZE = 2

        def handler(msg: Message) -> None:
            handler_started.set()
            can_proceed.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="block-sub",
            buffer_size=BUFFER_SIZE,
            backpressure_strategy=BackpressureStrategy.BLOCK,
        )

        broker_with_topic.publish("test-topic", 0, message_id="blk-0")
        handler_started.wait(timeout=2.0)
        assert handler_started.is_set()

        for i in range(1, BUFFER_SIZE + 1):
            broker_with_topic.publish("test-topic", i, message_id=f"blk-{i}")

        time.sleep(0.1)
        buf_size = broker_with_topic.get_subscriber_buffer_size("test-topic", "block-sub")
        assert buf_size == BUFFER_SIZE

        broker_with_topic.publish("test-topic", "late", message_id="blk-late")
        time.sleep(0.1)
        buf_size_after_late = broker_with_topic.get_subscriber_buffer_size(
            "test-topic", "block-sub"
        )
        assert buf_size_after_late == BUFFER_SIZE

        can_proceed.set()
        time.sleep(0.5)

        records = broker_with_topic.get_delivery_records(subscriber_id="block-sub")
        statuses = {r.message_id: r.status for r in records}
        for i in range(BUFFER_SIZE + 1):
            assert f"blk-{i}" in statuses, f"blk-{i} missing from records"
        assert "blk-late" in statuses
        success_count = sum(
            1 for s in statuses.values() if s == DeliveryStatus.SUCCESS
        )
        dropped_count = sum(
            1 for s in statuses.values() if s == DeliveryStatus.DROPPED
        )
        assert success_count + dropped_count == BUFFER_SIZE + 2

    def test_block_subscriber_does_not_block_other_subscribers(self, broker_with_topic: PubSubBroker):
        fast_received: List[Message] = []
        slow_received: List[Message] = []
        can_proceed = threading.Event()

        def block_handler(msg: Message) -> None:
            can_proceed.wait(timeout=5.0)
            slow_received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            block_handler,
            subscriber_id="slow-block",
            buffer_size=1,
            backpressure_strategy=BackpressureStrategy.BLOCK,
        )
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: fast_received.append(m),
            subscriber_id="fast",
        )

        start = time.monotonic()
        for i in range(5):
            broker_with_topic.publish("test-topic", i, message_id=f"pub-{i}")
        publish_elapsed = time.monotonic() - start

        assert publish_elapsed < 1.0, "publish should not be blocked by BLOCK subscriber"
        time.sleep(0.2)
        assert len(fast_received) == 5, "fast subscriber should receive all 5 messages"

        can_proceed.set()
        time.sleep(0.3)

    def test_block_timeout_drops_message(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        can_proceed = threading.Event()

        def handler(msg: Message) -> None:
            can_proceed.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="block-sub",
            buffer_size=1,
            backpressure_strategy=BackpressureStrategy.BLOCK,
        )

        broker_with_topic.publish("test-topic", 0, message_id="t-0")
        time.sleep(0.05)

        broker_with_topic.publish("test-topic", 1, message_id="t-1")
        time.sleep(0.05)

        broker_with_topic.publish("test-topic", 2, message_id="t-2")

        time.sleep(2.5)

        dropped_before = broker_with_topic.get_delivery_records(
            subscriber_id="block-sub"
        )
        dropped_records = [
            r for r in dropped_before if r.status == DeliveryStatus.DROPPED
        ]
        assert len(dropped_records) >= 1
        for rec in dropped_records:
            assert "timed out" in (rec.error_message or "").lower()
            assert rec.message_id in ("t-1", "t-2")

        can_proceed.set()
        time.sleep(0.5)

        all_records = broker_with_topic.get_delivery_records(subscriber_id="block-sub")
        statuses = {r.message_id: r.status for r in all_records}
        for i in range(3):
            assert f"t-{i}" in statuses
            assert statuses[f"t-{i}"] in (
                DeliveryStatus.SUCCESS,
                DeliveryStatus.DROPPED,
            )

    def test_block_stopped_drops_message(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        can_proceed = threading.Event()

        def handler(msg: Message) -> None:
            can_proceed.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="block-sub",
            buffer_size=1,
            backpressure_strategy=BackpressureStrategy.BLOCK,
        )

        broker_with_topic.publish("test-topic", 0, message_id="stop-0")
        time.sleep(0.05)
        broker_with_topic.publish("test-topic", 1, message_id="stop-1")
        time.sleep(0.05)
        broker_with_topic.publish("test-topic", 2, message_id="stop-2")

        time.sleep(0.3)
        broker_with_topic.delete_topic("test-topic")

        records_after_delete = broker_with_topic.get_delivery_records(
            subscriber_id="block-sub"
        )
        dropped_records = [
            r for r in records_after_delete if r.status == DeliveryStatus.DROPPED
        ]
        assert len(dropped_records) >= 1

        can_proceed.set()
        time.sleep(0.5)

        all_records = broker_with_topic.get_delivery_records(subscriber_id="block-sub")
        statuses = {r.message_id: r.status for r in all_records}
        for i in range(3):
            assert f"stop-{i}" in statuses
            assert statuses[f"stop-{i}"] in (
                DeliveryStatus.SUCCESS,
                DeliveryStatus.DROPPED,
            )

    def test_unsubscribe_records_dropped_for_buffered_messages(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        handler_event = threading.Event()

        def handler(msg: Message) -> None:
            handler_event.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="buf-sub",
            buffer_size=5,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )

        for i in range(3):
            broker_with_topic.publish("test-topic", i, message_id=f"buf-{i}")

        time.sleep(0.05)
        broker_with_topic.unsubscribe("test-topic", "buf-sub")

        records_after_unsub = broker_with_topic.get_delivery_records(
            subscriber_id="buf-sub"
        )
        dropped = [r for r in records_after_unsub if r.status == DeliveryStatus.DROPPED]
        assert len(dropped) >= 1
        for rec in dropped:
            assert "stopped" in (rec.error_message or "").lower()

        handler_event.set()
        time.sleep(0.3)

        all_records = broker_with_topic.get_delivery_records(subscriber_id="buf-sub")
        statuses = {r.message_id: r.status for r in all_records}
        for i in range(3):
            assert f"buf-{i}" in statuses
            assert statuses[f"buf-{i}"] in (
                DeliveryStatus.SUCCESS,
                DeliveryStatus.DROPPED,
            )

    def test_delete_topic_records_dropped_for_buffered_messages(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        handler_event = threading.Event()

        def handler(msg: Message) -> None:
            handler_event.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="del-sub",
            buffer_size=5,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )

        for i in range(4):
            broker_with_topic.publish("test-topic", i, message_id=f"del-{i}")

        time.sleep(0.05)
        broker_with_topic.delete_topic("test-topic")

        records_after_delete = broker_with_topic.get_delivery_records(
            subscriber_id="del-sub"
        )
        dropped = [r for r in records_after_delete if r.status == DeliveryStatus.DROPPED]
        assert len(dropped) >= 2

        handler_event.set()
        time.sleep(0.3)

        all_records = broker_with_topic.get_delivery_records(subscriber_id="del-sub")
        statuses = {r.message_id: r.status for r in all_records}
        for i in range(4):
            assert f"del-{i}" in statuses, f"del-{i} missing from records"
            assert statuses[f"del-{i}"] in (
                DeliveryStatus.SUCCESS,
                DeliveryStatus.DROPPED,
            )

    def test_clear_records_dropped_for_buffered_messages(self, broker_with_topic: PubSubBroker):
        broker_with_topic.create_topic("other-topic")
        received: List[Message] = []
        handler_event = threading.Event()

        def handler(msg: Message) -> None:
            handler_event.wait(timeout=5.0)
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="clear-sub",
            buffer_size=5,
        )
        broker_with_topic.subscribe(
            "other-topic",
            lambda m: None,
            subscriber_id="other-sub",
        )

        for i in range(3):
            broker_with_topic.publish("test-topic", i, message_id=f"clear-{i}")
        broker_with_topic.publish("other-topic", "other-msg", message_id="other-1")

        time.sleep(0.3)

        pre_clear_records = broker_with_topic.get_delivery_records()
        assert len(pre_clear_records) >= 1

        handler_event.set()
        time.sleep(0.3)

        broker_with_topic.clear()

        assert broker_with_topic.list_topics() == []
        assert broker_with_topic.get_delivery_records() == []

    def test_inactive_subscriber_does_not_receive(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: received.append(m),
            subscriber_id="sub-1",
        )

        broker_with_topic.set_subscriber_active("test-topic", "sub-1", False)
        broker_with_topic.publish("test-topic", "should-not-receive")
        time.sleep(0.1)

        assert len(received) == 0

        broker_with_topic.set_subscriber_active("test-topic", "sub-1", True)
        broker_with_topic.publish("test-topic", "should-receive")
        time.sleep(0.1)

        assert len(received) == 1
        assert received[0].payload == "should-receive"

    def test_set_active_nonexistent_subscriber_raises(self, broker_with_topic: PubSubBroker):
        with pytest.raises(SubscriberNotFoundError):
            broker_with_topic.set_subscriber_active("test-topic", "nonexistent", False)

    def test_set_active_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.set_subscriber_active("nonexistent", "sub-1", False)

    def test_get_buffer_size_nonexistent_subscriber_raises(self, broker_with_topic: PubSubBroker):
        with pytest.raises(SubscriberNotFoundError):
            broker_with_topic.get_subscriber_buffer_size("test-topic", "nonexistent")

    def test_get_buffer_size_nonexistent_topic_raises(self, broker: PubSubBroker):
        with pytest.raises(TopicNotFoundError):
            broker.get_subscriber_buffer_size("nonexistent", "sub-1")


class TestDeliveryStatusTracking:
    def test_successful_delivery_recorded(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        msg = broker_with_topic.publish("test-topic", "data")
        time.sleep(0.1)

        records = broker_with_topic.get_delivery_records(message_id=msg.id)
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.SUCCESS
        assert records[0].subscriber_id == "s1"
        assert records[0].message_id == msg.id
        assert records[0].completed_at is not None

    def test_failed_delivery_recorded(self, broker_with_topic: PubSubBroker):
        def failing_handler(msg: Message) -> None:
            raise RuntimeError("handler failed")

        broker_with_topic.subscribe(
            "test-topic", failing_handler, subscriber_id="s1"
        )
        msg = broker_with_topic.publish("test-topic", "data")
        time.sleep(0.1)

        records = broker_with_topic.get_delivery_records(message_id=msg.id)
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.FAILED
        assert records[0].error_message is not None
        assert "handler failed" in records[0].error_message

    def test_dropped_delivery_recorded(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        event = threading.Event()

        def handler(msg: Message) -> None:
            event.wait()
            received.append(msg)

        broker_with_topic.subscribe(
            "test-topic",
            handler,
            subscriber_id="sub-1",
            buffer_size=3,
            backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        )

        messages = []
        for i in range(10):
            msg = broker_with_topic.publish("test-topic", i)
            messages.append(msg)

        event.set()
        time.sleep(0.2)

        records = broker_with_topic.get_delivery_records(subscriber_id="sub-1")
        statuses = [r.status for r in records]
        assert DeliveryStatus.SUCCESS in statuses
        assert DeliveryStatus.DROPPED in statuses

    def test_inactive_subscriber_dropped_recorded(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.set_subscriber_active("test-topic", "s1", False)
        msg = broker_with_topic.publish("test-topic", "data")
        time.sleep(0.1)

        records = broker_with_topic.get_delivery_records(message_id=msg.id)
        assert len(records) == 1
        assert records[0].status == DeliveryStatus.DROPPED
        assert "inactive" in (records[0].error_message or "").lower()

    def test_filter_records_by_topic(self, broker: PubSubBroker):
        broker.create_topic("t1")
        broker.create_topic("t2")
        broker.subscribe("t1", lambda m: None, subscriber_id="s1")
        broker.subscribe("t2", lambda m: None, subscriber_id="s2")

        broker.publish("t1", "a")
        broker.publish("t2", "b")
        time.sleep(0.1)

        t1_records = broker.get_delivery_records(topic_name="t1")
        t2_records = broker.get_delivery_records(topic_name="t2")
        assert len(t1_records) == 1
        assert t1_records[0].topic == "t1"
        assert len(t2_records) == 1
        assert t2_records[0].topic == "t2"

    def test_filter_records_by_subscriber(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s2"
        )

        broker_with_topic.publish("test-topic", "x")
        time.sleep(0.1)

        s1_records = broker_with_topic.get_delivery_records(subscriber_id="s1")
        s2_records = broker_with_topic.get_delivery_records(subscriber_id="s2")
        assert len(s1_records) == 1
        assert s1_records[0].subscriber_id == "s1"
        assert len(s2_records) == 1
        assert s2_records[0].subscriber_id == "s2"

    def test_filter_records_by_message_id(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s2"
        )

        msg1 = broker_with_topic.publish("test-topic", "first")
        broker_with_topic.publish("test-topic", "second")
        time.sleep(0.1)

        msg1_records = broker_with_topic.get_delivery_records(message_id=msg1.id)
        assert len(msg1_records) == 2
        for r in msg1_records:
            assert r.message_id == msg1.id


class TestConcurrentPublishing:
    def test_high_concurrent_publish(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        lock = threading.Lock()

        def safe_handler(msg: Message) -> None:
            with lock:
                received.append(msg)

        broker_with_topic.subscribe(
            "test-topic", safe_handler, subscriber_id="s1"
        )

        num_threads = 5
        msgs_per_thread = 20

        def publisher(tid: int) -> None:
            for i in range(msgs_per_thread):
                broker_with_topic.publish(
                    "test-topic", f"t{tid}-m{i}"
                )

        threads = []
        for t in range(num_threads):
            th = threading.Thread(target=publisher, args=(t,))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        time.sleep(0.3)

        assert len(received) == num_threads * msgs_per_thread

    def test_concurrent_subscribe_unsubscribe(self, broker_with_topic: PubSubBroker):
        errors: List[Exception] = []

        def subscriber_ops(sid: int) -> None:
            try:
                for _ in range(10):
                    sub_id = f"sub-{sid}-{_}"
                    broker_with_topic.subscribe(
                        "test-topic", lambda m: None, subscriber_id=sub_id
                    )
                    time.sleep(0.001)
                    broker_with_topic.unsubscribe("test-topic", sub_id)
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(5):
            th = threading.Thread(target=subscriber_ops, args=(t,))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        assert len(errors) == 0

    def test_concurrent_publish_different_topics(self, broker: PubSubBroker):
        for i in range(5):
            broker.create_topic(f"topic-{i}")

        received_by_topic: dict = {}
        lock = threading.Lock()
        for i in range(5):
            received_by_topic[f"topic-{i}"] = []
            broker.subscribe(
                f"topic-{i}",
                lambda m, t=i: (
                    lock.acquire(),
                    received_by_topic[f"topic-{t}"].append(m),
                    lock.release(),
                ),
                subscriber_id=f"s-{i}",
            )

        def publish_to_topic(tid: int) -> None:
            for j in range(10):
                broker.publish(f"topic-{tid}", f"msg-{tid}-{j}")

        threads = []
        for t in range(5):
            th = threading.Thread(target=publish_to_topic, args=(t,))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        time.sleep(0.3)

        for i in range(5):
            assert len(received_by_topic[f"topic-{i}"]) == 10


class TestBoundaryAndEdgeCases:
    def test_subscriber_validation_empty_id(self):
        with pytest.raises(ValueError):
            Subscriber(id="", handler=lambda m: None)

    def test_subscriber_validation_zero_buffer(self):
        with pytest.raises(ValueError):
            Subscriber(id="s1", handler=lambda m: None, buffer_size=0)

    def test_subscriber_validation_negative_buffer(self):
        with pytest.raises(ValueError):
            Subscriber(id="s1", handler=lambda m: None, buffer_size=-1)

    def test_message_validation_empty_id(self):
        with pytest.raises(ValueError):
            Message(id="", topic="t", payload="x")

    def test_message_validation_empty_topic(self):
        with pytest.raises(ValueError):
            Message(id="m1", topic="", payload="x")

    def test_broker_invalid_default_buffer(self):
        with pytest.raises(ValueError):
            PubSubBroker(default_subscriber_buffer_size=0)

    def test_clear_resets_everything(self, broker_with_topic: PubSubBroker):
        broker_with_topic.subscribe(
            "test-topic", lambda m: None, subscriber_id="s1"
        )
        broker_with_topic.publish("test-topic", "data")
        time.sleep(0.1)

        broker_with_topic.clear()

        assert broker_with_topic.list_topics() == []
        assert broker_with_topic.get_delivery_records() == []

    def test_unsubscribe_stops_further_delivery(self, broker_with_topic: PubSubBroker):
        received: List[Message] = []
        broker_with_topic.subscribe(
            "test-topic",
            lambda m: received.append(m),
            subscriber_id="s1",
        )
        broker_with_topic.publish("test-topic", "before")
        time.sleep(0.1)
        assert len(received) == 1

        broker_with_topic.unsubscribe("test-topic", "s1")
        broker_with_topic.publish("test-topic", "after")
        time.sleep(0.1)

        assert len(received) == 1

    def test_delete_topic_stops_all_delivery(self, broker: PubSubBroker):
        received: List[Message] = []
        broker.create_topic("temp")
        broker.subscribe("temp", lambda m: received.append(m), subscriber_id="s1")
        broker.publish("temp", "before")
        time.sleep(0.1)
        assert len(received) == 1

        broker.delete_topic("temp")
        broker.create_topic("temp")
        broker.publish("temp", "after")
        time.sleep(0.1)

        assert len(received) == 1

    def test_multiple_topics_isolation(self, broker: PubSubBroker):
        broker.create_topic("t1")
        broker.create_topic("t2")

        t1_received: List[Message] = []
        t2_received: List[Message] = []

        broker.subscribe("t1", lambda m: t1_received.append(m), subscriber_id="s1")
        broker.subscribe("t2", lambda m: t2_received.append(m), subscriber_id="s2")

        broker.publish("t1", "for-t1")
        broker.publish("t2", "for-t2")
        time.sleep(0.1)

        assert len(t1_received) == 1
        assert t1_received[0].payload == "for-t1"
        assert len(t2_received) == 1
        assert t2_received[0].payload == "for-t2"
