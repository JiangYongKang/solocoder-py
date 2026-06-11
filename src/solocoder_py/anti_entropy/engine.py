from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from .exceptions import SyncError
from .models import (
    ConflictEntry,
    DiffEntry,
    DiffResult,
    EntryStatus,
    SyncResult,
    VersionedEntry,
)
from .replica import Replica


@dataclass
class AntiEntropyEngine:
    replica_a: Replica
    replica_b: Replica
    _conflicts: Dict[str, ConflictEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.replica_a is None or self.replica_b is None:
            raise SyncError("Both replicas must be provided")
        if self.replica_a.replica_id == self.replica_b.replica_id:
            raise SyncError("Replica IDs must be different")

    def diff(self) -> DiffResult:
        result = DiffResult()
        entries_a = self.replica_a.to_dict()
        entries_b = self.replica_b.to_dict()

        all_keys = set(entries_a.keys()) | set(entries_b.keys())

        for key in all_keys:
            in_a = key in entries_a
            in_b = key in entries_b

            if in_a and not in_b:
                result.only_in_a[key] = entries_a[key]
            elif not in_a and in_b:
                result.only_in_b[key] = entries_b[key]
            else:
                entry_a = entries_a[key]
                entry_b = entries_b[key]

                if entry_a.version == entry_b.version:
                    if entry_a.value == entry_b.value:
                        result.identical.add(key)
                    else:
                        diff_entry = DiffEntry(
                            key=key,
                            status=EntryStatus.CONFLICT,
                            entry_a=entry_a,
                            entry_b=entry_b,
                        )
                        result.conflicts[key] = diff_entry
                elif entry_a.version > entry_b.version:
                    diff_entry = DiffEntry(
                        key=key,
                        status=EntryStatus.A_HAS_NEWER,
                        entry_a=entry_a,
                        entry_b=entry_b,
                    )
                    result.a_has_newer[key] = diff_entry
                else:
                    diff_entry = DiffEntry(
                        key=key,
                        status=EntryStatus.B_HAS_NEWER,
                        entry_a=entry_a,
                        entry_b=entry_b,
                    )
                    result.b_has_newer[key] = diff_entry

        return result

    def sync_a_to_b(self) -> SyncResult:
        diff_result = self.diff()
        sync_result = SyncResult()

        for key, entry in diff_result.only_in_a.items():
            if self.replica_b.merge_entry(entry):
                sync_result.synced_keys.add(key)
                sync_result.a_to_b_count += 1

        for key, diff_entry in diff_result.a_has_newer.items():
            if diff_entry.entry_a is not None:
                if self.replica_b.merge_entry(diff_entry.entry_a):
                    sync_result.synced_keys.add(key)
                    sync_result.a_to_b_count += 1

        for key, diff_entry in diff_result.conflicts.items():
            if diff_entry.entry_a is not None and diff_entry.entry_b is not None:
                self._conflicts[key] = ConflictEntry(
                    key=key,
                    entry_a=diff_entry.entry_a,
                    entry_b=diff_entry.entry_b,
                )
                sync_result.conflict_keys.add(key)

        return sync_result

    def sync_b_to_a(self) -> SyncResult:
        diff_result = self.diff()
        sync_result = SyncResult()

        for key, entry in diff_result.only_in_b.items():
            if self.replica_a.merge_entry(entry):
                sync_result.synced_keys.add(key)
                sync_result.b_to_a_count += 1

        for key, diff_entry in diff_result.b_has_newer.items():
            if diff_entry.entry_b is not None:
                if self.replica_a.merge_entry(diff_entry.entry_b):
                    sync_result.synced_keys.add(key)
                    sync_result.b_to_a_count += 1

        for key, diff_entry in diff_result.conflicts.items():
            if diff_entry.entry_a is not None and diff_entry.entry_b is not None:
                self._conflicts[key] = ConflictEntry(
                    key=key,
                    entry_a=diff_entry.entry_a,
                    entry_b=diff_entry.entry_b,
                )
                sync_result.conflict_keys.add(key)

        return sync_result

    def sync_bidirectional(self) -> SyncResult:
        diff_result = self.diff()
        sync_result = SyncResult()

        for key, entry in diff_result.only_in_a.items():
            if self.replica_b.merge_entry(entry):
                sync_result.synced_keys.add(key)
                sync_result.a_to_b_count += 1

        for key, entry in diff_result.only_in_b.items():
            if self.replica_a.merge_entry(entry):
                sync_result.synced_keys.add(key)
                sync_result.b_to_a_count += 1

        for key, diff_entry in diff_result.a_has_newer.items():
            if diff_entry.entry_a is not None:
                if self.replica_b.merge_entry(diff_entry.entry_a):
                    sync_result.synced_keys.add(key)
                    sync_result.a_to_b_count += 1

        for key, diff_entry in diff_result.b_has_newer.items():
            if diff_entry.entry_b is not None:
                if self.replica_a.merge_entry(diff_entry.entry_b):
                    sync_result.synced_keys.add(key)
                    sync_result.b_to_a_count += 1

        for key, diff_entry in diff_result.conflicts.items():
            if diff_entry.entry_a is not None and diff_entry.entry_b is not None:
                self._conflicts[key] = ConflictEntry(
                    key=key,
                    entry_a=diff_entry.entry_a,
                    entry_b=diff_entry.entry_b,
                )
                sync_result.conflict_keys.add(key)

        return sync_result

    def get_conflicts(self) -> Dict[str, ConflictEntry]:
        return dict(self._conflicts)

    def resolve_conflict(self, key: str, winner: str) -> bool:
        if key not in self._conflicts:
            return False

        conflict = self._conflicts[key]
        if winner == "a":
            self.replica_b.force_merge_entry(conflict.entry_a)
            conflict.resolved = True
            conflict.winner = "a"
            del self._conflicts[key]
            return True
        elif winner == "b":
            self.replica_a.force_merge_entry(conflict.entry_b)
            conflict.resolved = True
            conflict.winner = "b"
            del self._conflicts[key]
            return True
        else:
            raise ValueError("winner must be 'a' or 'b'")

    def is_consistent(self) -> bool:
        diff_result = self.diff()
        return not diff_result.has_differences

    def clear_conflicts(self) -> None:
        self._conflicts.clear()
