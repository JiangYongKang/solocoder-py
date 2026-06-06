from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional


class SchedulerError(Exception):
    pass


class InsufficientSlotsError(SchedulerError):
    pass


class TaskNotFoundError(SchedulerError):
    pass


class TaskNotRunningError(SchedulerError):
    pass


class Priority(IntEnum):
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4

    @classmethod
    def clamp(cls, value: int) -> "Priority":
        if value <= cls.LOWEST:
            return cls.LOWEST
        if value >= cls.HIGHEST:
            return cls.HIGHEST
        return cls(value)


@dataclass
class Task:
    id: str
    resource_slots: int
    priority: Priority = Priority.NORMAL
    name: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.now)
    effective_priority: Priority = field(init=False)
    wait_started_at: datetime = field(init=False)
    last_promoted_at: Optional[datetime] = field(default=None)
    is_running: bool = field(default=False)
    started_at: Optional[datetime] = field(default=None)
    is_starvation_protected: bool = field(default=False)

    def __post_init__(self) -> None:
        if self.resource_slots <= 0:
            raise ValueError("resource_slots must be positive")
        self.effective_priority = self.priority
        self.wait_started_at = self.submitted_at

    @classmethod
    def create(
        cls,
        resource_slots: int,
        priority: Priority = Priority.NORMAL,
        name: Optional[str] = None,
    ) -> "Task":
        return cls(
            id=str(uuid.uuid4()),
            resource_slots=resource_slots,
            priority=priority,
            name=name,
        )
