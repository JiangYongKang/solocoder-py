from __future__ import annotations

import bisect
import logging
from typing import Any, Callable, Optional

from .exceptions import LateDataError
from .models import LateDataStrategy, WindowConfig

logger = logging.getLogger(__name__)


class OrderWindow:
    def __init__(
        self,
        config: WindowConfig,
        on_late: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self._config = config
        self._on_late = on_late

        self._window: list[dict[str, Any]] = []
        self._timestamps: list[float] = []
        self._high_watermark: Optional[float] = None
        self._late_data: list[dict[str, Any]] = []

    @property
    def config(self) -> WindowConfig:
        return self._config

    @property
    def high_watermark(self) -> Optional[float]:
        return self._high_watermark

    @property
    def window_size(self) -> int:
        return len(self._window)

    @property
    def late_data(self) -> list[dict[str, Any]]:
        return list(self._late_data)

    def process(
        self, records: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        accepted: list[dict[str, Any]] = []
        late: list[dict[str, Any]] = []

        for record in records:
            ts = self._extract_timestamp(record)
            if ts is None:
                late.append(record)
                self._late_data.append(record)
                self._handle_late(record)
                continue

            is_accepted = self._try_insert(record, ts)
            if is_accepted:
                accepted.append(record)
            else:
                late.append(record)
                self._late_data.append(record)
                self._handle_late(record)

        return accepted, late

    def _extract_timestamp(self, record: dict[str, Any]) -> Optional[float]:
        ts_field = self._config.timestamp_field
        ts = record.get(ts_field)
        if ts is None:
            return None
        try:
            return float(ts)
        except (ValueError, TypeError):
            return None

    def _try_insert(self, record: dict[str, Any], ts: float) -> bool:
        if self._high_watermark is None:
            self._high_watermark = ts
            self._insert_sorted(record, ts)
            return True

        if ts >= self._high_watermark:
            self._high_watermark = ts
            self._insert_sorted(record, ts)
            return True

        diff = self._high_watermark - ts
        if diff <= self._config.tolerance_seconds:
            self._insert_sorted(record, ts)
            return True

        return False

    def _insert_sorted(self, record: dict[str, Any], ts: float) -> None:
        idx = bisect.bisect_right(self._timestamps, ts)
        self._timestamps.insert(idx, ts)
        self._window.insert(idx, record)

    def _handle_late(self, record: dict[str, Any]) -> None:
        strategy = self._config.late_data_strategy
        if strategy == LateDataStrategy.LOG:
            logger.warning(
                "Late telemetry data detected: %s", record
            )
        elif strategy == LateDataStrategy.DISCARD:
            pass
        elif strategy == LateDataStrategy.CALLBACK:
            if self._on_late is not None:
                self._on_late(record)

    def drain(self) -> list[dict[str, Any]]:
        result = list(self._window)
        self._window.clear()
        self._timestamps.clear()
        return result

    def flush(self) -> list[dict[str, Any]]:
        result = self.drain()
        self._high_watermark = None
        return result

    def reset(self) -> None:
        self._window.clear()
        self._timestamps.clear()
        self._high_watermark = None
        self._late_data.clear()
