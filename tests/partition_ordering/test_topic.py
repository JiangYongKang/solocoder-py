import pytest

from solocoder_py.partition_ordering import PartitionNotFoundError, PartitionedTopic


class TestPartitionedTopic:
    def test_create_topic_valid(self):
        t = PartitionedTopic(name="orders", num_partitions=4)
        assert t.name == "orders"
        assert t.num_partitions == 4

    def test_create_topic_invalid_partitions(self):
        with pytest.raises(ValueError):
            PartitionedTopic(name="t", num_partitions=0)
        with pytest.raises(ValueError):
            PartitionedTopic(name="t", num_partitions=-5)

    def test_create_topic_empty_name(self):
        with pytest.raises(ValueError):
            PartitionedTopic(name="", num_partitions=4)

    def test_produce_assigns_partition_by_key(self, topic: PartitionedTopic):
        key_to_partition = {}
        for i in range(20):
            key = f"user-{i % 4}"
            msg = topic.produce(key=key, value=f"msg-{i}")
            if key not in key_to_partition:
                key_to_partition[key] = msg.partition_id
            else:
                assert msg.partition_id == key_to_partition[key]

    def test_produce_to_specific_partition(self, topic: PartitionedTopic):
        msg = topic.produce_to_partition(partition_id=2, key="k", value="v")
        assert msg.partition_id == 2
        assert msg.offset == 0

        msg2 = topic.produce_to_partition(partition_id=2, key="k2", value="v2")
        assert msg2.partition_id == 2
        assert msg2.offset == 1

    def test_produce_to_invalid_partition(self, topic: PartitionedTopic):
        with pytest.raises(PartitionNotFoundError):
            topic.produce_to_partition(partition_id=99, key="k", value="v")
        with pytest.raises(PartitionNotFoundError):
            topic.produce_to_partition(partition_id=-1, key="k", value="v")

    def test_message_offsets_increment_per_partition(self, topic: PartitionedTopic):
        for pid in range(topic.num_partitions):
            offsets = []
            for i in range(5):
                msg = topic.produce_to_partition(pid, f"k-{pid}", f"v-{i}")
                offsets.append(msg.offset)
            assert offsets == [0, 1, 2, 3, 4]

    def test_get_messages(self, topic: PartitionedTopic):
        for i in range(5):
            topic.produce_to_partition(0, "k", f"v-{i}")

        msgs = topic.get_messages(0, 0, 10)
        assert len(msgs) == 5
        assert [m.offset for m in msgs] == [0, 1, 2, 3, 4]

    def test_get_messages_pagination(self, topic: PartitionedTopic):
        for i in range(10):
            topic.produce_to_partition(0, "k", f"v-{i}")

        first_batch = topic.get_messages(0, 0, 3)
        assert [m.offset for m in first_batch] == [0, 1, 2]

        second_batch = topic.get_messages(0, 3, 3)
        assert [m.offset for m in second_batch] == [3, 4, 5]

    def test_get_messages_empty_partition(self, topic: PartitionedTopic):
        msgs = topic.get_messages(0, 0, 10)
        assert msgs == []

    def test_get_messages_beyond_latest(self, topic: PartitionedTopic):
        topic.produce_to_partition(0, "k", "v")
        msgs = topic.get_messages(0, 100, 10)
        assert msgs == []

    def test_get_messages_invalid_partition(self, topic: PartitionedTopic):
        with pytest.raises(PartitionNotFoundError):
            topic.get_messages(99, 0, 1)

    def test_get_messages_invalid_max_count(self, topic: PartitionedTopic):
        with pytest.raises(ValueError):
            topic.get_messages(0, 0, 0)
        with pytest.raises(ValueError):
            topic.get_messages(0, 0, -1)

    def test_get_latest_offset(self, topic: PartitionedTopic):
        assert topic.get_latest_offset(0) == -1
        topic.produce_to_partition(0, "k", "v1")
        assert topic.get_latest_offset(0) == 0
        topic.produce_to_partition(0, "k", "v2")
        assert topic.get_latest_offset(0) == 1

    def test_get_partition_size(self, topic: PartitionedTopic):
        assert topic.get_partition_size(0) == 0
        topic.produce_to_partition(0, "k", "v1")
        topic.produce_to_partition(0, "k", "v2")
        assert topic.get_partition_size(0) == 2
        assert topic.get_partition_size(1) == 0

    def test_message_timestamp(self, topic: PartitionedTopic):
        import time
        before = time.time()
        msg = topic.produce("k", "v")
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_custom_timestamp(self, topic: PartitionedTopic):
        custom_ts = 1234567890.0
        msg = topic.produce("k", "v", timestamp=custom_ts)
        assert msg.timestamp == custom_ts
