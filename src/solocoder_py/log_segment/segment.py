from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from .entry import LogEntry
from .exceptions import SegmentRecycledError, SegmentAlreadyRecycledError


@dataclass
class LogSegment:
    segment_id: int
    created_at: float = field(default_factory=time.time)
    retention_period: Optional[float] = None
    entries: List[LogEntry] = field(default_factory=list)
    physical_size: int = 0
    is_recycled: bool = False
    is_marked_for_recycling: bool = False
    base_logical_offset: int = 0
    next_logical_offset: int = 0

    def append(self, entry: LogEntry) -> int:
        if self.is_recycled:
            raise SegmentRecycledError(f"Segment {self.segment_id} has been recycled")
        entry.physical_offset = self.physical_size
        entry.logical_offset = self.next_logical_offset
        self.entries.append(entry)
        self.physical_size += entry.size()
        self.next_logical_offset += 1
        return entry.logical_offset

    def read_at(self, physical_offset: int) -> Optional[LogEntry]:
        if self.is_recycled:
            raise SegmentRecycledError(f"Segment {self.segment_id} has been recycled")
        for entry in self.entries:
            if entry.physical_offset == physical_offset:
                return entry
        return None

    def read_all(self) -> List[LogEntry]:
        if self.is_recycled:
            raise SegmentRecycledError(f"Segment {self.segment_id} has been recycled")
        return list(self.entries)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.retention_period is None:
            return False
        if current_time is None:
            current_time = time.time()
        return (current_time - self.created_at) > self.retention_period

    def mark_for_recycling(self) -> None:
        if self.is_recycled:
            raise SegmentAlreadyRecycledError(f"Segment {self.segment_id} has already been recycled")
        self.is_marked_for_recycling = True

    def recycle(self) -> None:
        if self.is_recycled:
            raise SegmentAlreadyRecycledError(f"Segment {self.segment_id} has already been recycled")
        self.entries.clear()
        self.physical_size = 0
        self.is_recycled = True

    def age(self, current_time: Optional[float] = None) -> float:
        if current_time is None:
            current_time = time.time()
        return current_time - self.created_at

    def count(self) -> int:
        return len(self.entries)

    def last_logical_offset(self) -> int:
        if not self.entries:
            return self.base_logical_offset - 1
        return self.entries[-1].logical_offset

    def first_logical_offset(self) -> int:
        if not self.entries:
            return self.base_logical_offset
        return self.entries[0].logical_offset

    def compacted_copy(self, retained_entries: List[LogEntry]) -> "LogSegment":
        new_segment = LogSegment(
            segment_id=self.segment_id,
            created_at=self.created_at,
            retention_period=self.retention_period,
            base_logical_offset=self.base_logical_offset,
            next_logical_offset=self.next_logical_offset,
        )
        new_segment.entries = []
        new_physical_offset = 0
        for entry in retained_entries:
            new_entry = LogEntry(
                key=entry.key,
                value=entry.value,
                logical_offset=entry.logical_offset,
                physical_offset=new_physical_offset,
                timestamp=entry.timestamp,
                tombstone=entry.tombstone,
            )
            new_segment.entries.append(new_entry)
            new_physical_offset += new_entry.size()
        new_segment.physical_size = new_physical_offset
        return new_segment

    def replace_entries(self, new_entries: List[LogEntry]) -> None:
        if self.is_recycled:
            raise SegmentRecycledError(f"Segment {self.segment_id} has been recycled")
        self.entries = new_entries
        new_physical_size = 0
        for entry in new_entries:
            entry.physical_offset = new_physical_size
            new_physical_size += entry.size()
        self.physical_size = new_physical_size
