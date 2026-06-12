from __future__ import annotations

from typing import Any, List, Optional

from ..seat.clock import Clock, SystemClock
from .exceptions import (
    EmptyAuditLogError,
    InvalidIndexError,
    TimestampRegressionError,
)
from .models import AuditLogEntry, compute_hash


class AuditLogStore:
    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._entries: List[AuditLogEntry] = []
        self._clock: Clock = clock or SystemClock()

    @property
    def is_empty(self) -> bool:
        return len(self._entries) == 0

    @property
    def length(self) -> int:
        return len(self._entries)

    @property
    def last_entry(self) -> Optional[AuditLogEntry]:
        if self.is_empty:
            return None
        return self._entries[-1]

    def append(
        self,
        event_type: str,
        subject: str,
        target: str,
        details: Any = None,
        timestamp: Optional[float] = None,
    ) -> AuditLogEntry:
        ts = timestamp if timestamp is not None else self._clock.now()
        last = self.last_entry

        if last is not None and ts < last.timestamp:
            raise TimestampRegressionError(ts, last.timestamp)

        index = len(self._entries)
        previous_hash = last.hash if last is not None else ""

        temp_entry = AuditLogEntry(
            index=index,
            event_type=event_type,
            subject=subject,
            target=target,
            timestamp=ts,
            details=details,
            previous_hash=previous_hash,
        )
        entry_hash = temp_entry.compute_hash()

        entry = AuditLogEntry(
            index=index,
            event_type=event_type,
            subject=subject,
            target=target,
            timestamp=ts,
            details=details,
            previous_hash=previous_hash,
            hash=entry_hash,
        )

        self._entries.append(entry)
        return entry

    def get_entry(self, index: int) -> AuditLogEntry:
        if index < 0 or index >= len(self._entries):
            raise InvalidIndexError(
                f"Index {index} out of range [0, {len(self._entries) - 1}]"
            )
        return self._entries[index]

    def get_entries(self, start: int = 0, end: Optional[int] = None) -> List[AuditLogEntry]:
        if start < 0 or start > len(self._entries):
            raise InvalidIndexError(f"Start index {start} out of range")
        if end is None:
            end = len(self._entries)
        if end < start or end > len(self._entries):
            raise InvalidIndexError(
                f"End index {end} out of range or less than start {start}"
            )
        return list(self._entries[start:end])

    def get_all_entries(self) -> List[AuditLogEntry]:
        return list(self._entries)

    def _unsafe_replace_entry(self, index: int, entry: AuditLogEntry) -> None:
        self._entries[index] = entry


__all__ = ["AuditLogStore"]
