import pytest

from solocoder_py.partition_assignor import PartitionAssignor


@pytest.fixture
def make_empty_assignor():
    def _make() -> PartitionAssignor:
        return PartitionAssignor()
    return _make


@pytest.fixture
def make_assignor_with_partitions():
    def _make(num_partitions: int = 10) -> PartitionAssignor:
        assignor = PartitionAssignor()
        assignor.add_partitions(range(num_partitions))
        return assignor
    return _make


@pytest.fixture
def make_balanced_assignor():
    def _make(num_consumers: int = 3, num_partitions: int = 9) -> PartitionAssignor:
        assignor = PartitionAssignor()
        assignor.add_partitions(range(num_partitions))
        for i in range(num_consumers):
            assignor.register_consumer(f"consumer-{i}")
        assignor.rebalance()
        return assignor
    return _make
