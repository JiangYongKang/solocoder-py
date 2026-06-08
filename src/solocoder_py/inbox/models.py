from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .clock import Clock, SystemClock


class DedupWindowMode(str, Enum):
    COUNT = "count"
    TIME = "time"
    HYBRID = "hybrid"


@dataclass
class InboxMessageRecord:
    message_id: str
    received_at: float = field(default_factory=lambda: SystemClock().now())

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id cannot be empty")

    def is_expired(self, ttl_seconds: float, clock: Optional[Clock] = None) -> bool:
        effective_clock = clock if clock is not None else SystemClock()
        return effective_clock.now() - self.received_at >= ttl_seconds

    def age_seconds(self, clock: Optional[Clock] = None) -> float:
        effective_clock = clock if clock is not None else SystemClock()
        return effective_clock.now() - self.received_at

    def snapshot(self) -> "InboxMessageRecord":
        return InboxMessageRecord(
            message_id=self.message_id,
            received_at=self.received_at,
        )


@dataclass
class DedupResult:
    is_duplicate: bool
    record: Optional[InboxMessageRecord]

    @property
    def should_process(self) -> bool:
        return not self.is_duplicate


@dataclass
class DedupStats:
    window_size: int
    total_received: int
    total_duplicates: int
    hit_rate: float

    def __post_init__(self) -> None:
        if self.total_received < 0:
            raise ValueError("total_received cannot be negative")
        if self.total_duplicates < 0:
            raise ValueError("total_duplicates cannot be negative")
        if self.total_duplicates > self.total_received and self.total_received > 0:
            raise ValueError("total_duplicates cannot exceed total_received")
        if self.hit_rate < 0.0 or self.hit_rate > 1.0:
            raise ValueError("hit_rate must be between 0.0 and 1.0")
