from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set


class EntryStatus(str, Enum):
    IDENTICAL = "identical"
    ONLY_IN_A = "only_in_a"
    ONLY_IN_B = "only_in_b"
    A_HAS_NEWER = "a_has_newer"
    B_HAS_NEWER = "b_has_newer"
    CONFLICT = "conflict"


@dataclass
class VersionedEntry:
    key: str
    value: Any
    version: int

    def __post_init__(self) -> None:
        if self.version < 0:
            raise ValueError("version must be non-negative")


@dataclass
class DiffEntry:
    key: str
    status: EntryStatus
    entry_a: Optional[VersionedEntry] = None
    entry_b: Optional[VersionedEntry] = None

    @property
    def newer_entry(self) -> Optional[VersionedEntry]:
        if self.status == EntryStatus.A_HAS_NEWER:
            return self.entry_a
        if self.status == EntryStatus.B_HAS_NEWER:
            return self.entry_b
        return None

    @property
    def older_entry(self) -> Optional[VersionedEntry]:
        if self.status == EntryStatus.A_HAS_NEWER:
            return self.entry_b
        if self.status == EntryStatus.B_HAS_NEWER:
            return self.entry_a
        return None


@dataclass
class DiffResult:
    only_in_a: Dict[str, VersionedEntry] = field(default_factory=dict)
    only_in_b: Dict[str, VersionedEntry] = field(default_factory=dict)
    a_has_newer: Dict[str, DiffEntry] = field(default_factory=dict)
    b_has_newer: Dict[str, DiffEntry] = field(default_factory=dict)
    conflicts: Dict[str, DiffEntry] = field(default_factory=dict)
    identical: Set[str] = field(default_factory=set)

    @property
    def has_differences(self) -> bool:
        return bool(
            self.only_in_a
            or self.only_in_b
            or self.a_has_newer
            or self.b_has_newer
            or self.conflicts
        )

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def diff_count(self) -> int:
        return (
            len(self.only_in_a)
            + len(self.only_in_b)
            + len(self.a_has_newer)
            + len(self.b_has_newer)
            + len(self.conflicts)
        )

    @property
    def version_mismatch_count(self) -> int:
        return len(self.a_has_newer) + len(self.b_has_newer)


@dataclass
class SyncResult:
    synced_keys: Set[str] = field(default_factory=set)
    conflict_keys: Set[str] = field(default_factory=set)
    a_to_b_count: int = 0
    b_to_a_count: int = 0

    @property
    def total_synced(self) -> int:
        return self.a_to_b_count + self.b_to_a_count

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflict_keys)


@dataclass
class ConflictEntry:
    key: str
    entry_a: VersionedEntry
    entry_b: VersionedEntry
    resolved: bool = False
    winner: Optional[str] = None
