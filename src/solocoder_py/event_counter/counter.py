from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from .exceptions import (
    InvalidGranularityError,
    InvalidTimeRangeError,
)
from .models import (
    CountResult,
    Event,
    Granularity,
    GranularityConfig,
    TimeWindow,
    WindowStore,
    validate_time_range,
)


class EventCounter:
    def __init__(
        self,
        granularity_configs: Optional[dict[Granularity, GranularityConfig]] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        if granularity_configs is None:
            granularity_configs = {
                g: GranularityConfig.default(g) for g in Granularity
            }

        for g in Granularity:
            if g not in granularity_configs:
                raise InvalidGranularityError(
                    f"Missing configuration for granularity: {g}"
                )

        self._configs = granularity_configs
        self._store = WindowStore()
        self._lock = threading.RLock()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def configs(self) -> dict[Granularity, GranularityConfig]:
        return dict(self._configs)

    def record(self, event: Event) -> None:
        with self._lock:
            self._record_one(event)
            self._maybe_cleanup()

    def record_many(self, events: list[Event]) -> None:
        with self._lock:
            for event in events:
                self._record_one(event)
            self._maybe_cleanup()

    def _record_one(self, event: Event) -> None:
        timestamp = event.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        for granularity in Granularity:
            window = TimeWindow.from_timestamp(timestamp, granularity)
            self._store.increment(window, event.count)

    def query(
        self,
        start: datetime,
        end: datetime,
        granularity: Granularity,
    ) -> list[CountResult]:
        validate_time_range(start, end)

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        with self._lock:
            self._maybe_cleanup()
            results: list[CountResult] = []
            current = TimeWindow.from_timestamp(start, granularity)

            while current.start < end:
                result = self._resolve_window(current)
                results.append(result)
                current = current.next_window()

            return results

    def query_single(
        self,
        timestamp: datetime,
        granularity: Granularity,
    ) -> CountResult:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        window = TimeWindow.from_timestamp(timestamp, granularity)
        with self._lock:
            self._maybe_cleanup()
            return self._resolve_window(window)

    def get_count(
        self,
        timestamp: datetime,
        granularity: Granularity,
    ) -> int:
        return self.query_single(timestamp, granularity).count

    def _resolve_window(self, target_window: TimeWindow) -> CountResult:
        direct_count = self._store.get_count(target_window)
        if direct_count is not None:
            return CountResult(
                window=target_window,
                count=direct_count,
                is_estimated=False,
                source_granularity=target_window.granularity,
            )

        finer_result = self._try_resolve_from_finer(target_window)
        if finer_result is not None:
            return finer_result

        coarser_result = self._try_resolve_from_coarser(target_window)
        if coarser_result is not None:
            return coarser_result

        return CountResult(
            window=target_window,
            count=0,
            is_estimated=False,
            source_granularity=None,
        )

    def _try_resolve_from_finer(self, target_window: TimeWindow) -> Optional[CountResult]:
        for finer_granularity in Granularity:
            if not finer_granularity.is_finer_than(target_window.granularity):
                continue

            if not self._is_finer_data_complete(target_window, finer_granularity):
                continue

            total = 0
            has_any_finer = False

            finer_start = TimeWindow.from_timestamp(
                target_window.start, finer_granularity
            )
            finer_end_ts = target_window.end.timestamp()

            current_finer = finer_start
            while current_finer.start.timestamp() < finer_end_ts:
                finer_count = self._store.get_count(current_finer)
                if finer_count is not None:
                    total += finer_count
                    has_any_finer = True
                current_finer = current_finer.next_window()

            if has_any_finer:
                return CountResult(
                    window=target_window,
                    count=total,
                    is_estimated=False,
                    source_granularity=finer_granularity,
                )

        return None

    def _is_finer_data_complete(
        self, target_window: TimeWindow, finer_granularity: Granularity
    ) -> bool:
        config = self._configs[finer_granularity]
        retention_cutoff = self._clock() - config.retention

        if target_window.start >= retention_cutoff:
            return True

        if target_window.end <= retention_cutoff:
            return False

        overlap_duration = target_window.end - retention_cutoff
        total_duration = target_window.end - target_window.start
        overlap_ratio = overlap_duration.total_seconds() / total_duration.total_seconds()

        return overlap_ratio >= 0.5

    def _try_resolve_from_coarser(self, target_window: TimeWindow) -> Optional[CountResult]:
        for coarser_granularity in Granularity:
            if not coarser_granularity.is_coarser_than(target_window.granularity):
                continue

            coarser_window = target_window.to_coarser(coarser_granularity)
            coarser_count = self._store.get_count(coarser_window)

            if coarser_count is not None:
                num_finer_in_coarser = int(
                    coarser_granularity.duration.total_seconds()
                    / target_window.granularity.duration.total_seconds()
                )
                if num_finer_in_coarser > 0:
                    base = coarser_count // num_finer_in_coarser
                    remainder = coarser_count % num_finer_in_coarser
                    has_data = self._target_window_has_finer_data(target_window)

                    if base > 0:
                        estimated = base + (1 if remainder > 0 and has_data else 0)
                        return CountResult(
                            window=target_window,
                            count=estimated,
                            is_estimated=True,
                            source_granularity=coarser_granularity,
                        )
                    elif remainder > 0 and has_data:
                        return CountResult(
                            window=target_window,
                            count=1,
                            is_estimated=True,
                            source_granularity=coarser_granularity,
                        )

        return None

    def _target_window_has_finer_data(self, target_window: TimeWindow) -> bool:
        for finer_granularity in Granularity:
            if not finer_granularity.is_finer_than(target_window.granularity):
                continue

            finer_start = TimeWindow.from_timestamp(
                target_window.start, finer_granularity
            )
            finer_end_ts = target_window.end.timestamp()

            current_finer = finer_start
            while current_finer.start.timestamp() < finer_end_ts:
                if self._store.get_count(current_finer) is not None:
                    return True
                current_finer = current_finer.next_window()

        return False

    def cleanup(self, reference_time: Optional[datetime] = None) -> dict[Granularity, int]:
        with self._lock:
            if reference_time is None:
                reference_time = self._clock()
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)

            removed: dict[Granularity, int] = {}
            for granularity, config in self._configs.items():
                cutoff = reference_time - config.retention
                cutoff_window = TimeWindow.from_timestamp(cutoff, granularity)
                count = self._store.remove_windows_before(
                    granularity, cutoff_window.start
                )
                removed[granularity] = count

            return removed

    def _maybe_cleanup(self) -> None:
        self.cleanup()

    def count_windows(self, granularity: Granularity) -> int:
        with self._lock:
            return self._store.count_windows(granularity)

    def clear(self, granularity: Optional[Granularity] = None) -> None:
        with self._lock:
            self._store.clear(granularity)
