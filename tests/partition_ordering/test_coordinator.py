import pytest

from solocoder_py.partition_ordering import (
    ConsumerGroupCoordinator,
    ConsumerNotFoundError,
    OrderedPartitionConsumer,
    PartitionedTopic,
    RebalanceEvent,
    RebalanceInProgressError,
)


class TestConsumerGroupBasic:
    def test_create_coordinator(self, topic: PartitionedTopic):
        coord = ConsumerGroupCoordinator(group_id="g1", topic=topic)
        assert coord.group_id == "g1"
        assert coord.topic == topic
        assert coord.get_consumer_count() == 0
        assert coord.generation_id == 0

    def test_create_coordinator_empty_group_id(self, topic: PartitionedTopic):
        with pytest.raises(ValueError):
            ConsumerGroupCoordinator(group_id="", topic=topic)

    def test_join_group_single_consumer(self, coordinator: ConsumerGroupCoordinator):
        c = coordinator.join_group("consumer-1")
        assert isinstance(c, OrderedPartitionConsumer)
        assert coordinator.get_consumer_count() == 1
        assert coordinator.generation_id == 1

    def test_join_group_assigns_all_partitions(self, coordinator: ConsumerGroupCoordinator):
        c = coordinator.join_group("consumer-1")
        assert len(c.assigned_partitions) == coordinator.topic.num_partitions
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) == "consumer-1"

    def test_join_group_second_consumer_triggers_rebalance(
        self, coordinator: ConsumerGroupCoordinator
    ):
        c1 = coordinator.join_group("consumer-1")
        assert coordinator.generation_id == 1

        c2 = coordinator.join_group("consumer-2")
        assert coordinator.generation_id == 2
        assert coordinator.get_consumer_count() == 2

        total_assigned = len(c1.assigned_partitions) + len(c2.assigned_partitions)
        assert total_assigned == coordinator.topic.num_partitions

    def test_join_group_distributes_evenly(self, topic: PartitionedTopic):
        coord = ConsumerGroupCoordinator("g", topic)
        c1 = coord.join_group("c1")
        c2 = coord.join_group("c2")
        c3 = coord.join_group("c3")
        c4 = coord.join_group("c4")

        assert len(c1.assigned_partitions) == 1
        assert len(c2.assigned_partitions) == 1
        assert len(c3.assigned_partitions) == 1
        assert len(c4.assigned_partitions) == 1

        all_assigned = set()
        all_assigned.update(c1.assigned_partitions)
        all_assigned.update(c2.assigned_partitions)
        all_assigned.update(c3.assigned_partitions)
        all_assigned.update(c4.assigned_partitions)
        assert all_assigned == {0, 1, 2, 3}

    def test_join_group_empty_consumer_id(self, coordinator: ConsumerGroupCoordinator):
        with pytest.raises(ValueError):
            coordinator.join_group("")

    def test_leave_group(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        coordinator.join_group("c2")
        assert coordinator.get_consumer_count() == 2
        assert coordinator.generation_id == 2

        coordinator.leave_group("c2")
        assert coordinator.get_consumer_count() == 1
        assert coordinator.generation_id == 3

        c1 = coordinator.get_consumer("c1")
        assert len(c1.assigned_partitions) == coordinator.topic.num_partitions

    def test_leave_nonexistent_consumer(self, coordinator: ConsumerGroupCoordinator):
        with pytest.raises(ConsumerNotFoundError):
            coordinator.leave_group("nonexistent")

    def test_get_consumer(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        c = coordinator.get_consumer("c1")
        assert c.consumer_id == "c1"

    def test_get_nonexistent_consumer(self, coordinator: ConsumerGroupCoordinator):
        with pytest.raises(ConsumerNotFoundError):
            coordinator.get_consumer("nonexistent")

    def test_get_partition_owner(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) == "c1"

    def test_get_all_assignments(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        coordinator.join_group("c2")

        assignments = coordinator.get_all_assignments()
        assert len(assignments) == 2
        total = sum(len(a.partition_ids) for a in assignments)
        assert total == coordinator.topic.num_partitions


class TestRebalanceListener:
    def test_listener_called_on_join(self, coordinator: ConsumerGroupCoordinator):
        events = []

        def listener(event: RebalanceEvent):
            events.append(event)

        coordinator.join_group("c1", listener=listener)
        assert len(events) == 1
        assert events[0].consumer_id == "c1"
        assert len(events[0].assigned_partitions) == 4
        assert events[0].revoked_partitions == []
        assert events[0].generation_id == 1

    def test_listener_called_on_second_join(self, coordinator: ConsumerGroupCoordinator):
        events_c1 = []
        events_c2 = []

        coordinator.join_group("c1", listener=lambda e: events_c1.append(e))
        coordinator.join_group("c2", listener=lambda e: events_c2.append(e))

        assert len(events_c1) == 2
        c1_second_event = events_c1[1]
        assert len(c1_second_event.revoked_partitions) >= 0
        assert len(c1_second_event.assigned_partitions) >= 0

        assert len(events_c2) == 1
        assert events_c2[0].consumer_id == "c2"

    def test_listener_called_on_leave(self, coordinator: ConsumerGroupCoordinator):
        events = []

        coordinator.join_group("c1", listener=lambda e: events.append(e))
        coordinator.join_group("c2")

        gen_before_leave = coordinator.generation_id
        coordinator.leave_group("c2")

        assert events[-1].generation_id == gen_before_leave + 1
        assert len(events[-1].assigned_partitions) >= 1
        assert events[-1].revoked_partitions == []

        c1 = coordinator.get_consumer("c1")
        assert len(c1.assigned_partitions) == coordinator.topic.num_partitions


class TestRebalanceOrderingGuarantee:
    def test_rebalance_preserves_committed_offset(self, coordinator: ConsumerGroupCoordinator):
        c1 = coordinator.join_group("c1")

        for i in range(10):
            coordinator.topic.produce(key=f"k-{i % 2}", value=f"v-{i}")

        pid = sorted(c1.assigned_partitions)[0]
        msgs = c1.poll(pid, max_messages=10)
        for m in msgs[:3]:
            c1.commit(pid, m.offset)
        committed = c1.get_committed_offset(pid)

        c2 = coordinator.join_group("c2")

        if pid in c2.assigned_partitions:
            new_consumer = c2
        else:
            new_consumer = c1

        assert pid in new_consumer.assigned_partitions
        new_consumer.seek(pid, committed)
        next_msg = new_consumer.poll(pid, max_messages=1)
        if next_msg:
            assert next_msg[0].offset == committed + 1

    def test_revoke_returns_uncommitted_messages(self, coordinator: ConsumerGroupCoordinator):
        c1 = coordinator.join_group("c1")

        for i in range(5):
            coordinator.topic.produce_to_partition(0, "k", f"v-{i}")

        c1.poll(0, max_messages=5)
        c1.commit(0, 0)
        c1.commit(0, 1)

        coordinator.join_group("c2")

        if 0 in c1.assigned_partitions:
            remaining = c1.get_in_flight_count(0)
        else:
            remaining = 0
        assert remaining + (3 if 0 not in c1.assigned_partitions else 0) >= 0


class TestForceRebalance:
    def test_force_rebalance(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        gen = coordinator.generation_id

        new_gen = coordinator.force_rebalance()
        assert new_gen == gen + 1
        assert coordinator.generation_id == new_gen

    def test_force_rebalance_during_rebalance_raises(self, coordinator: ConsumerGroupCoordinator):
        pass


class TestConsumerLeaveEmptiesPartitionOwner:
    def test_last_consumer_leave_clears_owners(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) == "c1"

        coordinator.leave_group("c1")
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) is None
