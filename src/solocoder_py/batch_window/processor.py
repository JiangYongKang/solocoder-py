from __future__ import annotations

import math
from typing import Dict, List, Optional

from .exceptions import (
    InvalidWindowConfigError,
    LateEventDroppedError,
    WindowAlreadyClosedError,
)
from .models import (
    AggregationResult,
    AggregationType,
    Event,
    OutputType,
    Window,
    WindowState,
)
from .watermark import WatermarkGenerator


class BatchWindowProcessor:
    def __init__(
        self,
        window_size_seconds: float,
        agg_type: AggregationType = AggregationType.COUNT,
        allowed_lateness_seconds: float = 0.0,
        watermark_delay_seconds: float = 5.0,
    ) -> None:
        if window_size_seconds <= 0:
            raise InvalidWindowConfigError("window_size_seconds must be positive")
        if allowed_lateness_seconds < 0:
            raise InvalidWindowConfigError("allowed_lateness_seconds must be non-negative")
        if watermark_delay_seconds < 0:
            raise InvalidWindowConfigError("watermark_delay_seconds must be non-negative")

        self._window_size: float = window_size_seconds
        self._agg_type: AggregationType = agg_type
        self._allowed_lateness: float = allowed_lateness_seconds
        self._watermark_generator: WatermarkGenerator = WatermarkGenerator(
            delay_seconds=watermark_delay_seconds
        )
        self._windows: Dict[float, WindowState] = {}
        self._dropped_late_count: int = 0
        self._rejected_closed_count: int = 0
        self._emitted_final_windows: set = set()

    @property
    def window_size_seconds(self) -> float:
        return self._window_size

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

    @property
    def rejected_closed_count(self) -> int:
        return self._rejected_closed_count

    def get_watermark(self) -> float:
        return self._watermark_generator.get_watermark()

    def get_active_window_count(self) -> int:
        return len(self._windows)

    def get_window_state(self, window_start: float) -> Optional[WindowState]:
        return self._windows.get(window_start)

    def get_all_window_states(self) -> List[WindowState]:
        return list(self._windows.values())

    def _get_window_start(self, timestamp: float) -> float:
        return math.floor(timestamp / self._window_size) * self._window_size

    def _create_result(
        self,
        state: WindowState,
        output_type: OutputType,
        is_late_update: bool = False,
    ) -> AggregationResult:
        return AggregationResult(
            window=state.window,
            agg_type=self._agg_type,
            value=state.get_result(self._agg_type),
            output_type=output_type,
            is_late_update=is_late_update,
        )

    def _is_event_droppable(self, event_timestamp: float, window_end: float, window_start: float) -> bool:
        if not self._watermark_generator.is_window_expired(window_end, self._allowed_lateness):
            return False
        if window_start not in self._windows:
            return True
        return True

    def _add_event_to_window(self, event: Event, window_start: float) -> WindowState:
        window_end = window_start + self._window_size
        if window_start not in self._windows:
            window = Window(start=window_start, end=window_end)
            self._windows[window_start] = WindowState(window=window)

        state = self._windows[window_start]
        if state.is_closed:
            raise WindowAlreadyClosedError(window_start, window_end)

        if event.value is not None:
            state.add(event.value)
        else:
            state.count += 1
        return state

    def _process_window_closures(self) -> List[AggregationResult]:
        results: List[AggregationResult] = []
        window_starts = list(self._windows.keys())
        close_starts: List[float] = []

        for window_start in window_starts:
            if window_start not in self._windows:
                continue
            state = self._windows[window_start]
            window_end = state.window.end

            if not state.is_fired and self._watermark_generator.is_window_triggerable(window_end):
                state.is_fired = True
                if state.count > 0 and window_start not in self._emitted_final_windows:
                    if self._allowed_lateness > 0:
                        results.append(
                            self._create_result(state, OutputType.INTERMEDIATE, is_late_update=False)
                        )
                    else:
                        state.is_closed = True
                        state.final_output_emitted = True
                        self._emitted_final_windows.add(window_start)
                        results.append(
                            self._create_result(state, OutputType.FINAL, is_late_update=False)
                        )
                        close_starts.append(window_start)
                        continue

            if not state.is_closed and self._watermark_generator.is_window_expired(
                window_end, self._allowed_lateness
            ):
                if not state.final_output_emitted and state.count > 0:
                    state.is_closed = True
                    state.final_output_emitted = True
                    self._emitted_final_windows.add(window_start)
                    results.append(
                        self._create_result(state, OutputType.FINAL, is_late_update=state.is_fired)
                    )
                state.is_closed = True
                close_starts.append(window_start)

        for start in close_starts:
            if start in self._windows:
                del self._windows[start]

        return results

    def on_event(self, event: Event) -> List[AggregationResult]:
        self._watermark_generator.observe_event(event.timestamp)

        window_start = self._get_window_start(event.timestamp)
        window_end = window_start + self._window_size

        existing_state = self._windows.get(window_start)

        if self._is_event_droppable(event.timestamp, window_end, window_start):
            self._dropped_late_count += 1
            self._process_window_closures()
            raise LateEventDroppedError(
                event_timestamp=event.timestamp,
                window_end=window_end,
                allowed_lateness=self._allowed_lateness,
            )

        if existing_state is not None and existing_state.is_closed:
            self._rejected_closed_count += 1
            self._process_window_closures()
            raise WindowAlreadyClosedError(window_start, window_end)

        was_fired = False
        if existing_state is not None:
            was_fired = existing_state.is_fired

        state = self._add_event_to_window(event, window_start)

        late_update_results: List[AggregationResult] = []
        if was_fired and self._allowed_lateness > 0 and not state.is_closed:
            late_update_results.append(
                self._create_result(state, OutputType.INTERMEDIATE, is_late_update=True)
            )

        closure_results = self._process_window_closures()
        return late_update_results + closure_results

    def advance_watermark(self, new_watermark: float) -> List[AggregationResult]:
        self._watermark_generator.advance_watermark(new_watermark)
        return self._process_window_closures()

    def process_source(self, source) -> List[AggregationResult]:
        all_results: List[AggregationResult] = []
        while source.has_next():
            event = source.next()
            try:
                results = self.on_event(event)
                all_results.extend(results)
            except LateEventDroppedError:
                continue
            except WindowAlreadyClosedError:
                continue
        if self._watermark_generator.max_event_time >= 0:
            last_window_start = self._get_window_start(
                self._watermark_generator.max_event_time
            )
            last_window_end = last_window_start + self._window_size
            final_watermark = last_window_end + self._allowed_lateness
            final_results = self.advance_watermark(final_watermark)
            all_results.extend(final_results)
        return all_results

    def get_final_output_count(self) -> int:
        return len(self._emitted_final_windows)

    def get_final_output_windows(self) -> List[Window]:
        result = []
        for start in sorted(self._emitted_final_windows):
            end = start + self._window_size
            result.append(Window(start=start, end=end))
        return result

    def reset(self) -> None:
        self._windows.clear()
        self._dropped_late_count = 0
        self._rejected_closed_count = 0
        self._emitted_final_windows.clear()
        self._watermark_generator = WatermarkGenerator(
            delay_seconds=self.watermark_delay_seconds
        )
