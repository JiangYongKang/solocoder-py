from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .exceptions import OffsetNotFoundError


@dataclass
class OffsetMapping:
    logical_to_physical: Dict[int, int] = field(default_factory=dict)
    physical_to_logical: Dict[int, int] = field(default_factory=dict)
    deleted_offsets: set = field(default_factory=set)

    def add_mapping(self, logical_offset: int, physical_offset: int) -> None:
        self.logical_to_physical[logical_offset] = physical_offset
        self.physical_to_logical[physical_offset] = logical_offset

    def mark_deleted(self, logical_offset: int) -> None:
        self.deleted_offsets.add(logical_offset)
        if logical_offset in self.logical_to_physical:
            physical = self.logical_to_physical.pop(logical_offset)
            self.physical_to_logical.pop(physical, None)

    def is_deleted(self, logical_offset: int) -> bool:
        return logical_offset in self.deleted_offsets

    def get_physical(self, logical_offset: int) -> int:
        if logical_offset in self.deleted_offsets:
            raise OffsetNotFoundError(f"Logical offset {logical_offset} was deleted during compaction")
        if logical_offset not in self.logical_to_physical:
            raise OffsetNotFoundError(f"Logical offset {logical_offset} not found")
        return self.logical_to_physical[logical_offset]

    def get_logical(self, physical_offset: int) -> int:
        if physical_offset not in self.physical_to_logical:
            raise OffsetNotFoundError(f"Physical offset {physical_offset} not found")
        return self.physical_to_logical[physical_offset]

    def clear(self) -> None:
        self.logical_to_physical.clear()
        self.physical_to_logical.clear()
        self.deleted_offsets.clear()

    def snapshot(self) -> OffsetMapping:
        return OffsetMapping(
            logical_to_physical=dict(self.logical_to_physical),
            physical_to_logical=dict(self.physical_to_logical),
            deleted_offsets=set(self.deleted_offsets),
        )


@dataclass
class OffsetMapper:
    global_mapping: OffsetMapping = field(default_factory=OffsetMapping)
    segment_mappings: Dict[int, OffsetMapping] = field(default_factory=dict)
    compaction_snapshots: List[OffsetMapping] = field(default_factory=list)

    def register_segment(self, segment_id: int) -> None:
        if segment_id not in self.segment_mappings:
            self.segment_mappings[segment_id] = OffsetMapping()

    def remove_segment(self, segment_id: int) -> None:
        if segment_id in self.segment_mappings:
            del self.segment_mappings[segment_id]

    def add_entry(self, segment_id: int, logical_offset: int, physical_offset: int) -> None:
        if segment_id not in self.segment_mappings:
            self.register_segment(segment_id)
        self.segment_mappings[segment_id].add_mapping(logical_offset, physical_offset)
        self.global_mapping.add_mapping(logical_offset, physical_offset)

    def mark_deleted(self, segment_id: int, logical_offset: int) -> None:
        if segment_id in self.segment_mappings:
            self.segment_mappings[segment_id].mark_deleted(logical_offset)
        self.global_mapping.mark_deleted(logical_offset)

    def get_physical(self, logical_offset: int, segment_id: Optional[int] = None) -> int:
        if segment_id is not None and segment_id in self.segment_mappings:
            return self.segment_mappings[segment_id].get_physical(logical_offset)
        return self.global_mapping.get_physical(logical_offset)

    def resolve_logical(self, logical_offset: int) -> Tuple[int, int]:
        physical_offset = self.global_mapping.get_physical(logical_offset)
        for seg_id, mapping in self.segment_mappings.items():
            if logical_offset in mapping.logical_to_physical:
                return (seg_id, physical_offset)
        return (-1, physical_offset)

    def save_compaction_snapshot(self) -> None:
        self.compaction_snapshots.append(self.global_mapping.snapshot())

    def clear(self) -> None:
        self.global_mapping.clear()
        self.segment_mappings.clear()
        self.compaction_snapshots.clear()
