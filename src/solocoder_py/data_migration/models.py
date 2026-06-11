from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BatchStatus(str, Enum):
    PENDING = "pending"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationStatus(str, Enum):
    IDLE = "idle"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class BatchInfo:
    batch_index: int
    start_index: int
    end_index: int
    status: BatchStatus = BatchStatus.PENDING
    record_count: int = 0
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.batch_index < 0:
            raise ValueError("batch_index must be non-negative")
        if self.start_index < 0:
            raise ValueError("start_index must be non-negative")
        if self.end_index < self.start_index:
            raise ValueError("end_index must be >= start_index")
        self.record_count = self.end_index - self.start_index


@dataclass
class MigrationState:
    status: MigrationStatus = MigrationStatus.IDLE
    total_records: int = 0
    batch_size: int = 0
    total_batches: int = 0
    completed_batches: int = 0
    failed_batch_index: Optional[int] = None
    error_message: Optional[str] = None
    batches: List[BatchInfo] = field(default_factory=list)
    checkpoint: int = -1

    @property
    def is_completed(self) -> bool:
        return self.status == MigrationStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == MigrationStatus.FAILED

    @property
    def is_rolled_back(self) -> bool:
        return self.status == MigrationStatus.ROLLED_BACK

    @property
    def progress_percent(self) -> float:
        if self.total_batches == 0:
            return 0.0
        return (self.completed_batches / self.total_batches) * 100.0

    def get_batch(self, batch_index: int) -> Optional[BatchInfo]:
        if 0 <= batch_index < len(self.batches):
            return self.batches[batch_index]
        return None
