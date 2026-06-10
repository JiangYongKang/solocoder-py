from __future__ import annotations

from typing import Optional


class WatermarkGenerator:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")

        self._delay_seconds: float = delay_seconds
        self._max_event_time: float = -1.0
        self._current_watermark: float = -1.0

    @property
    def delay_seconds(self) -> float:
        return self._delay_seconds

    @property
    def max_event_time(self) -> float:
        return self._max_event_time

    def observe_event(self, timestamp: float) -> float:
        if timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if timestamp > self._max_event_time:
            self._max_event_time = timestamp
        return self.get_watermark()

    def get_watermark(self) -> float:
        if self._max_event_time < 0:
            return -1.0
        return self._max_event_time - self._delay_seconds

    def advance_watermark(self, new_watermark: float) -> float:
        if new_watermark < 0:
            raise ValueError("watermark must be non-negative")
        if new_watermark > self._current_watermark:
            self._current_watermark = new_watermark
            effective_max = new_watermark + self._delay_seconds
            if effective_max > self._max_event_time:
                self._max_event_time = effective_max
        return self._current_watermark

    def is_window_expired(self, window_end: float, allowed_lateness: float = 0.0) -> bool:
        watermark = self.get_watermark()
        if watermark < 0:
            return False
        return watermark >= window_end + allowed_lateness
