from __future__ import annotations


class EventSourcingError(Exception):
    pass


class AggregateNotFoundError(EventSourcingError):
    pass


class VersionConflictError(EventSourcingError):
    def __init__(self, aggregate_id: str, expected_version: int, actual_version: int) -> None:
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Version conflict for aggregate '{aggregate_id}': "
            f"expected version {expected_version}, actual version {actual_version}"
        )


class EventVersionGapError(EventSourcingError):
    def __init__(self, aggregate_id: str, expected_version: int, got_version: int) -> None:
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.got_version = got_version
        super().__init__(
            f"Event version gap for aggregate '{aggregate_id}': "
            f"expected version {expected_version}, got {got_version}"
        )


class EventOverwriteError(EventSourcingError):
    def __init__(self, aggregate_id: str, version: int) -> None:
        self.aggregate_id = aggregate_id
        self.version = version
        super().__init__(
            f"Cannot overwrite existing event at version {version} for aggregate '{aggregate_id}'"
        )


class InvalidEventError(EventSourcingError):
    pass


class SnapshotNotFoundError(EventSourcingError):
    pass
