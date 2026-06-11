from __future__ import annotations

import threading
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar
from collections.abc import Sequence

from .clock import Clock, SystemClock
from .exceptions import BufferClosedError
from .models import (
    BatchRecord,
    BatchStatus,
    FlushResult,
    MicroBatchConfig,
    T,
)


class BatchWriter(Protocol[T]):
    def write_batch(self, batch: Sequence[T]) -> FlushResult:
        ...


class MicroBatchBatcher(Generic[T]):
    def __init__(
        self,
        writer: BatchWriter[T],
        config: Optional[MicroBatchConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._writer = writer
        self._config = config or MicroBatchConfig()
        self._clock = clock or SystemClock()

        self._buffer: list[T] = []
        self._buffer_lock = threading.Lock()
        self._flush_lock = threading.Lock()

        self._last_flush_time: float = self._clock.now()
        self._batch_counter: int = 0
        self._closed: bool = False
        self._scheduler_running: bool = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_stop_event = threading.Event()

        self._success_batches: list[BatchRecord[T]] = []
        self._failed_batches: list[BatchRecord[T]] = []
        self._history_lock = threading.Lock()

    @property
    def config(self) -> MicroBatchConfig:
        return self._config

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def buffer_size(self) -> int:
        with self._buffer_lock:
            return len(self._buffer)

    @property
    def success_batches(self) -> list[BatchRecord[T]]:
        with self._history_lock:
            return list(self._success_batches)

    @property
    def failed_batches(self) -> list[BatchRecord[T]]:
        with self._history_lock:
            return list(self._failed_batches)

    @property
    def is_closed(self) -> bool:
        return self._closed

    def submit(self, item: T) -> None:
        if self._closed:
            raise BufferClosedError("Cannot submit to a closed batcher")

        with self._buffer_lock:
            self._buffer.append(item)
            current_size = len(self._buffer)

        if current_size >= self._config.max_size:
            self.flush_if_needed(force=False)

    def submit_many(self, items: Sequence[T]) -> None:
        if self._closed:
            raise BufferClosedError("Cannot submit to a closed batcher")

        with self._buffer_lock:
            self._buffer.extend(items)
            current_size = len(self._buffer)

        if current_size >= self._config.max_size:
            self.flush_if_needed(force=False)

    def flush_if_needed(self, force: bool = False) -> bool:
        with self._buffer_lock:
            if not self._buffer:
                return False

            elapsed = self._clock.now() - self._last_flush_time
            should_flush = (
                force
                or len(self._buffer) >= self._config.max_size
                or elapsed >= self._config.max_interval
            )

            if not should_flush:
                return False

            batch = self._buffer
            self._buffer = []

        self._flush_batch(batch)
        return True

    def flush_all(self) -> None:
        flushed = True
        while flushed:
            flushed = self.flush_if_needed(force=True)

    def start(self) -> None:
        if self._scheduler_running:
            return
        self._scheduler_running = True
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="MicroBatchScheduler",
        )
        self._scheduler_thread.start()

    def stop(self, flush_remaining: bool = True) -> None:
        if not self._scheduler_running:
            if flush_remaining and not self._closed:
                self.flush_all()
            return

        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=5.0)
        self._scheduler_running = False

        if flush_remaining:
            self.flush_all()

    def close(self, flush_remaining: bool = True) -> None:
        if self._closed:
            return
        self.stop(flush_remaining=flush_remaining)
        self._closed = True

    def _scheduler_loop(self) -> None:
        interval = self._config.scheduler_interval
        while not self._scheduler_stop_event.is_set():
            try:
                self.flush_if_needed(force=False)
            except Exception:
                pass
            self._scheduler_stop_event.wait(interval)

    def _flush_batch(self, batch: list[T]) -> None:
        with self._flush_lock:
            created_at = self._clock.now()
            self._batch_counter += 1
            batch_id = self._batch_counter

            record = BatchRecord(
                batch_id=batch_id,
                items=list(batch),
                status=BatchStatus.PENDING,
                created_at=created_at,
            )

            record.status = BatchStatus.FLUSHING
            record.attempts = 0
            last_error: Exception | None = None

            max_total_attempts = self._config.max_retries + 1
            for attempt in range(1, max_total_attempts + 1):
                record.attempts = attempt
                try:
                    result = self._writer.write_batch(record.items)
                    if result.is_success:
                        record.status = BatchStatus.SUCCESS
                        record.last_error = None
                        break
                    else:
                        last_error = result.error
                        record.last_error = last_error
                except Exception as exc:
                    last_error = exc
                    record.last_error = exc

                if attempt < max_total_attempts and self._config.retry_interval > 0:
                    self._clock.sleep(self._config.retry_interval)

            if record.status != BatchStatus.SUCCESS:
                record.status = BatchStatus.FAILED
                record.last_error = last_error

            record.flushed_at = self._clock.now()
            self._last_flush_time = record.flushed_at

            with self._history_lock:
                if record.status == BatchStatus.SUCCESS:
                    self._success_batches.append(record)
                else:
                    self._failed_batches.append(record)

    def __enter__(self) -> "MicroBatchBatcher[T]":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close(flush_remaining=True)
