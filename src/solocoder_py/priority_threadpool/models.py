from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

from .exceptions import InvalidConfigError


class Priority(int, Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ThreadPoolState(str, Enum):
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    TERMINATED = "TERMINATED"


@dataclass
class ThreadPoolConfig:
    max_concurrency: int
    aging_threshold: float = 10.0
    aging_check_interval: float = 1.0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.max_concurrency <= 0:
            raise InvalidConfigError("max_concurrency must be positive")
        if self.aging_threshold < 0:
            raise InvalidConfigError("aging_threshold must be non-negative")
        if self.aging_check_interval <= 0:
            raise InvalidConfigError("aging_check_interval must be positive")


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    priority: Priority
    result: Any = None
    exception: Optional[BaseException] = None
    submitted_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    original_priority: Priority = Priority.LOW
    priority_boost_count: int = 0


@dataclass
class ThreadPoolStats:
    state: ThreadPoolState
    max_concurrency: int
    current_concurrency: int
    high_queue_size: int
    medium_queue_size: int
    low_queue_size: int
    total_submitted: int
    total_completed: int
    total_failed: int


@dataclass
class _TaskWrapper:
    task_id: str
    func: Callable[..., Any]
    args: tuple
    kwargs: dict
    priority: Priority
    submitted_at: float
    original_priority: Priority = field(init=False)
    priority_boost_count: int = 0

    def __post_init__(self) -> None:
        self.original_priority = self.priority

    @classmethod
    def create(
        cls,
        func: Callable[..., Any],
        priority: Priority,
        submitted_at: float,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        task_id: Optional[str] = None,
    ) -> "_TaskWrapper":
        if task_id is None:
            task_id = uuid4().hex
        if kwargs is None:
            kwargs = {}
        return cls(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            submitted_at=submitted_at,
        )
