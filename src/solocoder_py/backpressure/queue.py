from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, List, Optional

from .models import (
    BackpressureStrategy,
    BoundedQueueState,
    DequeueTimeoutError,
    EnqueueResult,
    HighWatermarkCallback,
    LowWatermarkCallback,
    QueueFullError,
    RejectedError,
)


class BoundedQueue:
    def __init__(
        self,
        capacity: int,
        strategy: BackpressureStrategy = BackpressureStrategy.BLOCK,
        high_watermark_ratio: float = 0.8,
        low_watermark_ratio: float = 0.2,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0.0 <= low_watermark_ratio <= high_watermark_ratio <= 1.0):
            raise ValueError(
                "watermark ratios must satisfy 0 <= low <= high <= 1"
            )

        self._capacity = capacity
        self._strategy = strategy
        self._high_watermark = max(1, int(capacity * high_watermark_ratio))
        self._low_watermark = min(capacity - 1, int(capacity * low_watermark_ratio))

        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._not_full = threading.Condition(self._lock)
        self._not_empty = threading.Condition(self._lock)

        self._dropped_count = 0
        self._rejected_count = 0
        self._in_high_watermark = False

        self._high_callbacks: List[HighWatermarkCallback] = []
        self._low_callbacks: List[LowWatermarkCallback] = []

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def remaining_capacity(self) -> int:
        with self._lock:
            return self._capacity - len(self._queue)

    @property
    def strategy(self) -> BackpressureStrategy:
        with self._lock:
            return self._strategy

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return self._dropped_count

    @property
    def rejected_count(self) -> int:
        with self._lock:
            return self._rejected_count

    @property
    def is_high_watermark(self) -> bool:
        with self._lock:
            return self._in_high_watermark

    def get_state(self) -> BoundedQueueState:
        with self._lock:
            return BoundedQueueState(
                capacity=self._capacity,
                size=len(self._queue),
                strategy=self._strategy,
                is_high_watermark=self._in_high_watermark,
                dropped_count=self._dropped_count,
                rejected_count=self._rejected_count,
            )

    def set_strategy(self, strategy: BackpressureStrategy) -> None:
        with self._lock:
            self._strategy = strategy

    def register_high_watermark_callback(self, callback: HighWatermarkCallback) -> None:
        with self._lock:
            self._high_callbacks.append(callback)

    def register_low_watermark_callback(self, callback: LowWatermarkCallback) -> None:
        with self._lock:
            self._low_callbacks.append(callback)

    def clear_callbacks(self) -> None:
        with self._lock:
            self._high_callbacks.clear()
            self._low_callbacks.clear()

    def _fire_high_watermark(self) -> None:
        state = BoundedQueueState(
            capacity=self._capacity,
            size=len(self._queue),
            strategy=self._strategy,
            is_high_watermark=True,
            dropped_count=self._dropped_count,
            rejected_count=self._rejected_count,
        )
        for cb in list(self._high_callbacks):
            cb(state)

    def _fire_low_watermark(self) -> None:
        state = BoundedQueueState(
            capacity=self._capacity,
            size=len(self._queue),
            strategy=self._strategy,
            is_high_watermark=False,
            dropped_count=self._dropped_count,
            rejected_count=self._rejected_count,
        )
        for cb in list(self._low_callbacks):
            cb(state)

    def _check_watermark_on_enqueue(self, previous_size: int) -> None:
        current_size = len(self._queue)
        if (
            not self._in_high_watermark
            and previous_size < self._high_watermark
            and current_size >= self._high_watermark
        ):
            self._in_high_watermark = True
            self._fire_high_watermark()

    def _check_watermark_on_dequeue(self, previous_size: int) -> None:
        current_size = len(self._queue)
        if (
            self._in_high_watermark
            and previous_size > self._low_watermark
            and current_size <= self._low_watermark
        ):
            self._in_high_watermark = False
            self._fire_low_watermark()

    def enqueue(
        self,
        element: Any,
        *,
        strategy: Optional[BackpressureStrategy] = None,
        timeout: Optional[float] = None,
    ) -> EnqueueResult:
        effective_strategy = strategy if strategy is not None else self._strategy

        if effective_strategy == BackpressureStrategy.BLOCK:
            return self._enqueue_block(element, timeout)
        elif effective_strategy == BackpressureStrategy.DROP:
            return self._enqueue_drop(element)
        elif effective_strategy == BackpressureStrategy.REJECT:
            return self._enqueue_reject(element)
        else:
            raise ValueError(f"Unknown strategy: {effective_strategy}")

    def _enqueue_block(self, element: Any, timeout: Optional[float]) -> EnqueueResult:
        deadline = None if timeout is None else time.monotonic() + timeout

        with self._not_full:
            while len(self._queue) >= self._capacity:
                if timeout is None:
                    self._not_full.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._dropped_count += 1
                        return EnqueueResult(success=False, dropped=True, element=element)
                    self._not_full.wait(timeout=remaining)

            previous_size = len(self._queue)
            self._queue.append(element)
            self._check_watermark_on_enqueue(previous_size)
            self._not_empty.notify_all()
            return EnqueueResult(success=True)

    def _enqueue_drop(self, element: Any) -> EnqueueResult:
        with self._not_empty:
            if len(self._queue) >= self._capacity:
                self._dropped_count += 1
                return EnqueueResult(success=False, dropped=True, element=element)

            previous_size = len(self._queue)
            self._queue.append(element)
            self._check_watermark_on_enqueue(previous_size)
            self._not_empty.notify_all()
            return EnqueueResult(success=True)

    def _enqueue_reject(self, element: Any) -> EnqueueResult:
        with self._not_empty:
            if len(self._queue) >= self._capacity:
                self._rejected_count += 1
                raise RejectedError(element=element)

            previous_size = len(self._queue)
            self._queue.append(element)
            self._check_watermark_on_enqueue(previous_size)
            self._not_empty.notify_all()
            return EnqueueResult(success=True)

    def dequeue(self, *, timeout: Optional[float] = None, block: bool = True) -> Any:
        deadline = None if timeout is None else time.monotonic() + timeout

        with self._not_empty:
            if not block:
                if len(self._queue) == 0:
                    return None
            else:
                while len(self._queue) == 0:
                    if timeout is None:
                        self._not_empty.wait()
                    else:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise DequeueTimeoutError("dequeue timed out")
                        self._not_empty.wait(timeout=remaining)

            previous_size = len(self._queue)
            element = self._queue.popleft()
            self._check_watermark_on_dequeue(previous_size)
            self._not_full.notify_all()
            return element

    def clear(self) -> None:
        with self._not_full:
            self._queue.clear()
            self._dropped_count = 0
            self._rejected_count = 0
            self._in_high_watermark = False
            self._not_full.notify_all()

    def __len__(self) -> int:
        return self.size

    def __bool__(self) -> bool:
        return self.size > 0
