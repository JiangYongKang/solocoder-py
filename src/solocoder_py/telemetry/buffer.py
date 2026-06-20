from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .clock import Clock, SystemClock
from .exceptions import BufferClosedError, InvalidDataError
from .models import BufferConfig, FlushReason, FlushResult

logger = logging.getLogger(__name__)


class BatchBuffer:
    def __init__(
        self,
        config: BufferConfig,
        on_flush: Callable[[FlushResult], None],
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config
        self._on_flush = on_flush
        self._clock = clock or SystemClock()

        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._flush_lock = threading.Lock()

        self._last_flush_time: float = self._clock.now()
        self._batch_counter: int = 0
        self._closed: bool = False

        self._scheduler_running: bool = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_stop_event = threading.Event()
        self._has_data: bool = False

    @property
    def config(self) -> BufferConfig:
        return self._config

    @property
    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def is_closed(self) -> bool:
        return self._closed

    def ingest(self, data: dict[str, Any]) -> None:
        if self._closed:
            raise BufferClosedError("Cannot ingest into a closed buffer")

        if not isinstance(data, dict):
            raise InvalidDataError(
                f"Expected dict, got {type(data).__name__}"
            )

        with self._lock:
            self._buffer.append(data)
            self._has_data = True

        self._try_flush(force=False)

    def ingest_many(self, items: list[dict[str, Any]]) -> None:
        if self._closed:
            raise BufferClosedError("Cannot ingest into a closed buffer")

        for item in items:
            if not isinstance(item, dict):
                raise InvalidDataError(
                    f"Expected dict, got {type(item).__name__}"
                )

        with self._lock:
            self._buffer.extend(items)
            self._has_data = True

        self._try_flush(force=False)

    def flush(self) -> Optional[FlushResult]:
        return self._try_flush(force=True)

    def _try_flush(self, force: bool = False) -> Optional[FlushResult]:
        with self._lock:
            if not self._buffer:
                return None

            elapsed = self._clock.now() - self._last_flush_time
            size_reached = len(self._buffer) >= self._config.batch_size
            timeout_reached = (
                self._has_data and elapsed >= self._config.timeout_seconds
            )

            should_flush = force or size_reached or timeout_reached
            if not should_flush:
                return None

            batch = self._buffer
            self._buffer = []
            self._has_data = False

            if force:
                reason = FlushReason.MANUAL
            elif size_reached:
                reason = FlushReason.BATCH_SIZE
            else:
                reason = FlushReason.TIMEOUT

        return self._do_flush(batch, reason)

    def _do_flush(
        self, batch: list[dict[str, Any]], reason: FlushReason
    ) -> FlushResult:
        with self._flush_lock:
            self._batch_counter += 1
            result = FlushResult(
                batch=batch,
                reason=reason,
                flushed_at=self._clock.now(),
                batch_id=self._batch_counter,
            )
            self._last_flush_time = self._clock.now()
            try:
                self._on_flush(result)
            except Exception:
                logger.exception("Error in on_flush callback")
            return result

    def start(self) -> None:
        if self._scheduler_running:
            return
        self._scheduler_running = True
        self._scheduler_stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="TelemetryBufferScheduler",
        )
        self._scheduler_thread.start()

    def stop(self) -> None:
        if not self._scheduler_running:
            return
        self._scheduler_stop_event.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=5.0)
        self._scheduler_running = False

    def close(self) -> None:
        if self._closed:
            return
        self.stop()
        self._try_flush(force=True)
        self._closed = True

    def _scheduler_loop(self) -> None:
        check_interval = min(0.1, self._config.timeout_seconds / 2) if self._config.timeout_seconds > 0 else 0.1
        while not self._scheduler_stop_event.is_set():
            try:
                self._try_flush(force=False)
            except Exception:
                logger.exception("Error in buffer scheduler loop")
            self._scheduler_stop_event.wait(check_interval)

    def __enter__(self) -> "BatchBuffer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
