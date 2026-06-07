from __future__ import annotations

from datetime import datetime
from time import sleep

import pytest

from solocoder_py.event_sourcing import (
    AggregateNotFoundError,
    AggregateRoot,
    DomainEvent,
    EventOverwriteError,
    EventSourcingError,
    EventStore,
    EventVersionGapError,
    InvalidEventError,
    Snapshot,
    VersionConflictError,
)

from .conftest import CounterAggregate


class TestDomainEventModel:
    def test_event_creation(self):
        now = datetime.now()
        event = DomainEvent(
            aggregate_id="agg-1",
            event_type="SomethingHappened",
            payload={"key": "value"},
            version=1,
            occurred_at=now,
        )
        assert event.aggregate_id == "agg-1"
        assert event.event_type == "SomethingHappened"
        assert event.payload == {"key": "value"}
        assert event.version == 1
        assert event.occurred_at == now

    def test_event_default_occurred_at(self):
        before = datetime.now()
        sleep(0.001)
        event = DomainEvent(
            aggregate_id="agg-1",
            event_type="SomethingHappened",
            payload={},
            version=1,
        )
        sleep(0.001)
        after = datetime.now()
        assert before < event.occurred_at < after

    def test_empty_aggregate_id_rejected(self):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            DomainEvent(
                aggregate_id="",
                event_type="SomethingHappened",
                payload={},
                version=1,
            )

    def test_empty_event_type_rejected(self):
        with pytest.raises(ValueError, match="event_type cannot be empty"):
            DomainEvent(
                aggregate_id="agg-1",
                event_type="",
                payload={},
                version=1,
            )

    def test_non_positive_version_rejected(self):
        with pytest.raises(ValueError, match="version must be positive"):
            DomainEvent(
                aggregate_id="agg-1",
                event_type="SomethingHappened",
                payload={},
                version=0,
            )
        with pytest.raises(ValueError, match="version must be positive"):
            DomainEvent(
                aggregate_id="agg-1",
                event_type="SomethingHappened",
                payload={},
                version=-1,
            )

    def test_none_payload_rejected(self):
        with pytest.raises(ValueError, match="payload cannot be None"):
            DomainEvent(
                aggregate_id="agg-1",
                event_type="SomethingHappened",
                payload=None,
                version=1,
            )


class TestSnapshotModel:
    def test_snapshot_creation(self):
        now = datetime.now()
        snapshot = Snapshot(
            aggregate_id="agg-1",
            aggregate_type="Counter",
            state={"count": 10, "name": "my-counter"},
            version=5,
            created_at=now,
        )
        assert snapshot.aggregate_id == "agg-1"
        assert snapshot.aggregate_type == "Counter"
        assert snapshot.state == {"count": 10, "name": "my-counter"}
        assert snapshot.version == 5
        assert snapshot.created_at == now

    def test_empty_aggregate_id_rejected(self):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            Snapshot(
                aggregate_id="",
                aggregate_type="Counter",
                state={},
                version=1,
            )

    def test_empty_aggregate_type_rejected(self):
        with pytest.raises(ValueError, match="aggregate_type cannot be empty"):
            Snapshot(
                aggregate_id="agg-1",
                aggregate_type="",
                state={},
                version=1,
            )

    def test_negative_version_rejected(self):
        with pytest.raises(ValueError, match="version cannot be negative"):
            Snapshot(
                aggregate_id="agg-1",
                aggregate_type="Counter",
                state={},
                version=-1,
            )

    def test_zero_version_allowed(self):
        snapshot = Snapshot(
            aggregate_id="agg-1",
            aggregate_type="Counter",
            state={},
            version=0,
        )
        assert snapshot.version == 0

    def test_none_state_rejected(self):
        with pytest.raises(ValueError, match="state cannot be None"):
            Snapshot(
                aggregate_id="agg-1",
                aggregate_type="Counter",
                state=None,
                version=1,
            )


class TestAggregateRoot:
    def test_counter_create(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        assert counter.id == "counter-1"
        assert counter.name == "my-counter"
        assert counter.count == 0
        assert counter.version == 1
        assert len(counter.pending_events) == 1
        assert counter.pending_events[0].event_type == "CounterCreated"

    def test_counter_increment(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        counter.increment(5)
        assert counter.count == 5
        assert counter.version == 2

    def test_counter_decrement(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        counter.increment(10)
        counter.decrement(3)
        assert counter.count == 7
        assert counter.version == 3

    def test_counter_reset(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        counter.increment(10)
        counter.reset()
        assert counter.count == 0
        assert counter.version == 3

    def test_empty_aggregate_id_rejected(self):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            CounterAggregate("")

    def test_apply_event_wrong_aggregate_id(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        event = DomainEvent(
            aggregate_id="counter-2",
            event_type="CounterIncremented",
            payload={"amount": 1},
            version=2,
        )
        with pytest.raises(InvalidEventError):
            counter.apply_event(event)

    def test_apply_event_version_gap(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        event = DomainEvent(
            aggregate_id="counter-1",
            event_type="CounterIncremented",
            payload={"amount": 1},
            version=5,
        )
        with pytest.raises(EventVersionGapError) as exc:
            counter.apply_event(event)
        assert exc.value.expected_version == 2
        assert exc.value.got_version == 5

    def test_pending_events_is_copy(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        pending = counter.pending_events
        pending.clear()
        assert len(counter.pending_events) == 1

    def test_clear_pending_events(self):
        counter = CounterAggregate("counter-1")
        counter.create("my-counter")
        counter.increment()
        assert len(counter.pending_events) == 2
        counter.clear_pending_events()
        assert len(counter.pending_events) == 0

    def test_from_events_factory(self):
        events = [
            DomainEvent(
                aggregate_id="counter-1",
                event_type="CounterCreated",
                payload={"name": "from-events"},
                version=1,
            ),
            DomainEvent(
                aggregate_id="counter-1",
                event_type="CounterIncremented",
                payload={"amount": 10},
                version=2,
            ),
        ]
        counter = CounterAggregate.from_events("counter-1", events)
        assert counter.id == "counter-1"
        assert counter.name == "from-events"
        assert counter.count == 10
        assert counter.version == 2
        assert len(counter.pending_events) == 0

    def test_from_snapshot_factory(self):
        snapshot = Snapshot(
            aggregate_id="counter-1",
            aggregate_type="Counter",
            state={"count": 42, "name": "from-snapshot"},
            version=3,
        )
        events_after = [
            DomainEvent(
                aggregate_id="counter-1",
                event_type="CounterIncremented",
                payload={"amount": 8},
                version=4,
            ),
        ]
        counter = CounterAggregate.from_snapshot("counter-1", snapshot, events_after)
        assert counter.id == "counter-1"
        assert counter.name == "from-snapshot"
        assert counter.count == 50
        assert counter.version == 4

    def test_from_snapshot_factory_no_events(self):
        snapshot = Snapshot(
            aggregate_id="counter-1",
            aggregate_type="Counter",
            state={"count": 100, "name": "snapshot-only"},
            version=5,
        )
        counter = CounterAggregate.from_snapshot("counter-1", snapshot)
        assert counter.count == 100
        assert counter.name == "snapshot-only"
        assert counter.version == 5

    def test_get_snapshot_state(self):
        counter = CounterAggregate("counter-1")
        counter.create("snap-test")
        counter.increment(7)
        state = counter.get_snapshot_state()
        assert state == {"count": 7, "name": "snap-test"}

    def test_get_aggregate_type(self):
        assert CounterAggregate.get_aggregate_type() == "Counter"


class TestAppendEvents:
    def test_append_single_event_new_aggregate(self, store: EventStore):
        event = DomainEvent(
            aggregate_id="agg-1",
            event_type="SomethingHappened",
            payload={"x": 1},
            version=1,
        )
        store.append_events("agg-1", [event], expected_version=0)
        assert store.aggregate_exists("agg-1") is True
        assert store.get_current_version("agg-1") == 1

    def test_append_multiple_events(self, store: EventStore):
        events = [
            DomainEvent(
                aggregate_id="agg-1",
                event_type="Event1",
                payload={},
                version=1,
            ),
            DomainEvent(
                aggregate_id="agg-1",
                event_type="Event2",
                payload={},
                version=2,
            ),
            DomainEvent(
                aggregate_id="agg-1",
                event_type="Event3",
                payload={},
                version=3,
            ),
        ]
        store.append_events("agg-1", events, expected_version=0)
        assert store.get_current_version("agg-1") == 3

    def test_append_events_incremental(self, store: EventStore):
        store.append_events(
            "agg-1",
            [DomainEvent(aggregate_id="agg-1", event_type="E1", payload={}, version=1)],
            expected_version=0,
        )
        store.append_events(
            "agg-1",
            [DomainEvent(aggregate_id="agg-1", event_type="E2", payload={}, version=2)],
            expected_version=1,
        )
        assert store.get_current_version("agg-1") == 2

    def test_append_version_conflict(self, store: EventStore):
        store.append_events(
            "agg-1",
            [DomainEvent(aggregate_id="agg-1", event_type="E1", payload={}, version=1)],
            expected_version=0,
        )
        with pytest.raises(VersionConflictError) as exc:
            store.append_events(
                "agg-1",
                [DomainEvent(aggregate_id="agg-1", event_type="E2", payload={}, version=2)],
                expected_version=0,
            )
        assert exc.value.aggregate_id == "agg-1"
        assert exc.value.expected_version == 0
        assert exc.value.actual_version == 1

    def test_append_event_version_gap_in_batch(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="E1", payload={}, version=1),
            DomainEvent(aggregate_id="agg-1", event_type="E3", payload={}, version=3),
        ]
        with pytest.raises(EventVersionGapError) as exc:
            store.append_events("agg-1", events, expected_version=0)
        assert exc.value.expected_version == 2
        assert exc.value.got_version == 3

    def test_append_event_mismatched_aggregate_id(self, store: EventStore):
        event = DomainEvent(
            aggregate_id="agg-2",
            event_type="SomethingHappened",
            payload={},
            version=1,
        )
        with pytest.raises(ValueError, match="does not match"):
            store.append_events("agg-1", [event], expected_version=0)

    def test_append_cannot_overwrite_existing_event(self, store: EventStore):
        store.append_events(
            "agg-1",
            [DomainEvent(aggregate_id="agg-1", event_type="E1", payload={}, version=1)],
            expected_version=0,
        )
        with pytest.raises(VersionConflictError):
            store.append_events(
                "agg-1",
                [
                    DomainEvent(aggregate_id="agg-1", event_type="E1-new", payload={}, version=1),
                    DomainEvent(aggregate_id="agg-1", event_type="E2", payload={}, version=2),
                ],
                expected_version=0,
            )

    def test_append_empty_aggregate_id_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            store.append_events(
                "",
                [DomainEvent(aggregate_id="x", event_type="E", payload={}, version=1)],
                expected_version=0,
            )

    def test_append_empty_events_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="events cannot be empty"):
            store.append_events("agg-1", [], expected_version=0)

    def test_append_negative_expected_version_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="expected_version cannot be negative"):
            store.append_events(
                "agg-1",
                [DomainEvent(aggregate_id="agg-1", event_type="E", payload={}, version=1)],
                expected_version=-1,
            )


class TestRebuildAggregateFromEvents:
    def test_rebuild_counter_from_events(self, store: EventStore, make_counter):
        counter = make_counter("counter-1", "rebuild-test")
        counter.increment(3)
        counter.increment(2)
        counter.decrement(1)
        store.save_aggregate(counter)

        loaded = store.load_aggregate("counter-1", CounterAggregate)
        assert loaded.id == "counter-1"
        assert loaded.name == "rebuild-test"
        assert loaded.count == 4
        assert loaded.version == 4

    def test_rebuild_validates_event_order(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="c-1", event_type="CounterCreated", payload={"name": "x"}, version=1),
            DomainEvent(aggregate_id="c-1", event_type="CounterIncremented", payload={"amount": 5}, version=2),
        ]
        store.append_events("c-1", events, expected_version=0)

        loaded = store.load_aggregate("c-1", CounterAggregate)
        assert loaded.count == 5

    def test_load_nonexistent_aggregate_raises(self, store: EventStore):
        with pytest.raises(AggregateNotFoundError):
            store.load_aggregate("nonexistent", CounterAggregate)

    def test_load_empty_aggregate_id_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            store.load_aggregate("", CounterAggregate)


class TestSnapshotMechanism:
    def test_should_create_snapshot_when_threshold_reached(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(3):
            counter.increment()
        store.save_aggregate(counter)
        assert store.should_create_snapshot("counter-1") is False

        counter = store.load_aggregate("counter-1", CounterAggregate)
        counter.increment()
        store.append_events(
            "counter-1",
            counter.pending_events,
            expected_version=store.get_current_version("counter-1"),
        )
        assert store.should_create_snapshot("counter-1") is True
        store.create_snapshot(counter)
        assert store.should_create_snapshot("counter-1") is False

        counter = store.load_aggregate("counter-1", CounterAggregate)
        for _ in range(4):
            counter.increment()
            store.append_events(
                "counter-1",
                counter.pending_events,
                expected_version=store.get_current_version("counter-1"),
            )
            counter.clear_pending_events()
        assert store.should_create_snapshot("counter-1") is False

        counter = store.load_aggregate("counter-1", CounterAggregate)
        counter.increment()
        store.append_events(
            "counter-1",
            counter.pending_events,
            expected_version=store.get_current_version("counter-1"),
        )
        assert store.should_create_snapshot("counter-1") is True

    def test_snapshot_created_automatically_on_save(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)

        assert store.get_latest_snapshot("counter-1") is not None
        snapshot = store.get_latest_snapshot("counter-1")
        assert snapshot.version == 5
        assert snapshot.state["count"] == 4

    def test_load_from_snapshot_with_incremental_events(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)

        counter = store.load_aggregate("counter-1", CounterAggregate)
        counter.increment(10)
        counter.increment(20)
        store.save_aggregate(counter)

        loaded = store.load_aggregate("counter-1", CounterAggregate)
        assert loaded.count == 34
        assert loaded.version == 7
        assert loaded.name == "test-counter"

    def test_snapshot_threshold_exactly_hit(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)

        snap = store.get_latest_snapshot("counter-1")
        assert snap is not None
        assert snap.version == 5

    def test_multiple_snapshots_keeps_latest(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)

        counter = store.load_aggregate("counter-1", CounterAggregate)
        for _ in range(5):
            counter.increment()
        store.save_aggregate(counter)

        snap = store.get_latest_snapshot("counter-1")
        assert snap.version == 10

    def test_get_snapshot_at_or_before(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)

        snap = store.get_snapshot_at_or_before("counter-1", 100)
        assert snap is not None
        assert snap.version == 5

        snap = store.get_snapshot_at_or_before("counter-1", 3)
        assert snap is None

        snap = store.get_snapshot_at_or_before("counter-1", 5)
        assert snap is not None
        assert snap.version == 5

    def test_get_latest_snapshot_nonexistent_aggregate(self, store: EventStore):
        assert store.get_latest_snapshot("nonexistent") is None

    def test_manual_create_snapshot(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        counter.increment(7)
        snap = store.create_snapshot(counter)
        assert snap.aggregate_id == "counter-1"
        assert snap.version == 2
        assert snap.state["count"] == 7
        assert snap.aggregate_type == "Counter"

    def test_empty_aggregate_should_not_create_snapshot(self, store: EventStore):
        assert store.should_create_snapshot("nonexistent") is False


class TestOptimisticConcurrency:
    def test_concurrent_write_conflict_detected(self, store: EventStore, make_counter):
        counter_a = make_counter("counter-1")
        store.save_aggregate(counter_a)

        counter_b = store.load_aggregate("counter-1", CounterAggregate)
        counter_a.increment(10)
        store.save_aggregate(counter_a)

        counter_b.increment(20)
        with pytest.raises(VersionConflictError):
            store.save_aggregate(counter_b)

    def test_sequential_writes_no_conflict(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        store.save_aggregate(counter)

        counter = store.load_aggregate("counter-1", CounterAggregate)
        counter.increment(5)
        store.save_aggregate(counter)

        counter = store.load_aggregate("counter-1", CounterAggregate)
        counter.increment(3)
        store.save_aggregate(counter)

        loaded = store.load_aggregate("counter-1", CounterAggregate)
        assert loaded.count == 8

    def test_version_conflict_error_has_details(self, store: EventStore):
        store.append_events(
            "agg-1",
            [DomainEvent(aggregate_id="agg-1", event_type="E", payload={}, version=1)],
            expected_version=0,
        )
        with pytest.raises(VersionConflictError) as exc:
            store.append_events(
                "agg-1",
                [DomainEvent(aggregate_id="agg-1", event_type="E", payload={}, version=2)],
                expected_version=5,
            )
        assert "agg-1" in str(exc.value)
        assert "5" in str(exc.value)
        assert "1" in str(exc.value)


class TestEventQueryAndAudit:
    def test_get_events_all(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="E1", payload={"i": 1}, version=1),
            DomainEvent(aggregate_id="agg-1", event_type="E2", payload={"i": 2}, version=2),
            DomainEvent(aggregate_id="agg-1", event_type="E1", payload={"i": 3}, version=3),
        ]
        store.append_events("agg-1", events, expected_version=0)

        result = store.get_events("agg-1")
        assert len(result) == 3
        assert [e.version for e in result] == [1, 2, 3]

    def test_get_events_by_version_range(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="E", payload={}, version=i)
            for i in range(1, 6)
        ]
        store.append_events("agg-1", events, expected_version=0)

        result = store.get_events("agg-1", from_version=2, to_version=4)
        assert [e.version for e in result] == [2, 3, 4]

    def test_get_events_by_type(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="Created", payload={}, version=1),
            DomainEvent(aggregate_id="agg-1", event_type="Updated", payload={}, version=2),
            DomainEvent(aggregate_id="agg-1", event_type="Updated", payload={}, version=3),
            DomainEvent(aggregate_id="agg-1", event_type="Deleted", payload={}, version=4),
        ]
        store.append_events("agg-1", events, expected_version=0)

        result = store.get_events("agg-1", event_type="Updated")
        assert len(result) == 2
        assert all(e.event_type == "Updated" for e in result)

    def test_get_events_combined_filters(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="A", payload={}, version=1),
            DomainEvent(aggregate_id="agg-1", event_type="B", payload={}, version=2),
            DomainEvent(aggregate_id="agg-1", event_type="A", payload={}, version=3),
            DomainEvent(aggregate_id="agg-1", event_type="B", payload={}, version=4),
            DomainEvent(aggregate_id="agg-1", event_type="A", payload={}, version=5),
        ]
        store.append_events("agg-1", events, expected_version=0)

        result = store.get_events("agg-1", from_version=2, to_version=4, event_type="A")
        assert len(result) == 1
        assert result[0].version == 3

    def test_get_events_nonexistent_aggregate(self, store: EventStore):
        with pytest.raises(AggregateNotFoundError):
            store.get_events("nonexistent")

    def test_get_events_invalid_from_version(self, store: EventStore, make_counter):
        counter = make_counter("agg-1")
        store.save_aggregate(counter)
        with pytest.raises(ValueError, match="from_version cannot be negative"):
            store.get_events("agg-1", from_version=-1)

    def test_get_events_from_version_zero_allowed(self, store: EventStore, make_counter):
        counter = make_counter("agg-1")
        counter.increment()
        counter.increment()
        store.save_aggregate(counter)
        result = store.get_events("agg-1", from_version=0)
        assert len(result) == 3
        assert [e.version for e in result] == [1, 2, 3]

    def test_get_events_invalid_to_version(self, store: EventStore, make_counter):
        counter = make_counter("agg-1")
        store.save_aggregate(counter)
        with pytest.raises(ValueError, match="to_version cannot be negative"):
            store.get_events("agg-1", to_version=-1)

    def test_get_events_to_version_zero_returns_empty(self, store: EventStore, make_counter):
        counter = make_counter("agg-1")
        counter.increment()
        store.save_aggregate(counter)
        result = store.get_events("agg-1", to_version=0)
        assert len(result) == 0

    def test_query_events_by_aggregate_id(self, store: EventStore, make_counter):
        counter = make_counter("counter-1")
        counter.increment()
        store.save_aggregate(counter)

        result = store.query_events(aggregate_id="counter-1")
        assert len(result) == 2

        result = store.query_events(aggregate_id="nonexistent")
        assert len(result) == 0

    def test_query_events_across_aggregates(self, store: EventStore):
        for i in range(1, 4):
            store.append_events(
                f"agg-{i}",
                [
                    DomainEvent(
                        aggregate_id=f"agg-{i}",
                        event_type="Created",
                        payload={},
                        version=1,
                    )
                ],
                expected_version=0,
            )

        result = store.query_events(event_type="Created")
        assert len(result) == 3
        assert {e.aggregate_id for e in result} == {"agg-1", "agg-2", "agg-3"}

    def test_query_events_empty_aggregate_id_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            store.get_events("")

    def test_aggregate_exists(self, store: EventStore, make_counter):
        assert store.aggregate_exists("c-1") is False
        counter = make_counter("c-1")
        store.save_aggregate(counter)
        assert store.aggregate_exists("c-1") is True

    def test_aggregate_exists_empty_id_rejected(self, store: EventStore):
        with pytest.raises(ValueError, match="aggregate_id cannot be empty"):
            store.aggregate_exists("")

    def test_get_current_version(self, store: EventStore, make_counter):
        counter = make_counter("c-1")
        counter.increment()
        counter.increment()
        store.save_aggregate(counter)
        assert store.get_current_version("c-1") == 3

    def test_get_current_version_nonexistent(self, store: EventStore):
        with pytest.raises(AggregateNotFoundError):
            store.get_current_version("nonexistent")

    def test_list_aggregate_ids(self, store: EventStore, make_counter):
        assert store.list_aggregate_ids() == []
        counter_a = make_counter("a")
        counter_b = make_counter("b")
        store.save_aggregate(counter_a)
        store.save_aggregate(counter_b)
        assert set(store.list_aggregate_ids()) == {"a", "b"}

    def test_event_order_preserved(self, store: EventStore):
        events = [
            DomainEvent(aggregate_id="agg-1", event_type="E", payload={"i": i}, version=i)
            for i in range(1, 11)
        ]
        store.append_events("agg-1", events, expected_version=0)

        result = store.get_events("agg-1")
        assert [e.payload["i"] for e in result] == list(range(1, 11))


class TestEventStoreConfiguration:
    def test_default_snapshot_threshold(self):
        store = EventStore()
        assert store.snapshot_threshold == 100

    def test_custom_snapshot_threshold(self):
        store = EventStore(snapshot_threshold=10)
        assert store.snapshot_threshold == 10

    def test_invalid_snapshot_threshold_rejected(self):
        with pytest.raises(ValueError, match="snapshot_threshold must be positive"):
            EventStore(snapshot_threshold=0)
        with pytest.raises(ValueError, match="snapshot_threshold must be positive"):
            EventStore(snapshot_threshold=-1)

    def test_clear_store(self, store: EventStore, make_counter):
        counter = make_counter("c-1")
        counter.increment(5)
        store.save_aggregate(counter)
        store.create_snapshot(counter)

        assert store.aggregate_exists("c-1") is True
        assert store.get_latest_snapshot("c-1") is not None

        store.clear()
        assert store.aggregate_exists("c-1") is False
        assert store.get_latest_snapshot("c-1") is None


class TestExceptionsHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(AggregateNotFoundError, EventSourcingError)
        assert issubclass(VersionConflictError, EventSourcingError)
        assert issubclass(EventVersionGapError, EventSourcingError)
        assert issubclass(EventOverwriteError, EventSourcingError)
        assert issubclass(InvalidEventError, EventSourcingError)


class TestSaveAggregate:
    def test_save_aggregate_no_pending_events(self, store: EventStore, make_counter):
        counter = make_counter("c-1")
        store.save_aggregate(counter)
        assert store.get_current_version("c-1") == 1

        loaded = store.load_aggregate("c-1", CounterAggregate)
        store.save_aggregate(loaded)
        assert store.get_current_version("c-1") == 1

    def test_save_aggregate_appends_pending(self, store: EventStore, make_counter):
        counter = make_counter("c-1")
        counter.increment(5)
        store.save_aggregate(counter)
        assert len(counter.pending_events) == 0
        assert store.get_current_version("c-1") == 2

    def test_save_aggregate_version_conflict_preserves_pending(self, store: EventStore, make_counter):
        counter_a = make_counter("c-1")
        store.save_aggregate(counter_a)

        counter_b = store.load_aggregate("c-1", CounterAggregate)
        counter_a.increment(10)
        store.save_aggregate(counter_a)

        counter_b.increment(20)
        pending_before = len(counter_b.pending_events)
        with pytest.raises(VersionConflictError):
            store.save_aggregate(counter_b)
        assert len(counter_b.pending_events) == pending_before
        assert store.get_current_version("c-1") == 2

    def test_save_aggregate_snapshot_construct_failure_no_partial_write(
        self, store: EventStore, make_counter, monkeypatch
    ):
        counter = make_counter("c-1")
        for _ in range(4):
            counter.increment()
        store.save_aggregate(counter)
        assert store.get_current_version("c-1") == 5
        assert store.get_latest_snapshot("c-1") is not None

        counter = store.load_aggregate("c-1", CounterAggregate)
        for _ in range(5):
            counter.increment()

        pending_before = list(counter.pending_events)
        version_before = store.get_current_version("c-1")
        snapshot_before = store.get_latest_snapshot("c-1")

        def bad_state(self):
            return None

        monkeypatch.setattr(CounterAggregate, "get_snapshot_state", bad_state)

        with pytest.raises(ValueError, match="state cannot be None"):
            store.save_aggregate(counter)

        assert store.get_current_version("c-1") == version_before
        assert store.get_latest_snapshot("c-1").version == snapshot_before.version
        assert len(counter.pending_events) == len(pending_before)
        assert [e.version for e in counter.pending_events] == [e.version for e in pending_before]


class TestEdgeCases:
    def test_empty_event_stream_load_raises(self, store: EventStore):
        with pytest.raises(AggregateNotFoundError):
            store.load_aggregate("empty-stream", CounterAggregate)

    def test_rebuild_from_single_event(self, store: EventStore, make_counter):
        counter = make_counter("c-1")
        store.save_aggregate(counter)
        loaded = store.load_aggregate("c-1", CounterAggregate)
        assert loaded.version == 1
        assert loaded.count == 0

    def test_event_version_equals_expected_exactly(self, store: EventStore):
        for v in range(1, 6):
            store.append_events(
                "agg-1",
                [DomainEvent(aggregate_id="agg-1", event_type="E", payload={}, version=v)],
                expected_version=v - 1,
            )
        assert store.get_current_version("agg-1") == 5

    def test_snapshot_version_zero_allowed(self, store: EventStore, make_counter):
        counter = CounterAggregate("c-1")
        snap = Snapshot(
            aggregate_id="c-1",
            aggregate_type="Counter",
            state={"count": 0, "name": "zero"},
            version=0,
        )
        store.save_snapshot(snap)
        assert store.get_latest_snapshot("c-1").version == 0

    def test_snapshot_version_zero_plus_from_version_zero_query(self, store: EventStore, make_counter):
        snap = Snapshot(
            aggregate_id="c-1",
            aggregate_type="Counter",
            state={"count": 0, "name": "pre-init"},
            version=0,
        )
        store.save_snapshot(snap)
        store.append_events(
            "c-1",
            [
                DomainEvent(aggregate_id="c-1", event_type="CounterCreated", payload={"name": "real"}, version=1),
                DomainEvent(aggregate_id="c-1", event_type="CounterIncremented", payload={"amount": 7}, version=2),
            ],
            expected_version=0,
        )
        all_via_zero = store.get_events("c-1", from_version=0)
        assert len(all_via_zero) == 2
        assert [e.version for e in all_via_zero] == [1, 2]

        loaded = store.load_aggregate("c-1", CounterAggregate)
        assert loaded.version == 2
        assert loaded.count == 7
        assert loaded.name == "real"
