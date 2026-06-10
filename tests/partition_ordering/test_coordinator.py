import pytest

from solocoder_py.partition_ordering import (
    ConsumerGroupCoordinator,
    ConsumerNotFoundError,
    OrderedPartitionConsumer,
    PartitionAlreadyAssignedError,
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

    def test_get_group_committed_offset_empty(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        assert coordinator.get_group_committed_offset(0) == -1


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


class TestRebalanceOffsetInheritance:
    def test_rebalance_auto_inherits_committed_offset_no_seek(
        self, coordinator: ConsumerGroupCoordinator
    ):
        for pid in range(coordinator.topic.num_partitions):
            for i in range(10):
                coordinator.topic.produce_to_partition(pid, f"k-{pid}", f"v-{pid}-{i}")

        c1 = coordinator.join_group("c1")

        test_pid = 1

        msgs = c1.poll(test_pid, max_messages=10)
        assert len(msgs) == 10
        for i in range(5):
            c1.commit(test_pid, i)
        committed_before = c1.get_committed_offset(test_pid)
        assert committed_before == 4

        c2 = coordinator.join_group("c2")

        assert test_pid in c2.assigned_partitions
        assert test_pid not in c1.assigned_partitions

        inherited = c2.get_committed_offset(test_pid)
        assert inherited == committed_before

        next_msgs = c2.poll(test_pid, max_messages=1)
        assert len(next_msgs) == 1
        assert next_msgs[0].offset == committed_before + 1

    def test_seek_backward_then_rebalance_inherits_regressed_offset(
        self, coordinator: ConsumerGroupCoordinator
    ):
        for i in range(20):
            coordinator.topic.produce_to_partition(1, "k", f"v-{i}")

        c1 = coordinator.join_group("c1")

        msgs = c1.poll(1, max_messages=20)
        for i in range(10):
            c1.commit(1, i)
        assert c1.get_committed_offset(1) == 9

        c1.seek(1, 2)
        assert c1.get_committed_offset(1) == 2

        c2 = coordinator.join_group("c2")

        assert 1 in c2.assigned_partitions
        assert 1 not in c1.assigned_partitions

        assert c2.get_committed_offset(1) == 2
        assert coordinator.get_group_committed_offset(1) == 2

        next_msg = c2.poll(1, max_messages=1)
        assert len(next_msg) == 1
        assert next_msg[0].offset == 3

    def test_rebalance_preserves_offset_across_multiple_rebalances(
        self, coordinator: ConsumerGroupCoordinator
    ):
        for pid in range(coordinator.topic.num_partitions):
            for i in range(20):
                coordinator.topic.produce_to_partition(pid, f"k-{pid}", f"v-{pid}-{i}")

        c1 = coordinator.join_group("c1")
        test_pid = 2

        msgs = c1.poll(test_pid, max_messages=20)
        for i in range(7):
            c1.commit(test_pid, i)
        committed_val = c1.get_committed_offset(test_pid)
        assert committed_val == 6

        c2 = coordinator.join_group("c2")
        assert coordinator.get_group_committed_offset(test_pid) == committed_val
        assert test_pid in c1.assigned_partitions

        c3 = coordinator.join_group("c3")
        assert coordinator.get_group_committed_offset(test_pid) == committed_val

        assert test_pid in c3.assigned_partitions
        assert test_pid not in c1.assigned_partitions
        assert c3.get_committed_offset(test_pid) == committed_val

        next_batch = c3.poll(test_pid, max_messages=1)
        assert len(next_batch) == 1
        assert next_batch[0].offset == committed_val + 1

    def test_leave_group_preserves_offsets_in_group_store(
        self, coordinator: ConsumerGroupCoordinator
    ):
        for i in range(15):
            coordinator.topic.produce_to_partition(0, "k", f"v-{i}")

        c1 = coordinator.join_group("c1")
        msgs = c1.poll(0, max_messages=15)
        for i in range(10):
            c1.commit(0, i)
        committed = c1.get_committed_offset(0)
        assert committed == 9

        coordinator.leave_group("c1")
        assert coordinator.get_group_committed_offset(0) == committed

        c2 = coordinator.join_group("c2")
        assert 0 in c2.assigned_partitions
        assert c2.get_committed_offset(0) == committed

        next_msg = c2.poll(0, max_messages=1)
        assert len(next_msg) == 1
        assert next_msg[0].offset == committed + 1


class TestRebalanceOrderingGuarantee:
    def test_revoke_partition_returns_uncommitted_messages(self, topic: PartitionedTopic):
        consumer = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        consumer.assign_partition(0)

        for i in range(5):
            topic.produce_to_partition(0, "k", f"v-{i}")

        msgs = consumer.poll(0, max_messages=5)
        assert len(msgs) == 5

        consumer.commit(0, 0)
        consumer.commit(0, 1)
        assert consumer.get_committed_offset(0) == 1

        revoked = consumer.revoke_partition(0)

        assert len(revoked) == 3
        assert [m.offset for m in revoked] == [2, 3, 4]
        assert [m.value for m in revoked] == ["v-2", "v-3", "v-4"]

    def test_revoke_returns_empty_when_no_in_flight(self, topic: PartitionedTopic):
        consumer = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        consumer.assign_partition(0)

        revoked = consumer.revoke_partition(0)
        assert revoked == []

    def test_revoke_unassigned_partition_returns_empty(self, topic: PartitionedTopic):
        consumer = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        revoked = consumer.revoke_partition(99)
        assert revoked == []


class TestForceRebalance:
    def test_force_rebalance(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        gen = coordinator.generation_id

        new_gen = coordinator.force_rebalance()
        assert new_gen == gen + 1
        assert coordinator.generation_id == new_gen

    def test_force_rebalance_during_rebalance_raises_via_listener(
        self, coordinator: ConsumerGroupCoordinator
    ):
        caught = []

        def listener(event: RebalanceEvent):
            try:
                coordinator.force_rebalance()
            except RebalanceInProgressError as e:
                caught.append(e)

        coordinator.join_group("c1", listener=listener)

        assert len(caught) == 1
        assert isinstance(caught[0], RebalanceInProgressError)
        assert coordinator.is_rebalancing is False

    def test_join_during_rebalance_raises_via_listener(
        self, coordinator: ConsumerGroupCoordinator
    ):
        join_errors = []
        leave_errors = []

        def listener(event: RebalanceEvent):
            try:
                coordinator.join_group("intruder")
            except RebalanceInProgressError as e:
                join_errors.append(e)
            try:
                coordinator.leave_group("c1")
            except RebalanceInProgressError as e:
                leave_errors.append(e)

        coordinator.join_group("c1", listener=listener)

        assert len(join_errors) == 1
        assert len(leave_errors) == 1
        assert isinstance(join_errors[0], RebalanceInProgressError)
        assert isinstance(leave_errors[0], RebalanceInProgressError)
        assert coordinator.is_rebalancing is False
        assert coordinator.get_consumer_count() == 1

    def test_is_rebalancing_reflects_state_via_listener(
        self, coordinator: ConsumerGroupCoordinator
    ):
        observed_states = []

        def listener(event: RebalanceEvent):
            observed_states.append(coordinator.is_rebalancing)

        assert coordinator.is_rebalancing is False
        coordinator.join_group("c1", listener=listener)
        assert coordinator.is_rebalancing is False
        assert observed_states == [True]


class TestDuplicateAssignmentDetection:
    def test_assign_partition_twice_raises(self, topic: PartitionedTopic):
        consumer = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        consumer.assign_partition(0)
        with pytest.raises(PartitionAlreadyAssignedError):
            consumer.assign_partition(0)

    def test_assign_partition_twice_different_initial_offsets_raises(
        self, topic: PartitionedTopic
    ):
        consumer = OrderedPartitionConsumer(consumer_id="c1", topic=topic)
        consumer.assign_partition(0, initial_committed_offset=5)
        with pytest.raises(PartitionAlreadyAssignedError):
            consumer.assign_partition(0, initial_committed_offset=10)

    def test_duplicate_assignment_error_message_includes_consumer_and_partition(
        self, topic: PartitionedTopic
    ):
        consumer = OrderedPartitionConsumer(consumer_id="my-consumer", topic=topic)
        consumer.assign_partition(3)
        with pytest.raises(PartitionAlreadyAssignedError, match="my-consumer"):
            consumer.assign_partition(3)
        with pytest.raises(PartitionAlreadyAssignedError, match="3"):
            consumer.assign_partition(3)

    def test_force_rebalance_no_spurious_duplicate(
        self, coordinator: ConsumerGroupCoordinator
    ):
        coordinator.join_group("c1")
        coordinator.join_group("c2")
        coordinator.force_rebalance()
        coordinator.force_rebalance()
        assert coordinator.get_consumer_count() == 2

    def test_ownership_conflict_detected_on_force_rebalance_public_path(
        self, coordinator: ConsumerGroupCoordinator
    ):
        c1 = coordinator.join_group("c1")
        c2 = coordinator.join_group("c2")

        assert 0 in c1.assigned_partitions
        assert 1 in c2.assigned_partitions

        c2.assign_partition(0)
        assert 0 in c1.assigned_partitions
        assert 0 in c2.assigned_partitions

        with pytest.raises(PartitionAlreadyAssignedError, match="multiple consumers"):
            coordinator.force_rebalance()


class TestConsumerLeaveEmptiesPartitionOwner:
    def test_last_consumer_leave_clears_owners(self, coordinator: ConsumerGroupCoordinator):
        coordinator.join_group("c1")
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) == "c1"

        coordinator.leave_group("c1")
        for pid in range(coordinator.topic.num_partitions):
            assert coordinator.get_partition_owner(pid) is None

    def test_leave_consumer_stores_offsets_in_group(self, coordinator: ConsumerGroupCoordinator):
        for i in range(10):
            coordinator.topic.produce_to_partition(1, "k", f"v-{i}")

        c1 = coordinator.join_group("c1")
        msgs = c1.poll(1, max_messages=10)
        for i in range(6):
            c1.commit(1, i)

        coordinator.leave_group("c1")
        assert coordinator.get_group_committed_offset(1) == 5
