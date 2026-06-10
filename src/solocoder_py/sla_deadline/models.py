from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SlaTimerStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    EXPIRED = "expired"


@dataclass
class PauseRecord:
    pause_time: datetime
    resume_time: Optional[datetime] = None
    work_hours_before_pause: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.resume_time is None

    @property
    def pause_duration_seconds(self) -> float:
        if self.resume_time is None:
            return 0.0
        return (self.resume_time - self.pause_time).total_seconds()


@dataclass
class SlaTimerResult:
    total_work_hours: float
    elapsed_work_hours: float
    remaining_work_hours: float
    estimated_deadline: datetime
    is_expired: bool
    status: SlaTimerStatus
    current_time: datetime

    @property
    def progress_percentage(self) -> float:
        if self.total_work_hours <= 0:
            return 100.0 if self.is_expired else 0.0
        return min(100.0, (self.elapsed_work_hours / self.total_work_hours) * 100.0)
