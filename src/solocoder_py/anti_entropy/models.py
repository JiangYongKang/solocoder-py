from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set


class EntryStatus(str, Enum):
    IDENTICAL = "identical"
    ONLY_IN_A = "only_in_a"
    ONLY_IN_B = "only_in_b"
    VERSION_MISMATCH = "version_mismatch"
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


@dataclass
class DiffResult:
    only_in_a: Dict[str, VersionedEntry] = field(default_factory=dict)
    only_in_b: Dict[str, VersionedEntry] = field(default_factory=dict)
    version_mismatch: Dict[str, DiffEntry] = field(default_factory=dict)
    conflicts: Dict[str, DiffEntry] = field(default_factory=dict)
    identical: Set[str] = field(default_factory=set)

    @property
    def has_differences(self) -> bool:
        return bool(
            self.only_in_a or self.only_in_b or self.version_mismatch or self.conflicts
        )

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    @property
    def diff_count(self) -> int:
        return (
            len(self.only_in_a)
            + len(self.only_in_b)
            + len(self.version_mismatch)
            + len(self.conflicts)
        )


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
