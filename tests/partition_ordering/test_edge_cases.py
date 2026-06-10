import threading
import time

import pytest

from solocoder_py.partition_ordering import (
    ConsumerGroupCoordinator,
    NotAssignedPartitionError,
    OrderedPartitionConsumer,
    OutOfOrderCommitError,
    PartitionedTopic,
)


class TestSinglePartitionDegenerate:
    def test_single_partition_all_keys_go_same_partition(self, single_partition_topic):
        keys = ["a", "b", "c", "d", "e", "f", "g"]
        for key in keys:
            msg = single_partition_topic.produce(key=key, value=f"v-{key}")
            assert msg.partition_id == 0

    def test_single_partition_strict_order(self, single_partition_topic):
        c = OrderedPartitionConsumer(consumer_id="c1", topic=single_partition_topic)
        c.assign_partition(0)

        for i in range(20):
            single_partition_topic.produce(key=f"k-{i % 5}", value=f"v-{i}")

        processed = []
        while True:
            msgs = c.poll(0, max_messages=1)
            if not msgs:
                break
            m = msgs[0]
            processed.append(m.value)
            c.commit(0, m.offset)

        assert processed == [f"v-{i}" for i in range(20)]

    def test_single_partition_one_consumer_gets_all(self, single_partition_topic):
        coord = ConsumerGroupCoordinator("g", single_partition_topic)
        c1 = coord.join_group("c1")
        c2 = coord.join_group("c2")

        assert 0 in c1.assigned_partitions or 0 in c2.assigned_partitions
        assert not (0 in c1.assigned_partitions and 0 in c2.assigned_partitions)


class TestEmptyMessageBatches:
    def test_poll_empty_partition_returns_empty(self, consumer: OrderedPartitionConsumer):
        result = consumer.poll(0)
        assert result == []

    def test_poll_all_empty_partitions(self, consumer: OrderedPartitionConsumer):
        result = consumer.poll_all()
        assert result == {}

    def test_poll_after_all_committed_returns_empty(self, consumer: OrderedPartitionConsumer):
        consumer.topic.produce_to_partition(0, "k", "v")

        msgs = consumer.poll(0)
        assert len(msgs) == 1
        consumer.commit(0, msgs[0].offset)

        msgs2 = consumer.poll(0)
        assert msgs2 == []

    def test_empty_batch_not_assigned_partition(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(NotAssignedPartitionError):
            consumer.poll(99)


class TestUnknownPartitionCommit:
    def test_commit_unknown_partition_raises(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(NotAssignedPartitionError):
            consumer.commit(999, 0)

    def test_commit_offset_without_messages_raises(self, consumer: OrderedPartitionConsumer):
        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 0)

    def test_commit_future_offset_raises(self, consumer: OrderedPartitionConsumer):
        for i in range(3):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.poll(0, max_messages=3)
        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 999)

    def test_commit_wrong_offset_sequence(self, consumer: OrderedPartitionConsumer):
        for i in range(5):
            consumer.topic.produce_to_partition(0, "k", f"v-{i}")

        consumer.poll(0, max_messages=5)
        consumer.commit(0, 0)

        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, 3)

        with pytest.raises(OutOfOrderCommitError):
            consumer.commit(0, -1)

        consumer.commit(0, 1)
        consumer.commit(0, 2)
        consumer.commit(0, 3)
        consumer.commit(0, 4)


class TestRebalanceDuringDuplicateAssignment:
    def test_same_consumer_joins_twice_returns_same(self, coordinator: ConsumerGroupCoordinator):
        c1 = coordinator.join_group("c1")
        c2 = coordinator.join_group("c1")
        assert c1 is c2
        assert coordinator.get_consumer_count() == 1

    def test_rebalance_preserves_partition_ownership(self, coordinator: ConsumerGroupCoordinator):
        c1 = coordinator.join_group("c1")
        initial_pids = sorted(c1.assigned_partitions)

        coordinator.force_rebalance()

        after_pids = sorted(c1.assigned_partitions)
        assert initial_pids == after_pids


class TestConcurrentPartitionAccess:
    def test_concurrent_produce_stable_partitioning(self, topic: PartitionedTopic):
        key = "concurrent-key"
        errors = []

        def produce(n):
            try:
                for i in range(n):
                    msg = topic.produce(key=key, value=f"v-{i}-{threading.current_thread().name}")
                    assert msg.partition_id == topic.partitioner.partition(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=produce, args=(50,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_concurrent_consume_different_partitions(self, topic: PartitionedTopic):
        for pid in range(topic.num_partitions):
            for i in range(20):
                topic.produce_to_partition(pid, f"k-{pid}", f"v-{pid}-{i}")

        results: dict[int, list[str]] = {pid: [] for pid in range(topic.num_partitions)}
        locks = {pid: threading.Lock() for pid in range(topic.num_partitions)}

        def consume_partition(pid):
            c = OrderedPartitionConsumer(consumer_id=f"consumer-{pid}", topic=topic)
            c.assign_partition(pid)
            while True:
                msgs = c.poll(pid, max_messages=1)
                if not msgs:
                    break
                m = msgs[0]
                with locks[pid]:
                    results[pid].append(m.value)
                c.commit(pid, m.offset)

        threads = [threading.Thread(target=consume_partition, args=(pid,))
                   for pid in range(topic.num_partitions)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for pid in range(topic.num_partitions):
            assert results[pid] == [f"v-{pid}-{i}" for i in range(20)]

    def test_consumer_group_concurrent_join(self, topic: PartitionedTopic):
        coord = ConsumerGroupCoordinator("test-group", topic)
        errors = []

        def join_safe(cid):
            try:
                coord.join_group(cid)
            except RebalanceInProgressError:
                time.sleep(0.01)
                coord.join_group(cid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=join_safe, args=(f"c-{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert coord.get_consumer_count() == 4


class TestModelsValidation:
    def test_message_negative_offset_raises(self):
        from solocoder_py.partition_ordering import Message
        with pytest.raises(ValueError):
            Message(offset=-1, key="k", value="v", partition_id=0, timestamp=0.0)

    def test_message_negative_partition_raises(self):
        from solocoder_py.partition_ordering import Message
        with pytest.raises(ValueError):
            Message(offset=0, key="k", value="v", partition_id=-1, timestamp=0.0)

    def test_message_negative_timestamp_raises(self):
        from solocoder_py.partition_ordering import Message
        with pytest.raises(ValueError):
            Message(offset=0, key="k", value="v", partition_id=0, timestamp=-1.0)

    def test_partition_offset_negative_partition_raises(self):
        from solocoder_py.partition_ordering import PartitionOffset
        with pytest.raises(ValueError):
            PartitionOffset(partition_id=-1)

    def test_consumer_assignment_empty_id_raises(self):
        from solocoder_py.partition_ordering import ConsumerAssignment
        with pytest.raises(ValueError):
            ConsumerAssignment(consumer_id="")

    def test_consumer_state_empty_id_raises(self):
        from solocoder_py.partition_ordering import ConsumerState
        with pytest.raises(ValueError):
            ConsumerState(consumer_id="")


class TestCrossPartitionOrderingIsolation:
    def test_different_partitions_process_independently(self, consumer: OrderedPartitionConsumer):
        for i in range(3):
            consumer.topic.produce_to_partition(0, "k0", f"v0-{i}")
        for i in range(5):
            consumer.topic.produce_to_partition(1, "k1", f"v1-{i}")

        p0_processed = []
        p1_processed = []

        while True:
            p0_msgs = consumer.poll(0, max_messages=1)
            p1_msgs = consumer.poll(1, max_messages=1)

            if not p0_msgs and not p1_msgs:
                break

            if p0_msgs:
                m = p0_msgs[0]
                p0_processed.append(m.value)
                consumer.commit(0, m.offset)

            if p1_msgs:
                m = p1_msgs[0]
                p1_processed.append(m.value)
                consumer.commit(1, m.offset)

        assert p0_processed == [f"v0-{i}" for i in range(3)]
        assert p1_processed == [f"v1-{i}" for i in range(5)]
