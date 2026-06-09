from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ItemStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PipelineStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


StageHandler = Callable[[Any], Any]


@dataclass
class PipelineItem:
    item_id: str
    data: Any
    status: ItemStatus = ItemStatus.PENDING
    error: Optional[Exception] = None
    attempts: int = 0
    stage_results: Dict[str, Any] = field(default_factory=dict)

    def mark_processing(self) -> None:
        self.status = ItemStatus.PROCESSING

    def mark_success(self, stage_name: str, result: Any) -> None:
        self.status = ItemStatus.SUCCESS
        self.stage_results[stage_name] = result

    def mark_retrying(self) -> None:
        self.status = ItemStatus.RETRYING
        self.attempts += 1

    def mark_failed(self, stage_name: str, error: Exception) -> None:
        self.status = ItemStatus.FAILED
        self.stage_results[stage_name] = error
        self.error = error

    def mark_cancelled(self) -> None:
        self.status = ItemStatus.CANCELLED


@dataclass
class StageConfig:
    name: str
    handler: StageHandler
    max_retries: int = 0
    retry_delay: float = 0.0
    queue_capacity: int = 100

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be >= 0")
        if self.queue_capacity <= 0:
            raise ValueError("queue_capacity must be > 0")


@dataclass
class StageResult:
    stage_name: str
    status: StageStatus
    processed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    duration: float = 0.0

    @property
    def total_count(self) -> int:
        return self.success_count + self.failed_count + self.cancelled_count


@dataclass
class PipelineResult:
    status: PipelineStatus
    items: List[PipelineItem]
    stage_results: List[StageResult]
    total_duration: float = 0.0
    error: Optional[Exception] = None

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.status == ItemStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == ItemStatus.FAILED)

    @property
    def cancelled_count(self) -> int:
        return sum(1 for item in self.items if item.status == ItemStatus.CANCELLED)

    @property
    def success_items(self) -> List[PipelineItem]:
        return [item for item in self.items if item.status == ItemStatus.SUCCESS]

    @property
    def failed_items(self) -> List[PipelineItem]:
        return [item for item in self.items if item.status == ItemStatus.FAILED]

    @property
    def cancelled_items(self) -> List[PipelineItem]:
        return [item for item in self.items if item.status == ItemStatus.CANCELLED]
