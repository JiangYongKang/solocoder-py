from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from ..ratelimiter.clock import Clock, SystemClock
from .models import (
    BucketConfig,
    BucketRequest,
    DroppedRequestRecord,
    EnqueueResult,
    LeakyBucketState,
    OverflowStrategy,
)


class LeakyBucket:
    def __init__(
        self,
        config: BucketConfig,
        overflow_strategy: OverflowStrategy = OverflowStrategy.REJECT_NEW,
        clock: Optional[Clock] = None,
    ) -> None:
        config.validate()
        self._config: BucketConfig = config
        self._overflow_strategy: OverflowStrategy = overflow_strategy
        self._clock: Clock = clock or SystemClock()
        self._queue: Deque[BucketRequest] = deque()
        self._last_leak_time: float = self._clock.now()
        self._leak_fraction: float = 0.0
        self._dropped_records: List[DroppedRequestRecord] = []
        self._processed_count: int = 0
        self._lock: threading.RLock = threading.RLock()

    def _leak(self) -> None:
        current_time = self._clock.now()
        elapsed = current_time - self._last_leak_time
        if elapsed <= 0:
            return

        total_requests_available = elapsed * self._config.leak_rate + self._leak_fraction
        can_leak_count = int(total_requests_available)

        if can_leak_count > 0:
            actual_leak = min(can_leak_count, len(self._queue))
            for _ in range(actual_leak):
                self._queue.popleft()
                self._processed_count += 1
            self._leak_fraction = total_requests_available - actual_leak
        else:
            self._leak_fraction = total_requests_available

        self._last_leak_time = current_time

    @property
    def capacity(self) -> int:
        with self._lock:
            return self._config.capacity

    @property
    def leak_rate(self) -> float:
        with self._lock:
            return self._config.leak_rate

    @property
    def overflow_strategy(self) -> OverflowStrategy:
        with self._lock:
            return self._overflow_strategy

    @property
    def dropped_records(self) -> List[DroppedRequestRecord]:
        with self._lock:
            return list(self._dropped_records)

    @property
    def dropped_count(self) -> int:
        with self._lock:
            return len(self._dropped_records)

    @property
    def processed_count(self) -> int:
        with self._lock:
            self._leak()
            return self._processed_count

    def current_size(self) -> int:
        with self._lock:
            self._leak()
            return len(self._queue)

    def is_empty(self) -> bool:
        with self._lock:
            self._leak()
            return len(self._queue) == 0

    def is_full(self) -> bool:
        with self._lock:
            self._leak()
            return len(self._queue) >= self._config.capacity

    def get_state(self) -> LeakyBucketState:
        with self._lock:
            self._leak()
            return LeakyBucketState(
                capacity=self._config.capacity,
                leak_rate=self._config.leak_rate,
                current_size=len(self._queue),
                last_leak_time=self._last_leak_time,
                dropped_count=len(self._dropped_records),
                processed_count=self._processed_count,
            )

    def _estimate_position_and_time(self, position_from_end: int) -> tuple[int, float, float]:
        queue_position = len(self._queue) + position_from_end
        estimated_wait = queue_position / self._config.leak_rate
        estimated_start = self._clock.now() + estimated_wait
        return queue_position, estimated_wait, estimated_start

    def enqueue(self, request: BucketRequest) -> EnqueueResult:
        with self._lock:
            self._leak()
            current_time = self._clock.now()
            request.enqueued_at = current_time

            if len(self._queue) < self._config.capacity:
                queue_position, estimated_wait, estimated_start = self._estimate_position_and_time(1)
                request.scheduled_at = estimated_start
                self._queue.append(request)
                return EnqueueResult(
                    accepted=True,
                    request=request,
                    queue_position=queue_position,
                    estimated_wait_seconds=estimated_wait,
                    estimated_start_time=estimated_start,
                )

            return self._handle_overflow(request, current_time)

    def _handle_overflow(
        self, request: BucketRequest, current_time: float
    ) -> EnqueueResult:
        if self._overflow_strategy == OverflowStrategy.REJECT_NEW:
            self._dropped_records.append(
                DroppedRequestRecord(
                    request=request,
                    dropped_at=current_time,
                    reason=OverflowStrategy.REJECT_NEW,
                )
            )
            return EnqueueResult(
                accepted=False,
                request=request,
                queue_position=0,
                estimated_wait_seconds=None,
                estimated_start_time=None,
                dropped_request=None,
                overflow_strategy=OverflowStrategy.REJECT_NEW,
            )

        if self._overflow_strategy == OverflowStrategy.DROP_OLDEST:
            dropped = self._queue.popleft()
            self._dropped_records.append(
                DroppedRequestRecord(
                    request=dropped,
                    dropped_at=current_time,
                    reason=OverflowStrategy.DROP_OLDEST,
                )
            )
            self._queue.append(request)
            queue_position, estimated_wait, estimated_start = self._estimate_position_and_time(0)
            request.scheduled_at = estimated_start
            return EnqueueResult(
                accepted=True,
                request=request,
                queue_position=queue_position,
                estimated_wait_seconds=estimated_wait,
                estimated_start_time=estimated_start,
                dropped_request=dropped,
                overflow_strategy=OverflowStrategy.DROP_OLDEST,
            )

        if self._overflow_strategy == OverflowStrategy.DROP_NEWEST:
            self._dropped_records.append(
                DroppedRequestRecord(
                    request=request,
                    dropped_at=current_time,
                    reason=OverflowStrategy.DROP_NEWEST,
                )
            )
            return EnqueueResult(
                accepted=False,
                request=request,
                queue_position=0,
                estimated_wait_seconds=None,
                estimated_start_time=None,
                dropped_request=request,
                overflow_strategy=OverflowStrategy.DROP_NEWEST,
            )

        self._dropped_records.append(
            DroppedRequestRecord(
                request=request,
                dropped_at=current_time,
                reason=self._overflow_strategy,
            )
        )
        return EnqueueResult(
            accepted=False,
            request=request,
            overflow_strategy=self._overflow_strategy,
        )

    def peek_next(self) -> Optional[BucketRequest]:
        with self._lock:
            self._leak()
            if not self._queue:
                return None
            return self._queue[0]

    def get_all_pending(self) -> List[BucketRequest]:
        with self._lock:
            self._leak()
            return list(self._queue)

    def clear(self) -> None:
        with self._lock:
            self._queue.clear()
            self._last_leak_time = self._clock.now()
            self._leak_fraction = 0.0

    def reset(self) -> None:
        with self._lock:
            self._queue.clear()
            self._last_leak_time = self._clock.now()
            self._leak_fraction = 0.0
            self._dropped_records.clear()
            self._processed_count = 0
