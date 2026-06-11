import pytest

from solocoder_py.partition_assignor import (
    AssignmentChange,
    ConsumerAlreadyRegisteredError,
    ConsumerNotFoundError,
    EmptyConsumerGroupError,
    InvalidPartitionIdError,
    PartitionAssignor,
    PartitionAssignorError,
    PartitionNotFoundError,
)
from solocoder_py.partition_assignor.models import ConsumerStatus


class TestPartitionModel:
    def test_valid_partition(self):
        from solocoder_py.partition_assignor import Partition
        p = Partition(partition_id=0)
        assert p.partition_id == 0

    def test_negative_partition_id_raises_error(self):
        from solocoder_py.partition_assignor import Partition
        with pytest.raises(ValueError, match="partition_id must be non-negative"):
            Partition(partition_id=-1)


class TestConsumerModel:
    def test_valid_consumer(self):
        from solocoder_py.partition_assignor import Consumer
        c = Consumer(consumer_id="c1")
        assert c.consumer_id == "c1"
        assert c.status == ConsumerStatus.ACTIVE
        assert len(c.assigned_partitions) == 0

    def test_empty_consumer_id_raises_error(self):
        from solocoder_py.partition_assignor import Consumer
        with pytest.raises(ValueError, match="consumer_id must not be empty"):
            Consumer(consumer_id="")


class TestConsumerStatus:
    def test_consumer_status_has_only_active_and_leaving(self):
        assert ConsumerStatus.ACTIVE == "active"
        assert ConsumerStatus.LEAVING == "leaving"
        assert len(ConsumerStatus) == 2


class TestExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(ConsumerAlreadyRegisteredError, PartitionAssignorError)
        assert issubclass(ConsumerNotFoundError, PartitionAssignorError)
        assert issubclass(EmptyConsumerGroupError, PartitionAssignorError)
        assert issubclass(InvalidPartitionIdError, PartitionAssignorError)
        assert issubclass(PartitionNotFoundError, PartitionAssignorError)


class TestConsumerRegistration:
    def test_register_single_consumer(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.register_consumer("consumer-1")
        assert "consumer-1" in [c.consumer_id for c in assignor.get_all_consumers()]

    def test_register_multiple_consumers(self, make_empty_assignor):
        assignor = make_empty_assignor()
        for i in range(5):
            assignor.register_consumer(f"consumer-{i}")
        assert len(assignor.get_all_consumers()) == 5

    def test_register_duplicate_consumer_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.register_consumer("consumer-1")
        with pytest.raises(ConsumerAlreadyRegisteredError):
            assignor.register_consumer("consumer-1")

    def test_unregister_consumer(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assert len(assignor.get_all_consumers()) == 3
        assignor.unregister_consumer("consumer-0")
        assert len(assignor.get_all_consumers()) == 2
        with pytest.raises(ConsumerNotFoundError):
            assignor.get_consumer("consumer-0")

    def test_unregister_nonexistent_consumer_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(ConsumerNotFoundError):
            assignor.unregister_consumer("nonexistent")

    def test_unregister_moves_partitions_to_orphan(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        consumer_0_partitions = assignor.get_assignment("consumer-0")
        assert len(consumer_0_partitions) == 2
        assert len(assignor.get_orphan_partitions()) == 0
        assignor.unregister_consumer("consumer-0")
        orphan_partitions = assignor.get_orphan_partitions()
        assert len(orphan_partitions) == 2
        for pid in consumer_0_partitions:
            assert pid in orphan_partitions


class TestPartitionManagement:
    def test_add_single_partition_goes_to_unassigned(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.add_partitions([0])
        assert len(assignor.get_all_partitions()) == 1
        assert 0 in assignor.get_unassigned_partitions()
        assert 0 not in assignor.get_orphan_partitions()

    def test_add_multiple_partitions_go_to_unassigned(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.add_partitions(range(10))
        assert len(assignor.get_all_partitions()) == 10
        assert len(assignor.get_unassigned_partitions()) == 10
        assert len(assignor.get_orphan_partitions()) == 0

    def test_unassigned_and_orphan_are_separate(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=4)
        assert len(assignor.get_unassigned_partitions()) == 0
        assert len(assignor.get_orphan_partitions()) == 0
        assignor.add_partitions([4, 5])
        assignor.unregister_consumer("consumer-0")
        unassigned = assignor.get_unassigned_partitions()
        orphan = assignor.get_orphan_partitions()
        assert len(unassigned) == 2
        assert len(orphan) == 2
        assert set(unassigned) == {4, 5}
        for pid in orphan:
            assert pid not in unassigned

    def test_add_duplicate_partition_is_idempotent(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.add_partitions([0])
        assignor.add_partitions([0])
        assert len(assignor.get_all_partitions()) == 1
        assert len(assignor.get_unassigned_partitions()) == 1

    def test_add_negative_partition_id_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(InvalidPartitionIdError):
            assignor.add_partitions([-1])

    def test_remove_partition_removes_from_both_unassigned_and_orphan(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=5)
        assert 0 in assignor.get_unassigned_partitions()
        assignor.remove_partitions([0])
        assert len(assignor.get_all_partitions()) == 4
        assert 0 not in assignor.get_unassigned_partitions()
        assert 0 not in assignor.get_orphan_partitions()

    def test_remove_assigned_partition(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assert 0 in [p.partition_id for p in assignor.get_all_partitions()]
        assignor.remove_partitions([0])
        assert 0 not in [p.partition_id for p in assignor.get_all_partitions()]
        all_assigned = set()
        for cid in [c.consumer_id for c in assignor.get_all_consumers()]:
            all_assigned.update(assignor.get_assignment(cid))
        assert 0 not in all_assigned

    def test_remove_nonexistent_partition_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(PartitionNotFoundError):
            assignor.remove_partitions([999])


class TestEvenRebalanceOnConsumerJoin:
    def test_initial_rebalance_distributes_evenly(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=9)
        for i in range(3):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        assert result.generation_id == 1
        for cid, partitions in result.assignments.items():
            assert len(partitions) == 3

    def test_adding_consumer_triggers_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=9)
        for cid, partitions in assignor.get_all_assignments().items():
            assert len(partitions) == 3
        assignor.register_consumer("consumer-3")
        result = assignor.rebalance()
        assert result.generation_id == 2
        for cid, partitions in result.assignments.items():
            assert len(partitions) in (2, 3)
        total = sum(len(p) for p in result.assignments.values())
        assert total == 9

    def test_rebalance_with_uneven_partitions(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=10)
        for i in range(3):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        partition_counts = [len(p) for p in result.assignments.values()]
        partition_counts.sort()
        assert partition_counts == [3, 3, 4]
        total = sum(partition_counts)
        assert total == 10

    def test_rebalance_assigns_all_partitions(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=7)
        for i in range(2):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert all_assigned == set(range(7))
        assert len(assignor.get_orphan_partitions()) == 0
        assert len(assignor.get_unassigned_partitions()) == 0

    def test_no_partition_assigned_to_multiple_consumers(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=20)
        for i in range(5):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        all_assigned = []
        for partitions in result.assignments.values():
            all_assigned.extend(partitions)
        assert len(all_assigned) == len(set(all_assigned))


class TestEvenRebalanceOnConsumerLeave:
    def test_removing_consumer_triggers_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=9)
        assignor.unregister_consumer("consumer-2")
        result = assignor.rebalance()
        for cid, partitions in result.assignments.items():
            assert len(partitions) in (4, 5)
        total = sum(len(p) for p in result.assignments.values())
        assert total == 9

    def test_all_partitions_assigned_after_consumer_removal(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=12)
        assignor.unregister_consumer("consumer-0")
        assignor.unregister_consumer("consumer-1")
        result = assignor.rebalance()
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert all_assigned == set(range(12))
        assert len(assignor.get_orphan_partitions()) == 0


class TestRebalanceOnPartitionChange:
    def test_adding_partitions_triggers_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        for cid, partitions in assignor.get_all_assignments().items():
            assert len(partitions) == 2
        assignor.add_partitions([6, 7, 8])
        result = assignor.rebalance()
        for cid, partitions in result.assignments.items():
            assert len(partitions) == 3

    def test_removing_partitions_triggers_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=9)
        assignor.remove_partitions([0, 1, 2])
        result = assignor.rebalance()
        for cid, partitions in result.assignments.items():
            assert len(partitions) == 2
        total = sum(len(p) for p in result.assignments.values())
        assert total == 6


class TestStickyAssignment:
    def test_sticky_keeps_existing_assignments_on_join(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=6)
        before = assignor.get_all_assignments()
        assignor.register_consumer("consumer-2")
        result = assignor.rebalance()
        kept_total = 0
        for cid in ["consumer-0", "consumer-1"]:
            before_set = set(before[cid])
            after_set = set(result.assignments[cid])
            kept = before_set & after_set
            kept_total += len(kept)
            assert len(kept) >= 2
        assert kept_total >= 4

    def test_sticky_minimizes_partition_movement(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=12)
        before = assignor.get_all_assignments()
        assignor.register_consumer("consumer-4")
        result = assignor.rebalance()
        total_moved = 0
        for change in result.changes:
            total_moved += len(change.revoked_partitions)
        assert total_moved <= 3

    def test_sticky_preserves_all_when_no_change_needed(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=9)
        before = assignor.get_all_assignments()
        result = assignor.rebalance()
        for cid in before:
            assert set(before[cid]) == set(result.assignments[cid])
        total_moved = sum(len(c.revoked_partitions) for c in result.changes)
        assert total_moved == 0


class TestOrphanPartitionRecovery:
    def test_orphan_partitions_are_recovered_on_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.unregister_consumer("consumer-0")
        orphans = assignor.get_orphan_partitions()
        assert len(orphans) == 2
        result = assignor.rebalance()
        assert len(result.orphan_partitions_recovered) == 2
        for pid in orphans:
            assert pid in result.orphan_partitions_recovered
        assert len(assignor.get_orphan_partitions()) == 0

    def test_orphan_partitions_distributed_evenly(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=6)
        assignor.unregister_consumer("consumer-0")
        result = assignor.rebalance()
        assert len(result.orphan_partitions_recovered) == 3
        assert len(result.assignments["consumer-1"]) == 6

    def test_consumer_removal_creates_orphans_then_recovery(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=5, num_partitions=10)
        removed_consumer = "consumer-2"
        removed_partitions = set(assignor.get_assignment(removed_consumer))
        assert len(removed_partitions) == 2
        assignor.unregister_consumer(removed_consumer)
        assert len(assignor.get_orphan_partitions()) == 2
        result = assignor.rebalance()
        assert set(result.orphan_partitions_recovered) == removed_partitions
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert removed_partitions.issubset(all_assigned)

    def test_orphan_partitions_priority_over_unassigned(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.add_partitions([0, 1, 2, 3, 4, 5])
        assignor.register_consumer("consumer-0")
        assignor.register_consumer("consumer-1")
        assignor.rebalance()
        assert len(assignor.get_orphan_partitions()) == 0
        assert len(assignor.get_unassigned_partitions()) == 0
        assignor.unregister_consumer("consumer-0")
        assignor.add_partitions([6, 7])
        assert len(assignor.get_orphan_partitions()) == 3
        assert len(assignor.get_unassigned_partitions()) == 2
        result = assignor.rebalance()
        assert len(result.orphan_partitions_recovered) == 3
        assert len(assignor.get_orphan_partitions()) == 0
        assert len(assignor.get_unassigned_partitions()) == 0
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert all_assigned == {0, 1, 2, 3, 4, 5, 6, 7}

    def test_unregister_orphans_not_in_heartbeat_timeout_field(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        consumer_0_partitions = set(assignor.get_assignment("consumer-0"))
        assignor.unregister_consumer("consumer-0")
        result = assignor.rebalance()
        assert set(result.orphan_partitions_recovered) == consumer_0_partitions
        assert len(result.heartbeat_timeout_orphans_recovered) == 0

    def test_mixed_orphans_unregister_and_timeout_distinguished(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=8)
        consumer_0_partitions = set(assignor.get_assignment("consumer-0"))
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 50.0)
        assignor.heartbeat("consumer-2", 100.0)
        assignor.heartbeat("consumer-3", 100.0)
        consumer_1_partitions = set(assignor.get_assignment("consumer-1"))
        assignor.unregister_consumer("consumer-0")
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        all_orphans = consumer_0_partitions | consumer_1_partitions
        assert set(result.orphan_partitions_recovered) == all_orphans
        assert set(result.heartbeat_timeout_orphans_recovered) == consumer_1_partitions
        for pid in consumer_0_partitions:
            assert pid not in result.heartbeat_timeout_orphans_recovered
        total = sum(len(p) for p in result.assignments.values())
        assert total == 8


class TestHeartbeatTimeout:
    def test_heartbeat_updates_timestamp(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.register_consumer("consumer-0")
        assignor.heartbeat("consumer-0", 100.0)
        consumer = assignor.get_consumer("consumer-0")
        assert consumer.last_heartbeat == 100.0

    def test_check_heartbeat_timeout_marks_leaving(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 50.0)
        timed_out = assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        assert len(timed_out) == 1
        assert "consumer-2" in timed_out
        assert assignor.get_consumer("consumer-0").status == ConsumerStatus.ACTIVE
        assert assignor.get_consumer("consumer-1").status == ConsumerStatus.ACTIVE
        assert assignor.get_consumer("consumer-2").status == ConsumerStatus.LEAVING

    def test_check_heartbeat_timeout_no_timeout(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 100.0)
        timed_out = assignor.check_heartbeat_timeout(current_time=129.0, timeout_seconds=30.0)
        assert len(timed_out) == 0
        for consumer in assignor.get_all_consumers():
            assert consumer.status == ConsumerStatus.ACTIVE

    def test_check_heartbeat_timeout_multiple_consumers(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=8)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 50.0)
        assignor.heartbeat("consumer-2", 40.0)
        assignor.heartbeat("consumer-3", 100.0)
        timed_out = assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        assert len(timed_out) == 2
        assert "consumer-1" in timed_out
        assert "consumer-2" in timed_out
        assert assignor.get_consumer("consumer-1").status == ConsumerStatus.LEAVING
        assert assignor.get_consumer("consumer-2").status == ConsumerStatus.LEAVING

    def test_rebalance_removes_leaving_consumers_and_recovers_partitions(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 50.0)
        consumer_2_partitions = set(assignor.get_assignment("consumer-2"))
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        assert "consumer-2" in assignor.consumers
        assert assignor.get_consumer("consumer-2").status == ConsumerStatus.LEAVING
        result = assignor.rebalance()
        assert "consumer-2" not in assignor.consumers
        assert "consumer-2" not in result.assignments
        assert set(result.orphan_partitions_recovered) == consumer_2_partitions
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert consumer_2_partitions.issubset(all_assigned)
        assert len(assignor.get_orphan_partitions()) == 0

    def test_heartbeat_prevents_timeout(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=4)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-0", 120.0)
        timed_out = assignor.check_heartbeat_timeout(current_time=129.0, timeout_seconds=30.0)
        assert len(timed_out) == 0
        timed_out = assignor.check_heartbeat_timeout(current_time=131.0, timeout_seconds=30.0)
        assert len(timed_out) == 1
        assert "consumer-1" in timed_out

    def test_check_heartbeat_timeout_for_nonexistent_consumer_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(ConsumerNotFoundError):
            assignor.heartbeat("nonexistent", 100.0)

    def test_rebalance_after_all_consumers_timeout_raises_error(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=4)
        assignor.heartbeat("consumer-0", 50.0)
        assignor.heartbeat("consumer-1", 50.0)
        assignor.check_heartbeat_timeout(current_time=100.0, timeout_seconds=30.0)
        with pytest.raises(EmptyConsumerGroupError):
            assignor.rebalance()

    def test_heartbeat_timeout_orphans_recorded_in_result(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 50.0)
        consumer_2_partitions = set(assignor.get_assignment("consumer-2"))
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        assert set(result.heartbeat_timeout_orphans_recovered) == consumer_2_partitions
        assert set(result.orphan_partitions_recovered) == consumer_2_partitions

    def test_no_timeout_heartbeat_orphans_empty(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 100.0)
        assignor.check_heartbeat_timeout(current_time=120.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        assert len(result.heartbeat_timeout_orphans_recovered) == 0

    def test_multiple_heartbeat_timeout_orphans_recorded(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=8)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 50.0)
        assignor.heartbeat("consumer-2", 50.0)
        assignor.heartbeat("consumer-3", 100.0)
        consumer_1_partitions = set(assignor.get_assignment("consumer-1"))
        consumer_2_partitions = set(assignor.get_assignment("consumer-2"))
        all_timeout_partitions = consumer_1_partitions | consumer_2_partitions
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        assert set(result.heartbeat_timeout_orphans_recovered) == all_timeout_partitions
        assert len(result.heartbeat_timeout_orphans_recovered) == 4


class TestBoundaryConditions:
    def test_single_consumer_holds_all_partitions(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=10)
        assignor.register_consumer("consumer-0")
        result = assignor.rebalance()
        assert len(result.assignments["consumer-0"]) == 10
        assert len(assignor.get_orphan_partitions()) == 0
        assert len(assignor.get_unassigned_partitions()) == 0

    def test_partitions_equal_to_consumers(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=5)
        for i in range(5):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        for cid, partitions in result.assignments.items():
            assert len(partitions) == 1
        all_assigned = set()
        for partitions in result.assignments.values():
            all_assigned.update(partitions)
        assert all_assigned == set(range(5))

    def test_more_consumers_than_partitions(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=3)
        for i in range(5):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        consumers_with_partitions = 0
        consumers_idle = 0
        for cid, partitions in result.assignments.items():
            if len(partitions) == 1:
                consumers_with_partitions += 1
            elif len(partitions) == 0:
                consumers_idle += 1
        assert consumers_with_partitions == 3
        assert consumers_idle == 2

    def test_zero_partitions(self, make_empty_assignor):
        assignor = make_empty_assignor()
        for i in range(3):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        for cid, partitions in result.assignments.items():
            assert len(partitions) == 0

    def test_single_partition(self, make_empty_assignor):
        assignor = make_empty_assignor()
        assignor.add_partitions([0])
        for i in range(3):
            assignor.register_consumer(f"consumer-{i}")
        result = assignor.rebalance()
        total = sum(len(p) for p in result.assignments.values())
        assert total == 1
        partition_owner_count = sum(
            1 for p in result.assignments.values() if len(p) == 1
        )
        assert partition_owner_count == 1


class TestErrorCases:
    def test_rebalance_empty_consumer_group_raises_error(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=5)
        with pytest.raises(EmptyConsumerGroupError):
            assignor.rebalance()

    def test_get_nonexistent_consumer_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(ConsumerNotFoundError):
            assignor.get_consumer("nonexistent")

    def test_get_assignment_for_nonexistent_consumer_raises_error(self, make_empty_assignor):
        assignor = make_empty_assignor()
        with pytest.raises(ConsumerNotFoundError):
            assignor.get_assignment("nonexistent")


class TestAssignmentChangeTracking:
    def test_changes_recorded_on_initial_rebalance(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=3)
        assignor.register_consumer("consumer-0")
        result = assignor.rebalance()
        assert len(result.changes) == 1
        change = result.changes[0]
        assert change.consumer_id == "consumer-0"
        assert len(change.assigned_partitions) == 3
        assert len(change.revoked_partitions) == 0

    def test_changes_recorded_on_consumer_join(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=6)
        assignor.register_consumer("consumer-2")
        result = assignor.rebalance()
        assert len(result.changes) >= 1
        new_consumer_change = [
            c for c in result.changes if c.consumer_id == "consumer-2"
        ]
        assert len(new_consumer_change) == 1
        assert len(new_consumer_change[0].assigned_partitions) == 2
        assert len(new_consumer_change[0].revoked_partitions) == 0

    def test_revoked_partitions_recorded(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=2, num_partitions=6)
        assignor.register_consumer("consumer-2")
        result = assignor.rebalance()
        existing_changes = [
            c for c in result.changes if c.consumer_id != "consumer-2"
        ]
        for change in existing_changes:
            assert len(change.assigned_partitions) == 0
            assert len(change.revoked_partitions) == 1


class TestGenerationId:
    def test_generation_id_increments_on_rebalance(self, make_assignor_with_partitions):
        assignor = make_assignor_with_partitions(num_partitions=3)
        assignor.register_consumer("consumer-0")
        assert assignor.generation_id == 0
        result1 = assignor.rebalance()
        assert result1.generation_id == 1
        assert assignor.generation_id == 1
        assignor.register_consumer("consumer-1")
        result2 = assignor.rebalance()
        assert result2.generation_id == 2
        assert assignor.generation_id == 2


class TestPartitionToConsumerMapping:
    def test_each_partition_mapped_to_exactly_one_consumer(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=9)
        assignments = assignor.get_all_assignments()
        partition_to_consumer = {}
        for cid, partitions in assignments.items():
            for pid in partitions:
                assert pid not in partition_to_consumer
                partition_to_consumer[pid] = cid
        assert len(partition_to_consumer) == 9


class TestLeavingStateTransition:
    def test_leaving_consumers_not_in_active_list(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-2", 50.0)
        assignor.check_heartbeat_timeout(current_time=100.0, timeout_seconds=30.0)
        assert assignor.get_consumer("consumer-2").status == ConsumerStatus.LEAVING
        assert len(assignor.get_all_consumers()) == 3

    def test_process_leaving_consumers_on_rebalance(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=3, num_partitions=6)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 100.0)
        assignor.heartbeat("consumer-2", 50.0)
        consumer_2_partitions = set(assignor.get_assignment("consumer-2"))
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        assert "consumer-2" not in assignor.consumers
        assert consumer_2_partitions == set(result.orphan_partitions_recovered)
        total_partitions = sum(len(p) for p in result.assignments.values())
        assert total_partitions == 6

    def test_multiple_leaving_consumers_processed(self, make_balanced_assignor):
        assignor = make_balanced_assignor(num_consumers=4, num_partitions=8)
        assignor.heartbeat("consumer-0", 100.0)
        assignor.heartbeat("consumer-1", 50.0)
        assignor.heartbeat("consumer-2", 50.0)
        assignor.heartbeat("consumer-3", 100.0)
        assignor.check_heartbeat_timeout(current_time=130.0, timeout_seconds=30.0)
        result = assignor.rebalance()
        assert "consumer-1" not in assignor.consumers
        assert "consumer-2" not in assignor.consumers
        assert len(result.assignments) == 2
        total_partitions = sum(len(p) for p in result.assignments.values())
        assert total_partitions == 8
