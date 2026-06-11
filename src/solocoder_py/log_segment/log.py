from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time

from .compactor import CompactionResult, LogCompactor
from .entry import LogEntry
from .exceptions import (
    CompactionInProgressError,
    OffsetNotFoundError,
    SegmentAlreadyRecycledError,
    SegmentRecycledError,
)
from .offset_mapper import OffsetMapper
from .segment import LogSegment


@dataclass
class SegmentedLogConfig:
    retention_period: Optional[float] = None
    max_segment_entries: int = 1000
    max_segment_bytes: int = 1024 * 1024


@dataclass
class SegmentedLog:
    config: SegmentedLogConfig = field(default_factory=SegmentedLogConfig)
    segments: Dict[int, LogSegment] = field(default_factory=dict)
    segment_order: List[int] = field(default_factory=list)
    offset_mapper: OffsetMapper = field(default_factory=OffsetMapper)
    compactor: LogCompactor = field(default_factory=LogCompactor)
    next_segment_id: int = 0
    next_logical_offset: int = 0
    active_segment_id: Optional[int] = None

    def _create_new_segment(self) -> LogSegment:
        seg_id = self.next_segment_id
        self.next_segment_id += 1
        segment = LogSegment(
            segment_id=seg_id,
            created_at=time.time(),
            retention_period=self.config.retention_period,
            base_logical_offset=self.next_logical_offset,
            next_logical_offset=self.next_logical_offset,
        )
        self.segments[seg_id] = segment
        self.segment_order.append(seg_id)
        self.offset_mapper.register_segment(seg_id)
        self.active_segment_id = seg_id
        return segment

    def _get_active_segment(self) -> LogSegment:
        if self.active_segment_id is None or self.active_segment_id not in self.segments:
            return self._create_new_segment()
        seg = self.segments[self.active_segment_id]
        if seg.is_recycled:
            return self._create_new_segment()
        if (
            seg.count() >= self.config.max_segment_entries
            or seg.physical_size >= self.config.max_segment_bytes
        ):
            return self._create_new_segment()
        return seg

    def _get_active_segment_for_flush(self, preferred_seg_id: int) -> Optional[LogSegment]:
        if preferred_seg_id in self.segments:
            seg = self.segments[preferred_seg_id]
            if not seg.is_recycled and seg.count() < self.config.max_segment_entries:
                return seg
        return self._get_active_segment()

    def append(self, key: str, value: Any, tombstone: bool = False) -> int:
        if self.compactor.is_compacting:
            placeholder_offset = self.next_logical_offset
            self.next_logical_offset += 1
            entry = LogEntry(
                key=key,
                value=value,
                logical_offset=placeholder_offset,
                physical_offset=0,
                timestamp=time.time(),
                tombstone=tombstone,
            )
            self.compactor.queue_write_during_compaction(self.active_segment_id or 0, entry)
            return placeholder_offset

        segment = self._get_active_segment()
        entry = LogEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            tombstone=tombstone,
        )
        logical_offset = segment.append(entry)
        self.offset_mapper.add_entry(
            segment.segment_id,
            entry.logical_offset,
            entry.physical_offset,
        )
        self.next_logical_offset = max(self.next_logical_offset, logical_offset + 1)
        return logical_offset

    def read(self, logical_offset: int) -> Optional[LogEntry]:
        resolved_offset = self.compactor.pending_offset_map.get(logical_offset, logical_offset)
        try:
            segment_id, physical_offset = self.offset_mapper.resolve_logical(resolved_offset)
        except OffsetNotFoundError:
            return None

        if segment_id == -1:
            return None

        if segment_id not in self.segments:
            return None
        segment = self.segments[segment_id]
        if segment.is_recycled:
            return None

        try:
            entry = segment.read_at(physical_offset)
            return entry
        except SegmentRecycledError:
            return None

    def compact(self) -> CompactionResult:
        all_segments_list = [self.segments[sid] for sid in self.segment_order if sid in self.segments]
        compactable_segments = [
            seg for seg in all_segments_list
            if not seg.is_recycled and not seg.is_marked_for_recycling
        ]
        if not compactable_segments:
            return CompactionResult()

        new_segments, result = self.compactor.compact_segments(
            compactable_segments, self.offset_mapper
        )

        for new_seg in new_segments:
            self.segments[new_seg.segment_id] = new_seg

        pending = self.compactor.flush_pending_writes()
        for seg_id, entry in pending:
            target_seg = self._get_active_segment_for_flush(seg_id)
            if target_seg is not None and not target_seg.is_recycled:
                original_offset = entry.logical_offset
                logical = target_seg.append(entry)
                self.offset_mapper.add_entry(
                    target_seg.segment_id,
                    logical,
                    entry.physical_offset,
                )
                if original_offset != logical:
                    self.compactor.pending_offset_map[original_offset] = logical

        return result

    def collect_expired_segments(self, current_time: Optional[float] = None) -> List[int]:
        if current_time is None:
            current_time = time.time()
        expired_ids: List[int] = []
        for seg_id in list(self.segment_order):
            if seg_id not in self.segments:
                continue
            seg = self.segments[seg_id]
            if seg.is_recycled:
                continue
            if seg.is_expired(current_time):
                seg.mark_for_recycling()
                expired_ids.append(seg_id)
        return expired_ids

    def recycle_marked_segments(self) -> int:
        recycled_count = 0
        for seg_id in list(self.segment_order):
            if seg_id not in self.segments:
                continue
            seg = self.segments[seg_id]
            if seg.is_marked_for_recycling and not seg.is_recycled:
                for entry in list(seg.entries):
                    self.offset_mapper.mark_deleted(seg_id, entry.logical_offset)
                seg.recycle()
                self.offset_mapper.remove_segment(seg_id)
                recycled_count += 1
        return recycled_count

    def force_recycle_segment(self, segment_id: int) -> None:
        if segment_id not in self.segments:
            return
        seg = self.segments[segment_id]
        if seg.is_recycled:
            raise SegmentAlreadyRecycledError(f"Segment {segment_id} has already been recycled")
        for entry in list(seg.entries):
            self.offset_mapper.mark_deleted(segment_id, entry.logical_offset)
        seg.mark_for_recycling()
        seg.recycle()
        self.offset_mapper.remove_segment(segment_id)

    def is_offset_readable(self, logical_offset: int) -> bool:
        entry = self.read(logical_offset)
        return entry is not None

    def total_entries(self) -> int:
        return sum(seg.count() for seg in self.segments.values() if not seg.is_recycled)

    def total_segments(self, include_recycled: bool = False) -> int:
        if include_recycled:
            return len(self.segments)
        return sum(1 for seg in self.segments.values() if not seg.is_recycled)

    def total_size_bytes(self) -> int:
        return sum(seg.physical_size for seg in self.segments.values() if not seg.is_recycled)

    def scan_all(self) -> List[LogEntry]:
        all_entries: List[LogEntry] = []
        for seg_id in self.segment_order:
            if seg_id not in self.segments:
                continue
            seg = self.segments[seg_id]
            if seg.is_recycled:
                continue
            all_entries.extend(seg.read_all())
        return all_entries

    def get_segment(self, segment_id: int) -> Optional[LogSegment]:
        return self.segments.get(segment_id)

    def list_segment_ids(self, include_recycled: bool = False) -> List[int]:
        ids: List[int] = []
        for seg_id in self.segment_order:
            if seg_id not in self.segments:
                continue
            seg = self.segments[seg_id]
            if include_recycled or not seg.is_recycled:
                ids.append(seg_id)
        return ids

    def mark_tombstone(self, key: str) -> int:
        return self.append(key, None, tombstone=True)

    def cleanup(self, current_time: Optional[float] = None) -> Tuple[List[int], int]:
        expired = self.collect_expired_segments(current_time)
        recycled = self.recycle_marked_segments()
        return (expired, recycled)
