from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .exceptions import EventVersionGapError, InvalidEventError


@dataclass
class DomainEvent:
    aggregate_id: str
    event_type: str
    payload: Dict[str, Any]
    version: int
    occurred_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if self.version <= 0:
            raise ValueError("version must be positive")
        if self.payload is None:
            raise ValueError("payload cannot be None")


@dataclass
class Snapshot:
    aggregate_id: str
    aggregate_type: str
    state: Dict[str, Any]
    version: int
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        if not self.aggregate_type:
            raise ValueError("aggregate_type cannot be empty")
        if self.version < 0:
            raise ValueError("version cannot be negative")
        if self.state is None:
            raise ValueError("state cannot be None")


class AggregateRoot(ABC):
    def __init__(self, aggregate_id: str) -> None:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        self._id: str = aggregate_id
        self._version: int = 0
        self._pending_events: List[DomainEvent] = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    @property
    def pending_events(self) -> List[DomainEvent]:
        return list(self._pending_events)

    def clear_pending_events(self) -> None:
        self._pending_events.clear()

    @abstractmethod
    def _apply(self, event: DomainEvent) -> None:
        ...

    @abstractmethod
    def get_snapshot_state(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def restore_from_snapshot(self, state: Dict[str, Any], version: int) -> None:
        ...

    def apply_event(self, event: DomainEvent) -> None:
        if event.aggregate_id != self._id:
            raise InvalidEventError(
                f"Event aggregate_id '{event.aggregate_id}' does not match "
                f"aggregate id '{self._id}'"
            )
        expected_version = self._version + 1
        if event.version != expected_version:
            raise EventVersionGapError(self._id, expected_version, event.version)
        self._apply(event)
        self._version = event.version

    def replay_events(self, events: List[DomainEvent]) -> None:
        for event in events:
            self.apply_event(event)

    def _record(self, event: DomainEvent) -> None:
        self.apply_event(event)
        self._pending_events.append(event)

    @classmethod
    @abstractmethod
    def get_aggregate_type(cls) -> str:
        ...

    @classmethod
    def from_events(cls, aggregate_id: str, events: List[DomainEvent]) -> "AggregateRoot":
        aggregate = cls(aggregate_id)
        aggregate.replay_events(events)
        return aggregate

    @classmethod
    def from_snapshot(
        cls,
        aggregate_id: str,
        snapshot: Snapshot,
        events_after_snapshot: Optional[List[DomainEvent]] = None,
    ) -> "AggregateRoot":
        aggregate = cls(aggregate_id)
        aggregate.restore_from_snapshot(snapshot.state, snapshot.version)
        if events_after_snapshot:
            aggregate.replay_events(events_after_snapshot)
        return aggregate
