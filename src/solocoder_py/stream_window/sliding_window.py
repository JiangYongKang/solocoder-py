from __future__ import annotations

import math
from typing import Dict, List, Optional

from .models import (
    AggregationResult,
    AggregationType,
    Event,
    InvalidWindowConfigError,
    LateEventDroppedError,
    Window,
    WindowState,
)
from .watermark import WatermarkGenerator


class SlidingWindowAggregator:
    def __init__(
        self,
        window_size_seconds: float,
        slide_seconds: float,
        agg_type: AggregationType = AggregationType.COUNT,
        allowed_lateness_seconds: float = 0.0,
        watermark_delay_seconds: float = 0.0,
    ) -> None:
        if window_size_seconds <= 0:
            raise InvalidWindowConfigError("window_size_seconds must be positive")
        if slide_seconds <= 0:
            raise InvalidWindowConfigError("slide_seconds must be positive")
        if slide_seconds > window_size_seconds:
            raise InvalidWindowConfigError(
                "slide_seconds must be <= window_size_seconds"
            )
        if allowed_lateness_seconds < 0:
            raise InvalidWindowConfigError("allowed_lateness_seconds must be non-negative")
        if watermark_delay_seconds < 0:
            raise InvalidWindowConfigError("watermark_delay_seconds must be non-negative")

        self._window_size: float = window_size_seconds
        self._slide: float = slide_seconds
        self._agg_type: AggregationType = agg_type
        self._allowed_lateness: float = allowed_lateness_seconds
        self._watermark_generator: WatermarkGenerator = WatermarkGenerator(
            delay_seconds=watermark_delay_seconds
        )
        self._windows: Dict[float, WindowState] = {}
        self._dropped_late_count: int = 0

    @property
    def window_size_seconds(self) -> float:
        return self._window_size

    @property
    def slide_seconds(self) -> float:
        return self._slide

    @property
    def agg_type(self) -> AggregationType:
        return self._agg_type

    @property
    def allowed_lateness_seconds(self) -> float:
        return self._allowed_lateness

    @property
    def watermark_delay_seconds(self) -> float:
        return self._watermark_generator.delay_seconds

    @property
    def dropped_late_count(self) -> int:
        return self._dropped_late_count

    def get_watermark(self) -> float:
        return self._watermark_generator.get_watermark()

    def get_active_window_count(self) -> int:
        return len(self._windows)

    def get_window_state(self, window_start: float) -> Optional[WindowState]:
        return self._windows.get(window_start)

    def _get_containing_window_starts(self, timestamp: float) -> List[float]:
        first_start = math.floor((timestamp - self._window_size) / self._slide) * self._slide + self._slide
        last_start = math.floor(timestamp / self._slide) * self._slide

        if first_start > last_start:
            return []

        starts: List[float] = []
        current = first_start
        while current <= last_start:
            if current < 0:
                current += self._slide
                continue
            starts.append(current)
            current += self._slide
        return starts

    def _is_window_fired(self, window_end: float) -> bool:
        watermark = self._watermark_generator.get_watermark()
        if watermark < 0:
            return False
        return watermark >= window_end

    def _is_window_cleanup_ready(self, window_end: float) -> bool:
        return self._watermark_generator.is_window_expired(window_end, self._allowed_lateness)

    def _is_event_too_late_for_window(
        self, event_timestamp: float, window_end: float
    ) -> bool:
        return self._watermark_generator.is_window_expired(window_end, self._allowed_lateness)

    def _add_event_to_window(self, event: Event, window_start: float) -> WindowState:
        window_end = window_start + self._window_size
        if window_start not in self._windows:
            window = Window(start=window_start, end=window_end)
            self._windows[window_start] = WindowState(window=window)

        state = self._windows[window_start]
        if event.value is not None:
            state.add(event.value)
        else:
            state.count += 1
        return state

    def _fire_and_cleanup_windows(self) -> List[AggregationResult]:
        results: List[AggregationResult] = []
        cleanup_starts: List[float] = []

        for window_start, state in self._windows.items():
            window_end = state.window.end

            if not state.fired and self._is_window_fired(window_end):
                state.fired = True
                results.append(
                    AggregationResult(
                        window=state.window,
                        agg_type=self._agg_type,
                        value=state.get_result(self._agg_type),
                        is_late_recompute=False,
                    )
                )

            if self._is_window_cleanup_ready(window_end):
                cleanup_starts.append(window_start)

        for start in cleanup_starts:
            del self._windows[start]

        return results

    def on_event(self, event: Event) -> List[AggregationResult]:
        self._watermark_generator.observe_event(event.timestamp)

        window_starts = self._get_containing_window_starts(event.timestamp)

        expired_windows: List[float] = []
        active_windows: List[float] = []
        for start in window_starts:
            window_end = start + self._window_size
            if self._is_event_too_late_for_window(event.timestamp, window_end):
                expired_windows.append(window_end)
            else:
                active_windows.append(start)

        if not active_windows and expired_windows:
            self._dropped_late_count += 1
            self._fire_and_cleanup_windows()
            earliest_window_end = min(expired_windows)
            raise LateEventDroppedError(
                event_timestamp=event.timestamp,
                window_end=earliest_window_end,
                allowed_lateness=self._allowed_lateness,
            )

        late_recompute_results: List[AggregationResult] = []
        for start in active_windows:
            was_fired = False
            if start in self._windows:
                was_fired = self._windows[start].fired

            self._add_event_to_window(event, start)

            if was_fired:
                state = self._windows[start]
                late_recompute_results.append(
                    AggregationResult(
                        window=state.window,
                        agg_type=self._agg_type,
                        value=state.get_result(self._agg_type),
                        is_late_recompute=True,
                    )
                )

        fire_results = self._fire_and_cleanup_windows()
        return late_recompute_results + fire_results

    def advance_watermark(self, new_watermark: float) -> List[AggregationResult]:
        self._watermark_generator.advance_watermark(new_watermark)
        return self._fire_and_cleanup_windows()

    def get_all_window_states(self) -> List[WindowState]:
        return list(self._windows.values())
