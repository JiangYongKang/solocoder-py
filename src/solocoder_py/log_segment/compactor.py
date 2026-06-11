from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .entry import LogEntry
from .exceptions import CompactionInProgressError
from .offset_mapper import OffsetMapper
from .segment import LogSegment


@dataclass
class CompactionResult:
    segments_compacted: int = 0
    entries_removed: int = 0
    entries_retained: int = 0
    space_saved_bytes: int = 0
    offset_mapping_changes: Dict[int, int] = field(default_factory=dict)


@dataclass
class LogCompactor:
    is_compacting: bool = False
    pending_writes: List[Tuple[int, LogEntry]] = field(default_factory=list)

    def compact_segments(
        self,
        segments: List[LogSegment],
        offset_mapper: OffsetMapper,
    ) -> Tuple[List[LogSegment], CompactionResult]:
        if self.is_compacting:
            raise CompactionInProgressError("Compaction already in progress")
        self.is_compacting = True
        try:
            all_entries: List[Tuple[int, LogEntry]] = []
            original_sizes: Dict[int, int] = {}

            for seg in segments:
                if seg.is_recycled:
                    continue
                original_sizes[seg.segment_id] = seg.physical_size
                for entry in seg.read_all():
                    all_entries.append((seg.segment_id, entry))

            latest_entries: Dict[str, Tuple[int, LogEntry]] = {}
            for seg_id, entry in all_entries:
                if entry.tombstone:
                    if entry.key in latest_entries:
                        del latest_entries[entry.key]
                else:
                    latest_entries[entry.key] = (seg_id, entry)

            retained_by_segment: Dict[int, List[LogEntry]] = {}
            removed_count = 0
            retained_logical_offsets: Set[int] = set()
            removed_logical_offsets: Set[int] = set()

            for seg_id, entry in all_entries:
                if seg_id not in retained_by_segment:
                    retained_by_segment[seg_id] = []
                latest = latest_entries.get(entry.key)
                if latest is not None and latest[1].logical_offset == entry.logical_offset:
                    retained_by_segment[seg_id].append(entry)
                    retained_logical_offsets.add(entry.logical_offset)
                else:
                    removed_count += 1
                    removed_logical_offsets.add(entry.logical_offset)

            new_segments: List[LogSegment] = []
            offset_mapping_changes: Dict[int, int] = {}
            new_entries_retained = 0
            total_space_saved = 0

            for seg in segments:
                if seg.is_recycled:
                    new_segments.append(seg)
                    continue
                retained = retained_by_segment.get(seg.segment_id, [])
                original_size = original_sizes.get(seg.segment_id, 0)
                new_seg = seg.compacted_copy(retained)
                for idx, new_entry in enumerate(retained):
                    if idx < len(new_seg.entries):
                        old_physical = new_seg.entries[idx].physical_offset
                        logical_off = new_entry.logical_offset
                        offset_mapper.segment_mappings[seg.segment_id].logical_to_physical[logical_off] = old_physical
                        offset_mapper.global_mapping.logical_to_physical[logical_off] = old_physical
                        offset_mapping_changes[logical_off] = old_physical
                new_entries_retained += len(retained)
                total_space_saved += (original_size - new_seg.physical_size)
                new_segments.append(new_seg)

            for logical_off in removed_logical_offsets:
                    for seg in segments:
                        if seg.segment_id in offset_mapper.segment_mappings:
                            mapping = offset_mapper.segment_mappings[seg.segment_id]
                            if logical_off in mapping.logical_to_physical:
                                mapping.mark_deleted(logical_off)
                    offset_mapper.global_mapping.mark_deleted(logical_off)

            offset_mapper.save_compaction_snapshot()

            result = CompactionResult(
                segments_compacted=len(segments),
                entries_removed=removed_count,
                entries_retained=new_entries_retained,
                space_saved_bytes=total_space_saved,
                offset_mapping_changes=offset_mapping_changes,
            )
            return (new_segments, result)
        finally:
            self.is_compacting = False

    def queue_write_during_compaction(self, segment_id: int, entry: LogEntry) -> None:
        self.pending_writes.append((segment_id, entry))

    def flush_pending_writes(self) -> List[Tuple[int, LogEntry]]:
        pending = self.pending_writes
        self.pending_writes = []
        return pending
