from __future__ import annotations

import threading
from typing import Dict, List, Optional, Type

from .exceptions import (
    AggregateNotFoundError,
    EventOverwriteError,
    EventVersionGapError,
    VersionConflictError,
)
from .models import AggregateRoot, DomainEvent, Snapshot


class EventStore:
    def __init__(self, snapshot_threshold: int = 100) -> None:
        if snapshot_threshold <= 0:
            raise ValueError("snapshot_threshold must be positive")
        self._events: Dict[str, List[DomainEvent]] = {}
        self._snapshots: Dict[str, List[Snapshot]] = {}
        self._snapshot_threshold: int = snapshot_threshold
        self._lock: threading.RLock = threading.RLock()

    @property
    def snapshot_threshold(self) -> int:
        return self._snapshot_threshold

    def _get_event_stream(self, aggregate_id: str) -> List[DomainEvent]:
        return self._events.setdefault(aggregate_id, [])

    def _get_snapshots(self, aggregate_id: str) -> List[Snapshot]:
        return self._snapshots.setdefault(aggregate_id, [])

    def append_events(
        self,
        aggregate_id: str,
        events: List[DomainEvent],
        expected_version: int,
    ) -> None:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        if not events:
            raise ValueError("events cannot be empty")
        if expected_version < 0:
            raise ValueError("expected_version cannot be negative")

        with self._lock:
            stream = self._get_event_stream(aggregate_id)
            current_version = len(stream)

            if current_version != expected_version:
                raise VersionConflictError(aggregate_id, expected_version, current_version)

            for i, event in enumerate(events):
                expected_event_version = expected_version + i + 1
                if event.version != expected_event_version:
                    raise EventVersionGapError(
                        aggregate_id, expected_event_version, event.version
                    )
                if event.aggregate_id != aggregate_id:
                    raise ValueError(
                        f"Event aggregate_id '{event.aggregate_id}' does not match "
                        f"requested aggregate_id '{aggregate_id}'"
                    )

            existing_count = len(stream)
            for event in events:
                idx = event.version - 1
                if idx < existing_count:
                    raise EventOverwriteError(aggregate_id, event.version)

            stream.extend(events)

    def get_events(
        self,
        aggregate_id: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> List[DomainEvent]:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")

        with self._lock:
            stream = self._events.get(aggregate_id)
            if stream is None:
                raise AggregateNotFoundError(
                    f"Aggregate '{aggregate_id}' not found"
                )

            result = list(stream)

            if from_version is not None:
                if from_version < 0:
                    raise ValueError("from_version cannot be negative")
                if from_version > 0:
                    result = [e for e in result if e.version >= from_version]

            if to_version is not None:
                if to_version < 0:
                    raise ValueError("to_version cannot be negative")
                result = [e for e in result if e.version <= to_version]

            if event_type is not None:
                result = [e for e in result if e.event_type == event_type]

            return result

    def get_current_version(self, aggregate_id: str) -> int:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")

        with self._lock:
            stream = self._events.get(aggregate_id)
            if stream is None:
                raise AggregateNotFoundError(
                    f"Aggregate '{aggregate_id}' not found"
                )
            return len(stream)

    def aggregate_exists(self, aggregate_id: str) -> bool:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        with self._lock:
            return aggregate_id in self._events and len(self._events[aggregate_id]) > 0

    def save_snapshot(self, snapshot: Snapshot) -> None:
        with self._lock:
            snapshots = self._get_snapshots(snapshot.aggregate_id)
            snapshots.append(snapshot)

    def get_latest_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")

        with self._lock:
            snapshots = self._snapshots.get(aggregate_id)
            if not snapshots:
                return None
            return max(snapshots, key=lambda s: s.version)

    def get_snapshot_at_or_before(
        self, aggregate_id: str, version: int
    ) -> Optional[Snapshot]:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        if version < 0:
            raise ValueError("version cannot be negative")

        with self._lock:
            snapshots = self._snapshots.get(aggregate_id)
            if not snapshots:
                return None
            candidates = [s for s in snapshots if s.version <= version]
            if not candidates:
                return None
            return max(candidates, key=lambda s: s.version)

    def should_create_snapshot(self, aggregate_id: str) -> bool:
        with self._lock:
            stream = self._events.get(aggregate_id, [])
            event_count = len(stream)
            if event_count == 0:
                return False

            latest_snapshot = self.get_latest_snapshot(aggregate_id)
            if latest_snapshot is None:
                return event_count >= self._snapshot_threshold

            events_since_snapshot = event_count - latest_snapshot.version
            return events_since_snapshot >= self._snapshot_threshold

    def create_snapshot(
        self,
        aggregate: AggregateRoot,
    ) -> Snapshot:
        snapshot = Snapshot(
            aggregate_id=aggregate.id,
            aggregate_type=aggregate.get_aggregate_type(),
            state=aggregate.get_snapshot_state(),
            version=aggregate.version,
        )
        self.save_snapshot(snapshot)
        return snapshot

    def load_aggregate(
        self,
        aggregate_id: str,
        aggregate_class: Type[AggregateRoot],
    ) -> AggregateRoot:
        if not aggregate_id:
            raise ValueError("aggregate_id cannot be empty")

        with self._lock:
            if not self.aggregate_exists(aggregate_id):
                raise AggregateNotFoundError(
                    f"Aggregate '{aggregate_id}' not found"
                )

            latest_snapshot = self.get_latest_snapshot(aggregate_id)

            if latest_snapshot is not None:
                events_after = self.get_events(
                    aggregate_id, from_version=latest_snapshot.version + 1
                )
                return aggregate_class.from_snapshot(
                    aggregate_id, latest_snapshot, events_after
                )
            else:
                all_events = self.get_events(aggregate_id)
                return aggregate_class.from_events(aggregate_id, all_events)

    def save_aggregate(self, aggregate: AggregateRoot) -> None:
        pending = aggregate.pending_events
        if not pending:
            return

        current_version = aggregate.version - len(pending)

        with self._lock:
            self.append_events(
                aggregate.id, pending, expected_version=current_version
            )

            snapshot_to_save: Optional[Snapshot] = None
            if self.should_create_snapshot(aggregate.id):
                snapshot_to_save = Snapshot(
                    aggregate_id=aggregate.id,
                    aggregate_type=aggregate.get_aggregate_type(),
                    state=aggregate.get_snapshot_state(),
                    version=aggregate.version,
                )

            if snapshot_to_save is not None:
                self.save_snapshot(snapshot_to_save)

        aggregate.clear_pending_events()

    def query_events(
        self,
        aggregate_id: Optional[str] = None,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
        event_type: Optional[str] = None,
    ) -> List[DomainEvent]:
        with self._lock:
            if aggregate_id is not None:
                if not self.aggregate_exists(aggregate_id):
                    return []
                return self.get_events(aggregate_id, from_version, to_version, event_type)

            all_events: List[DomainEvent] = []
            for aid in self._events:
                evts = self.get_events(aid, from_version, to_version, event_type)
                all_events.extend(evts)

            all_events.sort(key=lambda e: (e.occurred_at, e.version))
            return all_events

    def list_aggregate_ids(self) -> List[str]:
        with self._lock:
            return [aid for aid, events in self._events.items() if len(events) > 0]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._snapshots.clear()
