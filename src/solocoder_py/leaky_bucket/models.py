from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class LeakyBucketError(Exception):
    pass


class InvalidBucketConfigError(LeakyBucketError):
    pass


class BucketOverflowError(LeakyBucketError):
    def __init__(self, request_id: str, strategy: "OverflowStrategy") -> None:
        self.request_id = request_id
        self.strategy = strategy
        super().__init__(
            f"Request {request_id} rejected due to bucket overflow (strategy={strategy.value})"
        )


class OverflowStrategy(str, Enum):
    REJECT_NEW = "reject_new"
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"


@dataclass
class BucketConfig:
    capacity: int
    leak_rate: float

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.capacity <= 0:
            raise InvalidBucketConfigError("capacity must be positive")
        if self.leak_rate <= 0:
            raise InvalidBucketConfigError("leak_rate must be positive")


@dataclass
class BucketRequest:
    id: str
    payload: Any = None
    enqueued_at: Optional[float] = None
    scheduled_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class EnqueueResult:
    accepted: bool
    request: BucketRequest
    queue_position: int = 0
    estimated_start_time: Optional[float] = None
    estimated_wait_seconds: Optional[float] = None
    dropped_request: Optional[BucketRequest] = None
    overflow_strategy: Optional[OverflowStrategy] = None


@dataclass
class DroppedRequestRecord:
    request: BucketRequest
    dropped_at: float
    reason: OverflowStrategy


@dataclass
class LeakyBucketState:
    capacity: int
    leak_rate: float
    current_size: int
    last_leak_time: float
    dropped_count: int
    processed_count: int
