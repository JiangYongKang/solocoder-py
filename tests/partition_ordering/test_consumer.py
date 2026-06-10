import pytest

from solocoder_py.partition_ordering import (
    NotAssignedPartitionError,
    OffsetOutOfRangeError,
    OrderedPartitionConsumer,
    OutOfOrderCommitError,
    PartitionNotFoundError,
    PartitionedTopic,
)


class TestOrderedPartitionConsumerBasic:
    def test_create_consumer(self, topic: PartitionedTopic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        assert c.consumer_id == "c1"
        assert c.topic == topic
        assert c.assigned_partitions == set()

    def test_create_consumer_empty_id(self, topic: PartitionedTopic):
        with pytest.raises(ValueError):
            OrderedPartitionConsumer(consumer_id="", topic=topic)

    def test_assign_partition(self, topic: PartitionedTopic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        c.assign_partition(0)
        c.assign_partition(1)
        assert c.assigned_partitions == {0, 1}

    def test_assign_invalid_partition(self, topic: PartitionedTopic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        with pytest.raises(PartitionNotFoundError):
            c.assign_partition(99)
        with pytest.raises(PartitionNotFoundError):
            c.assign_partition(-1)

    def test_revoke_partition(self, topic: PartitionedTopic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        c.assign_partition(0)
        c.assign_partition(1)
        revoked = c.revoke_partition(0)
        assert revoked == []
        assert c.assigned_partitions == {1}

    def test_revoke_unassigned_partition(self, topic: PartitionedTopic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        revoked = c.revoke_partition(5)
        assert revoked == []


class TestConsumerPolling:
    def test_poll_empty_partition(self, consumer: OrderedPartitionConsumer):
        msgs = consumer.poll(0)
        assert msgs == []

    def test_poll_single_message(self, consumer: OrderedPartitionConsumer):
        consumer.topic.produce_to_partition(0, "k", "v1")
        msgs = consumer.poll(0)
        assert len(msgs) == 1
        assert msgs[0].value == "v1"
        assert msgs[0].offset == 0

    def test_poll_multiple_messages(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")
        msgs = consumer.poll(0, max_messages=3)
        assert len(msgs) == 3
        assert [m.offset for m in msgs] == [0, 1, 2]

    def test_poll_blocks_until_commit(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        batch1 = consumer.poll(0, max_messages=2)
        assert len(batch1) == 2

        batch2 = consumer.poll(0, max_messages=2)
        assert batch2 == []

        consumer.commit(0, 0)
        batch3 = consumer.poll(0, max_messages=2)
        assert batch3 == []

        consumer.commit(0, 1)
        batch4 = consumer.poll(0, max_messages=2)
        assert len(batch4) == 2
        assert [m.offset for m in batch4] == [2, 3]

    def test_poll_not_assigned_partition(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(NotAssignedPartitionError):
            consumer.poll(99)

    def test_poll_invalid_max_messages(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(ValueError):
            consumer.poll(0, max_messages=0)
        with pytest.raises(ValueError):
            consumer.poll(0, max_messages=-1)

    def test_poll_all_partitions(self, consumer: OrderedPartitionConsumer):
        consumer.topic.produce_to_partition(0, "k", "v0")
        consumer.topic.produce_to_partition(1, "k", "v1")
        result = consumer.poll_all()
        assert 0 in result
        assert 1 in result
        assert result[0][0].value == "v0"
        assert result[1][0].value == "v1"


class TestConsumerOrderingGuarantee:
    def test_sequential_processing(self, consumer: OrderedPartitionConsumer):
        for i in range(10):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        processed = []
        while True:
            msgs = consumer.poll(0, max_messages=1)
            if not msgs:
                break
            msg = msgs[0]
            processed.append(msg.value)
            consumer.commit(0, msg.offset)

        assert processed == [f"v-{i}" for i in range(10)]

    def test_out_of_order_commit_rejected(self, consumer: OrderedPartitionConsumer):
        for i in range(3):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.poll(0, max_messages=3)

        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 1)

        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 2)

    def test_commit_before_poll_rejected(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 0)

    def test_commit_not_assigned_partition(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(NotAssignedPartitionError):
            consumer.commit(99, 0)

    def test_get_committed_offset(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        assert consumer.get_committed_offset(0) == -1

        consumer.poll(0)
        consumer.commit(0, 0)
        assert consumer.get_committed_offset(0) == 0

        consumer.poll(0)
        consumer.commit(0, 1)
        assert consumer.get_committed_offset(0) == 1


class TestConsumerSeek:
    def test_seek_valid_offset(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.seek(0, 2)
        msgs = consumer.poll(0)
        assert msgs[0].offset == 3

    def test_seek_to_beginning(self, consumer: OrderedPartitionConsumer):
        for i in range(3):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.seek(0, -1)
        msgs = consumer.poll(0)
        assert msgs[0].offset == 0

    def test_seek_to_future_offset_raises(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(OffsetOutOfRangeError):
            consumer.seek(0, 100)

    def test_seek_invalid_offset(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(OffsetOutOfRangeError):
            consumer.seek(0, -2)

    def test_seek_not_assigned_partition(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(NotAssignedPartitionError):
            consumer.seek(99, 0)

    def test_seek_clears_in_flight(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.poll(0, max_messages=5)
        assert consumer.get_in_flight_count(0) == 5

        consumer.seek(0, 1)
        assert consumer.get_in_flight_count(0) == 0


class TestConsumerInFlight:
    def test_in_flight_count(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        assert consumer.get_in_flight_count(0) == 0
        consumer.poll(0, max_messages=3)
        assert consumer.get_in_flight_count(0) == 3

        consumer.commit(0, 0)
        assert consumer.get_in_flight_count(0) == 2

        consumer.commit(0, 1)
        consumer.commit(0, 2)
        assert consumer.get_in_flight_count(0) == 0

    def test_revoke_returns_uncommitted_messages(self, consumer: OrderedPartitionConsumer):
        for i in range(3):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.poll(0, max_messages=3)
        consumer.commit(0, 0)

        revoked = consumer.revoke_partition(0)
        assert len(revoked) == 2
        assert [m.offset for m in revoked] == [1, 2]
