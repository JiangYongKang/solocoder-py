import pytest

from solocoder_py.partition_ordering import Partitioner


class TestPartitioner:
    def test_num_partitions_validation(self):
        with pytest.raises(ValueError):
            Partitioner(num_partitions=0)
        with pytest.raises(ValueError):
            Partitioner(num_partitions=-1)

    def test_partition_returns_valid_range(self, partitioner: Partitioner):
        for key in ["a", "b", "c", "d", "e", "f", "g", "h"]:
            pid = partitioner.partition(key)
            assert 0 <= pid < partitioner.num_partitions

    def test_same_key_stable_partition(self, partitioner: Partitioner):
        key = "user-123"
        p1 = partitioner.partition(key)
        p2 = partitioner.partition(key)
        p3 = partitioner.partition_stable(key)
        assert p1 == p2 == p3

    def test_different_keys_may_go_to_different_partitions(self, partitioner: Partitioner):
        partitions = set()
        for i in range(100):
            pid = partitioner.partition(f"key-{i}")
            partitions.add(pid)
        assert len(partitions) > 1

    def test_key_none_raises(self, partitioner: Partitioner):
        with pytest.raises(ValueError):
            partitioner.partition(None)

    def test_uniform_distribution_rough(self):
        num_partitions = 10
        p = Partitioner(num_partitions=num_partitions)
        counts = [0] * num_partitions
        num_keys = 10000
        for i in range(num_keys):
            pid = p.partition(f"key-{i}")
            counts[pid] += 1
        expected = num_keys / num_partitions
        for count in counts:
            assert expected * 0.5 < count < expected * 1.5
