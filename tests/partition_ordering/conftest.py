import pytest

from solocoder_py.partition_ordering import (
    ConsumerGroupCoordinator,
    OrderedPartitionConsumer,
    PartitionedTopic,
    Partitioner,
)


@pytest.fixture
def partitioner() -> Partitioner:
    return Partitioner(num_partitions=8)


@pytest.fixture
def topic() -> PartitionedTopic:
    return PartitionedTopic(name="test-topic", num_partitions=4)


@pytest.fixture
def single_partition_topic() -> PartitionedTopic:
    return PartitionedTopic(name="single-topic", num_partitions=1)


@pytest.fixture
def consumer(topic: PartitionedTopic) -> OrderedPartitionConsumer:
    c = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
    c.assign_partition(0)
    c.assign_partition(1)
    return c


@pytest.fixture
def coordinator(topic: PartitionedTopic) -> ConsumerGroupCoordinator:
    return ConsumerGroupCoordinator(group_id="test-group", topic=topic)
