from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, List, Optional


class DAGError(Exception):
    pass


class TaskAlreadyRegisteredError(DAGError):
    pass


class TaskNotFoundError(DAGError):
    pass


class DependencyNotFoundError(DAGError):
    pass


class CycleDetectedError(DAGError):
    pass


class TaskNotReadyError(DAGError):
    pass


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


TaskAction = Callable[["TaskExecutionContext"], Any]


@dataclass
class TaskExecutionContext:
    task_id: str
    result: Any = None
    error: Optional[Exception] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Task:
    task_id: str
    dependencies: List[str] = field(default_factory=list)
    action: Optional[TaskAction] = None
    name: Optional[str] = None

    status: TaskStatus = field(default=TaskStatus.PENDING, init=False)
    result: Any = field(default=None, init=False)
    error: Optional[Exception] = field(default=None, init=False)
    started_at: Optional[datetime] = field(default=None, init=False)
    completed_at: Optional[datetime] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.task_id:
            raise DAGError("task_id cannot be empty")
        self.dependencies = list(dict.fromkeys(self.dependencies))

    def is_terminal(self) -> bool:
        return self.status in (
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
        )

    def mark_ready(self) -> None:
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.READY

    def mark_running(self) -> None:
        if self.status == TaskStatus.READY:
            self.status = TaskStatus.RUNNING
            self.started_at = datetime.now()

    def mark_success(self, result: Any = None) -> None:
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.SUCCESS
            self.result = result
            self.completed_at = datetime.now()

    def mark_failed(self, error: Exception) -> None:
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.FAILED
            self.error = error
            self.completed_at = datetime.now()

    def mark_blocked(self) -> None:
        if not self.is_terminal():
            self.status = TaskStatus.BLOCKED
            self.completed_at = datetime.now()
