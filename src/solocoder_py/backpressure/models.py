from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class BackpressureStrategy(str, Enum):
    BLOCK = "block"
    DROP = "drop"
    REJECT = "reject"


class BackpressureError(Exception):
    pass


class QueueFullError(BackpressureError):
    pass


class RejectedError(BackpressureError):
    def __init__(self, element: Any, message: Optional[str] = None) -> None:
        self.element = element
        msg = message or f"Element rejected due to queue full: {element!r}"
        super().__init__(msg)


class DequeueTimeoutError(BackpressureError):
    pass


HighWatermarkCallback = Callable[["BoundedQueueState"], None]
LowWatermarkCallback = Callable[["BoundedQueueState"], None]


@dataclass(frozen=True)
class BoundedQueueState:
    capacity: int
    size: int
    strategy: BackpressureStrategy
    is_high_watermark: bool
    dropped_count: int
    rejected_count: int

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - self.size


@dataclass(frozen=True)
class EnqueueResult:
    success: bool
    dropped: bool = False
    element: Any = None
