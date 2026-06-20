from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from .buffer import BatchBuffer
from .clock import Clock, SystemClock
from .models import (
    BufferConfig,
    FlushReason,
    FlushResult,
    LateDataStrategy,
    ProcessedBatch,
    SchemaConfig,
    WindowConfig,
)
from .schema import SchemaNormalizer
from .window import OrderWindow

logger = logging.getLogger(__name__)


class TelemetryPipeline:
    def __init__(
        self,
        buffer_config: BufferConfig,
        schema_config: SchemaConfig,
        window_config: WindowConfig,
        on_batch: Optional[Callable[[ProcessedBatch], None]] = None,
        on_late: Optional[Callable[[dict[str, Any]], None]] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._buffer_config = buffer_config
        self._schema_config = schema_config
        self._window_config = window_config
        self._on_batch = on_batch
        self._on_late = on_late
        self._clock = clock or SystemClock()

        self._normalizer = SchemaNormalizer(schema_config)
        self._order_window = OrderWindow(
            window_config,
            on_late=on_late,
        )

        self._processed_batches: list[ProcessedBatch] = []
        self._history_lock = threading.Lock()

        self._buffer = BatchBuffer(
            buffer_config,
            on_flush=self._handle_flush,
            clock=self._clock,
        )

    @property
    def buffer(self) -> BatchBuffer:
        return self._buffer

    @property
    def normalizer(self) -> SchemaNormalizer:
        return self._normalizer

    @property
    def order_window(self) -> OrderWindow:
        return self._order_window

    @property
    def processed_batches(self) -> list[ProcessedBatch]:
        with self._history_lock:
            return list(self._processed_batches)

    def ingest(self, data: dict[str, Any]) -> None:
        self._buffer.ingest(data)

    def ingest_many(self, items: list[dict[str, Any]]) -> None:
        self._buffer.ingest_many(items)

    def flush(self) -> Optional[ProcessedBatch]:
        flush_result = self._buffer.flush()
        if flush_result is None:
            return None
        return self._process_batch(flush_result)

    def start(self) -> None:
        self._buffer.start()

    def stop(self) -> None:
        self._buffer.stop()

    def close(self) -> None:
        self._buffer.close()

    def _handle_flush(self, result: FlushResult) -> None:
        batch = self._process_batch(result)
        if batch is not None and self._on_batch is not None:
            try:
                self._on_batch(batch)
            except Exception:
                logger.exception("Error in on_batch callback")

    def _process_batch(self, result: FlushResult) -> Optional[ProcessedBatch]:
        normalized = self._normalizer.normalize_batch(result.batch)
        accepted, late = self._order_window.process(normalized)
        sorted_data = self._order_window.drain()

        batch = ProcessedBatch(
            data=sorted_data,
            late_data=late,
            original_count=len(result.batch),
        )

        with self._history_lock:
            self._processed_batches.append(batch)

        return batch

    def __enter__(self) -> "TelemetryPipeline":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
