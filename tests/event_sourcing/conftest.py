from __future__ import annotations

from typing import Any, Dict

import pytest

from solocoder_py.event_sourcing import (
    AggregateRoot,
    DomainEvent,
    EventStore,
)


class CounterAggregate(AggregateRoot):
    def __init__(self, aggregate_id: str) -> None:
        super().__init__(aggregate_id)
        self._count: int = 0
        self._name: str = ""

    @classmethod
    def get_aggregate_type(cls) -> str:
        return "Counter"

    @property
    def count(self) -> int:
        return self._count

    @property
    def name(self) -> str:
        return self._name

    def _apply(self, event: DomainEvent) -> None:
        if event.event_type == "CounterCreated":
            self._name = event.payload["name"]
        elif event.event_type == "CounterIncremented":
            self._count += event.payload.get("amount", 1)
        elif event.event_type == "CounterDecremented":
            self._count -= event.payload.get("amount", 1)
        elif event.event_type == "CounterReset":
            self._count = 0

    def get_snapshot_state(self) -> Dict[str, Any]:
        return {"count": self._count, "name": self._name}

    def restore_from_snapshot(self, state: Dict[str, Any], version: int) -> None:
        self._count = state["count"]
        self._name = state["name"]
        self._version = version

    def create(self, name: str) -> None:
        event = DomainEvent(
            aggregate_id=self.id,
            event_type="CounterCreated",
            payload={"name": name},
            version=self.version + 1,
        )
        self._record(event)

    def increment(self, amount: int = 1) -> None:
        event = DomainEvent(
            aggregate_id=self.id,
            event_type="CounterIncremented",
            payload={"amount": amount},
            version=self.version + 1,
        )
        self._record(event)

    def decrement(self, amount: int = 1) -> None:
        event = DomainEvent(
            aggregate_id=self.id,
            event_type="CounterDecremented",
            payload={"amount": amount},
            version=self.version + 1,
        )
        self._record(event)

    def reset(self) -> None:
        event = DomainEvent(
            aggregate_id=self.id,
            event_type="CounterReset",
            payload={},
            version=self.version + 1,
        )
        self._record(event)


@pytest.fixture
def store() -> EventStore:
    return EventStore(snapshot_threshold=5)


@pytest.fixture
def make_counter():
    def _make(counter_id: str, name: str = "test-counter") -> CounterAggregate:
        counter = CounterAggregate(counter_id)
        counter.create(name)
        return counter

    return _make
