from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .exceptions import TransactionStateError


class TransactionStatus(str, Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ABORTED = "aborted"


@dataclass
class Version:
    key: str
    value: Any
    version: int
    transaction_id: int
    is_tombstone: bool = False

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("version must be positive")
        if self.transaction_id <= 0:
            raise ValueError("transaction_id must be positive")


@dataclass
class Snapshot:
    snapshot_id: int
    snapshot_version: int
    active_transactions: Tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.snapshot_id <= 0:
            raise ValueError("snapshot_id must be positive")
        if self.snapshot_version < 0:
            raise ValueError("snapshot_version cannot be negative")

    def is_visible(self, version: Version) -> bool:
        if self.snapshot_version == 0:
            return False
        if version.transaction_id in self.active_transactions:
            return False
        return version.version <= self.snapshot_version


@dataclass
class Transaction:
    transaction_id: int
    start_version: int
    status: TransactionStatus = TransactionStatus.ACTIVE
    writes: Dict[str, Any] = field(default_factory=dict)
    commit_version: Optional[int] = None

    def __post_init__(self) -> None:
        if self.transaction_id <= 0:
            raise ValueError("transaction_id must be positive")
        if self.start_version < 0:
            raise ValueError("start_version cannot be negative")

    @property
    def is_active(self) -> bool:
        return self.status == TransactionStatus.ACTIVE

    @property
    def is_committed(self) -> bool:
        return self.status == TransactionStatus.COMMITTED

    @property
    def is_aborted(self) -> bool:
        return self.status == TransactionStatus.ABORTED

    def mark_committed(self, commit_version: int) -> None:
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot commit transaction in state {self.status}"
            )
        if commit_version <= 0:
            raise ValueError("commit_version must be positive")
        self.status = TransactionStatus.COMMITTED
        self.commit_version = commit_version

    def mark_aborted(self) -> None:
        if not self.is_active:
            raise TransactionStateError(
                f"Cannot abort transaction in state {self.status}"
            )
        self.status = TransactionStatus.ABORTED
