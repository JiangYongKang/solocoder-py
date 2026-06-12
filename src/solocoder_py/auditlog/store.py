from __future__ import annotations

from typing import Any, List, Optional

from ..seat.clock import Clock, SystemClock
from .exceptions import (
    EmptyAuditLogError,
    InvalidIndexError,
    TimestampRegressionError,
)
from .models import AuditLogEntry, ChainState, compute_hash


class AuditLogStore:
    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._entries: List[AuditLogEntry] = []
        self._chain_hashes: List[str] = []
        self._clock: Clock = clock or SystemClock()

    @property
    def is_empty(self) -> bool:
        return len(self._entries) == 0

    @property
    def length(self) -> int:
        return len(self._entries)

    @property
    def last_entry(self) -> AuditLogEntry:
        if self.is_empty:
            raise EmptyAuditLogError("Cannot get last entry from an empty audit log")
        return self._entries[-1]

    @property
    def genesis_hash(self) -> str:
        if self.is_empty:
            raise EmptyAuditLogError("Cannot get genesis hash from an empty audit log")
        return self._chain_hashes[0]

    @property
    def chain_tip_hash(self) -> str:
        if self.is_empty:
            raise EmptyAuditLogError("Cannot get chain tip hash from an empty audit log")
        return self._chain_hashes[-1]

    def get_chain_state(self) -> ChainState:
        if self.is_empty:
            return ChainState(
                length=0,
                genesis_hash="",
                chain_tip_hash="",
                hashes=[],
            )
        return ChainState(
            length=len(self._entries),
            genesis_hash=self._chain_hashes[0],
            chain_tip_hash=self._chain_hashes[-1],
            hashes=list(self._chain_hashes),
        )

    def append(
        self,
        event_type: str,
        subject: str,
        target: str,
        details: Any = None,
        timestamp: Optional[float] = None,
    ) -> AuditLogEntry:
        ts = timestamp if timestamp is not None else self._clock.now()
        if not self.is_empty:
            last = self.last_entry
            if ts < last.timestamp:
                raise TimestampRegressionError(ts, last.timestamp)
            previous_hash = last.hash
        else:
            previous_hash = ""

        index = len(self._entries)

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
        self._chain_hashes.append(entry_hash)
        return entry

    def get_entry(self, index: int) -> AuditLogEntry:
        if self.is_empty:
            raise EmptyAuditLogError("Cannot get entry from an empty audit log")
        if index < 0 or index >= len(self._entries):
            raise InvalidIndexError(
                f"Index {index} out of range [0, {len(self._entries) - 1}]"
            )
        return self._entries[index]

    def get_entries(self, start: int = 0, end: Optional[int] = None) -> List[AuditLogEntry]:
        if self.is_empty:
            if start == 0 and (end is None or end == 0):
                return []
            raise EmptyAuditLogError("Cannot get entries from an empty audit log")
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

    def verify(self) -> bool:
        if self.is_empty:
            return True
        for i, entry in enumerate(self._entries):
            if entry.hash != self._chain_hashes[i]:
                return False
            expected_prev = self._chain_hashes[i - 1] if i > 0 else ""
            if entry.previous_hash != expected_prev:
                return False
            if entry.compute_hash() != entry.hash:
                return False
        return True

    def _unsafe_replace_entry(self, index: int, entry: AuditLogEntry) -> None:
        self._entries[index] = entry


__all__ = ["AuditLogStore"]
