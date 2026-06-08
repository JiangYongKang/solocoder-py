from __future__ import annotations

import threading
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .exceptions import (
    KeyNotFoundError,
    SnapshotInvalidError,
    TransactionStateError,
    VersionNotFoundError,
    VersionReclaimedError,
    WriteWriteConflictError,
)
from .models import (
    Snapshot,
    Transaction,
    TransactionStatus,
    Version,
)


@dataclass
class MVCCStore:
    _data: Dict[str, List[Version]] = field(default_factory=dict)
    _transactions: Dict[int, Transaction] = field(default_factory=dict)
    _active_snapshots: Dict[int, Snapshot] = field(default_factory=dict)
    _next_version: int = 1
    _committed_version: int = 0
    _next_transaction_id: int = 1
    _next_snapshot_id: int = 1
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _reclaimed_versions: Set[int] = field(default_factory=set)

    def _allocate_version(self) -> int:
        version = self._next_version
        self._next_version += 1
        return version

    def _allocate_transaction_id(self) -> int:
        tid = self._next_transaction_id
        self._next_transaction_id += 1
        return tid

    def _allocate_snapshot_id(self) -> int:
        sid = self._next_snapshot_id
        self._next_snapshot_id += 1
        return sid

    def _get_active_transaction_ids(self) -> Set[int]:
        return {
            tid
            for tid, txn in self._transactions.items()
            if txn.is_active
        }

    def begin_transaction(self) -> Transaction:
        with self._lock:
            txn_id = self._allocate_transaction_id()
            start_version = self._committed_version
            txn = Transaction(
                transaction_id=txn_id,
                start_version=start_version,
            )
            self._transactions[txn_id] = txn
            return txn

    def create_snapshot(self) -> Snapshot:
        with self._lock:
            snapshot_id = self._allocate_snapshot_id()
            snapshot_version = self._committed_version
            active = tuple(sorted(self._get_active_transaction_ids()))
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                snapshot_version=snapshot_version,
                active_transactions=active,
            )
            self._active_snapshots[snapshot_id] = snapshot
            return snapshot

    def release_snapshot(self, snapshot: Snapshot) -> None:
        with self._lock:
            self._active_snapshots.pop(snapshot.snapshot_id, None)

    def _get_min_snapshot_version(self) -> Optional[int]:
        if not self._active_snapshots:
            return None
        return min(s.snapshot_version for s in self._active_snapshots.values())

    def read(self, key: str, snapshot: Optional[Snapshot] = None) -> Any:
        with self._lock:
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found")

            versions = self._data[key]

            if snapshot is None:
                for version in reversed(versions):
                    if version.version in self._reclaimed_versions:
                        continue
                    txn = self._transactions.get(version.transaction_id)
                    if txn is not None and not txn.is_committed:
                        continue
                    if version.is_tombstone:
                        raise KeyNotFoundError(f"Key '{key}' not found")
                    return version.value
                raise KeyNotFoundError(f"Key '{key}' not found")

            if snapshot.snapshot_version in self._reclaimed_versions:
                raise VersionReclaimedError(
                    f"Snapshot version {snapshot.snapshot_version} has been reclaimed"
                )
            if snapshot.snapshot_version > self._committed_version:
                raise SnapshotInvalidError(
                    f"Snapshot version {snapshot.snapshot_version} is invalid"
                )

            for version in reversed(versions):
                if version.version > snapshot.snapshot_version:
                    continue
                if version.version in self._reclaimed_versions:
                    raise VersionReclaimedError(
                        f"Version {version.version} for key '{key}' has been reclaimed"
                    )
                if not snapshot.is_visible(version):
                    continue
                if version.is_tombstone:
                    raise KeyNotFoundError(f"Key '{key}' not found")
                return version.value

            raise KeyNotFoundError(f"Key '{key}' not found")

    def read_version(self, key: str, version: int) -> Any:
        with self._lock:
            if version in self._reclaimed_versions:
                raise VersionReclaimedError(
                    f"Version {version} for key '{key}' has been reclaimed"
                )
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found")

            versions = self._data[key]
            version_numbers = [v.version for v in versions]
            idx = bisect_right(version_numbers, version) - 1

            if idx < 0:
                raise VersionNotFoundError(
                    f"Version {version} not found for key '{key}'"
                )

            found = versions[idx]
            if found.version != version:
                raise VersionNotFoundError(
                    f"Version {version} not found for key '{key}'"
                )

            txn = self._transactions.get(found.transaction_id)
            if txn is not None and not txn.is_committed:
                raise VersionNotFoundError(
                    f"Version {version} for key '{key}' belongs to an uncommitted transaction"
                )

            if found.is_tombstone:
                raise KeyNotFoundError(f"Key '{key}' not found at version {version}")

            return found.value

    def write(self, transaction: Transaction, key: str, value: Any) -> None:
        with self._lock:
            if not transaction.is_active:
                raise TransactionStateError(
                    f"Cannot write: transaction is {transaction.status}"
                )
            if transaction.transaction_id not in self._transactions:
                raise TransactionStateError("Transaction not found in store")

            transaction.writes[key] = value

    def delete(self, transaction: Transaction, key: str) -> None:
        with self._lock:
            if not transaction.is_active:
                raise TransactionStateError(
                    f"Cannot delete: transaction is {transaction.status}"
                )
            if transaction.transaction_id not in self._transactions:
                raise TransactionStateError("Transaction not found in store")

            transaction.writes[key] = _TOMBSTONE

    def _check_write_conflicts(self, transaction: Transaction) -> None:
        for key in transaction.writes:
            if key not in self._data:
                continue
            versions = self._data[key]
            for version in reversed(versions):
                if version.transaction_id == transaction.transaction_id:
                    continue
                txn = self._transactions.get(version.transaction_id)
                if txn is not None and not txn.is_committed:
                    continue
                if version.version in self._reclaimed_versions:
                    continue
                if version.version > transaction.start_version:
                    raise WriteWriteConflictError(
                        f"Write-Write conflict on key '{key}': "
                        f"start_version={transaction.start_version}, "
                        f"latest_committed_version={version.version}"
                    )
                break

    def commit(self, transaction: Transaction) -> int:
        with self._lock:
            if not transaction.is_active:
                raise TransactionStateError(
                    f"Cannot commit: transaction is {transaction.status}"
                )
            if transaction.transaction_id not in self._transactions:
                raise TransactionStateError("Transaction not found in store")

            self._check_write_conflicts(transaction)

            commit_version = self._allocate_version()
            transaction.mark_committed(commit_version)

            for key, value in transaction.writes.items():
                is_tombstone = value is _TOMBSTONE
                actual_value = None if is_tombstone else value
                version = Version(
                    key=key,
                    value=actual_value,
                    version=commit_version,
                    transaction_id=transaction.transaction_id,
                    is_tombstone=is_tombstone,
                )
                if key not in self._data:
                    self._data[key] = []
                self._data[key].append(version)

            if commit_version > self._committed_version:
                self._committed_version = commit_version

            return commit_version

    def rollback(self, transaction: Transaction) -> None:
        with self._lock:
            if not transaction.is_active:
                raise TransactionStateError(
                    f"Cannot rollback: transaction is {transaction.status}"
                )
            if transaction.transaction_id not in self._transactions:
                raise TransactionStateError("Transaction not found in store")

            transaction.mark_aborted()
            transaction.writes.clear()

    def get_versions(self, key: str) -> List[Version]:
        with self._lock:
            if key not in self._data:
                raise KeyNotFoundError(f"Key '{key}' not found")
            return [
                Version(
                    key=v.key,
                    value=v.value,
                    version=v.version,
                    transaction_id=v.transaction_id,
                    is_tombstone=v.is_tombstone,
                )
                for v in self._data[key]
                if v.version not in self._reclaimed_versions
            ]

    def collect_garbage(self) -> int:
        with self._lock:
            min_snapshot = self._get_min_snapshot_version()
            active_txns = self._get_active_transaction_ids()
            min_txn_start = None
            for tid in active_txns:
                txn = self._transactions[tid]
                if min_txn_start is None or txn.start_version < min_txn_start:
                    min_txn_start = txn.start_version

            safe_version = None
            if min_snapshot is not None and min_txn_start is not None:
                safe_version = min(min_snapshot, min_txn_start)
            elif min_snapshot is not None:
                safe_version = min_snapshot
            elif min_txn_start is not None:
                safe_version = min_txn_start
            else:
                safe_version = self._committed_version + 1

            reclaimed_count = 0

            for key in list(self._data.keys()):
                versions = self._data[key]
                kept = []
                for v in versions:
                    if v.version < safe_version:
                        if not v.is_tombstone:
                            is_latest_before_safe = True
                            for other in versions:
                                if (
                                    other.version > v.version
                                    and other.version < safe_version
                                    and not other.is_tombstone
                                ):
                                    is_latest_before_safe = False
                                    break
                            if is_latest_before_safe:
                                kept.append(v)
                            else:
                                self._reclaimed_versions.add(v.version)
                                reclaimed_count += 1
                        else:
                            has_older_version = any(
                                ov.version < v.version for ov in versions
                            )
                            if not has_older_version:
                                kept.append(v)
                            else:
                                self._reclaimed_versions.add(v.version)
                                reclaimed_count += 1
                    else:
                        kept.append(v)

                self._data[key] = kept
                if not kept:
                    del self._data[key]

            return reclaimed_count

    def transaction_read(self, transaction: Transaction, key: str) -> Any:
        with self._lock:
            if not transaction.is_active:
                raise TransactionStateError(
                    f"Cannot read: transaction is {transaction.status}"
                )
            if transaction.transaction_id not in self._transactions:
                raise TransactionStateError("Transaction not found in store")

            if key in transaction.writes:
                value = transaction.writes[key]
                if value is _TOMBSTONE:
                    raise KeyNotFoundError(f"Key '{key}' not found")
                return value

            snapshot = Snapshot(
                snapshot_id=self._allocate_snapshot_id(),
                snapshot_version=transaction.start_version,
                active_transactions=tuple(sorted(self._get_active_transaction_ids())),
            )
            return self.read(key, snapshot)

    def count_active_transactions(self) -> int:
        with self._lock:
            return len(self._get_active_transaction_ids())

    def count_active_snapshots(self) -> int:
        with self._lock:
            return len(self._active_snapshots)

    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        with self._lock:
            return self._transactions.get(transaction_id)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._transactions.clear()
            self._active_snapshots.clear()
            self._reclaimed_versions.clear()
            self._next_version = 1
            self._committed_version = 0
            self._next_transaction_id = 1
            self._next_snapshot_id = 1


class _Tombstone:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<TOMBSTONE>"


_TOMBSTONE = _Tombstone()
