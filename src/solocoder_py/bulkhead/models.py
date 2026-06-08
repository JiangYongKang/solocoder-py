from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from .exceptions import InvalidConfigError


class FullStrategy(str, Enum):
    REJECT = "REJECT"
    QUEUE = "QUEUE"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    QUEUE_TIMEOUT = "QUEUE_TIMEOUT"


@dataclass
class GroupConfig:
    name: str
    max_concurrency: int
    full_strategy: FullStrategy = FullStrategy.QUEUE
    queue_timeout: float = 0.0
    max_queue_size: int = 0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.name:
            raise InvalidConfigError("group name must not be empty")
        if self.max_concurrency <= 0:
            raise InvalidConfigError("max_concurrency must be positive")
        if self.full_strategy == FullStrategy.QUEUE and self.queue_timeout < 0:
            raise InvalidConfigError("queue_timeout must be non-negative")
        if self.max_queue_size < 0:
            raise InvalidConfigError("max_queue_size must be non-negative")


@dataclass
class GroupStats:
    name: str
    max_concurrency: int
    current_concurrency: int
    queue_size: int
    success_count: int
    failure_count: int
    full_strategy: FullStrategy
    queue_timeout: float
    max_queue_size: int


@dataclass
class TaskResult:
    task_id: str
    group_name: str
    status: TaskStatus
    result: Any = None
    exception: Optional[BaseException] = None
    execution_time: float = 0.0
    queue_wait_time: float = 0.0


@dataclass
class _TaskWrapper:
    task_id: str
    func: Callable[..., Any]
    args: tuple
    kwargs: dict
    submitted_at: float
    timeout_deadline: Optional[float] = None
    result: Optional[TaskResult] = None
