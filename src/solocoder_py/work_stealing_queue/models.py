from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOLEN = "stolen"


@dataclass
class Task:
    id: str
    body: Any
    owner_worker_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    stolen_by: str | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Task id cannot be empty")
        if not self.owner_worker_id:
            raise ValueError("owner_worker_id cannot be empty")

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING

    def mark_stolen(self, thief_worker_id: str) -> None:
        self.status = TaskStatus.STOLEN
        self.stolen_by = thief_worker_id

    def mark_completed(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self, error_message: str | None = None) -> None:
        self.status = TaskStatus.FAILED
        self.failed_at = datetime.now()
        self.error_message = error_message
