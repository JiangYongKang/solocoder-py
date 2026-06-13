from __future__ import annotations

import datetime
from bisect import bisect_left, bisect_right
from typing import Iterable, Iterator, Optional

from .aggregator import aggregate_points, align_timestamp
from .exceptions import (
    InvalidAggregationTypeError,
    InvalidTimeRangeError,
    InvalidWindowSizeError,
    OutOfOrderWriteError,
)
from .models import AggregateValue, DataPoint, QueryOptions


class TimeSeries:
    def __init__(self, name: str = "default") -> None:
        self._name = name
        self._data: list[DataPoint] = []
        self._timestamps: list[float] = []
        self._latest_timestamp: float = float("-inf")

    @property
    def name(self) -> str:
        return self._name

    @property
    def latest_timestamp(self) -> float:
        return self._latest_timestamp

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[DataPoint]:
        return iter(self._data)

    def __contains__(self, timestamp: float) -> bool:
        idx = bisect_left(self._timestamps, timestamp)
        return idx < len(self._timestamps) and self._timestamps[idx] == timestamp

    def write(
        self,
        timestamp: float | datetime.datetime,
        value: float,
        labels: Optional[dict[str, str]] = None,
        allow_out_of_order: bool = False,
    ) -> DataPoint:
        if isinstance(timestamp, datetime.datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            ts = timestamp.timestamp()
        else:
            ts = float(timestamp)

        point = DataPoint(timestamp=ts, value=float(value), labels=labels or {})

        if not allow_out_of_order and ts < self._latest_timestamp:
            raise OutOfOrderWriteError(ts, self._latest_timestamp)

        idx = bisect_left(self._timestamps, ts)
        if idx < len(self._timestamps) and self._timestamps[idx] == ts:
            self._data[idx] = point
        else:
            self._data.insert(idx, point)
            self._timestamps.insert(idx, ts)

        if ts > self._latest_timestamp:
            self._latest_timestamp = ts

        return point

    def write_many(
        self,
        points: Iterable[tuple[float | datetime.datetime, float]]
        | Iterable[DataPoint],
        allow_out_of_order: bool = False,
    ) -> list[DataPoint]:
        result: list[DataPoint] = []
        for item in points:
            if isinstance(item, DataPoint):
                point = self.write(
                    timestamp=item.timestamp,
                    value=item.value,
                    labels=item.labels,
                    allow_out_of_order=allow_out_of_order,
                )
            else:
                ts, value = item
                point = self.write(
                    timestamp=ts,
                    value=value,
                    allow_out_of_order=allow_out_of_order,
                )
            result.append(point)
        return result

    def query(
        self,
        start_time: Optional[float | datetime.datetime] = None,
        end_time: Optional[float | datetime.datetime] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> list[DataPoint]:
        start_ts = self._to_timestamp(start_time) if start_time is not None else None
        end_ts = self._to_timestamp(end_time) if end_time is not None else None

        if start_ts is not None and end_ts is not None and start_ts > end_ts:
            raise InvalidTimeRangeError(start_ts, end_ts)

        if not self._data:
            return []

        left_idx = 0
        if start_ts is not None:
            left_idx = bisect_left(self._timestamps, start_ts)

        right_idx = len(self._data)
        if end_ts is not None:
            right_idx = bisect_right(self._timestamps, end_ts)

        results = self._data[left_idx:right_idx]

        if labels:
            results = [
                p for p in results if all(p.labels.get(k) == v for k, v in labels.items())
            ]

        return results

    def query_with_options(self, options: QueryOptions) -> list[DataPoint]:
        return self.query(
            start_time=options.start_time,
            end_time=options.end_time,
            labels=options.labels,
        )

    def downsample(
        self,
        window_seconds: int,
        agg_type: str = "avg",
        start_time: Optional[float | datetime.datetime] = None,
        end_time: Optional[float | datetime.datetime] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> list[AggregateValue]:
        if window_seconds <= 0:
            raise InvalidWindowSizeError(window_seconds)
        if agg_type not in {"avg", "max", "min", "sum", "count"}:
            raise InvalidAggregationTypeError(agg_type)

        points = self.query(start_time=start_time, end_time=end_time, labels=labels)

        if not points:
            return []

        aggregates = aggregate_points(points, window_seconds, agg_type)

        if start_time is not None or end_time is not None:
            start_ts = self._to_timestamp(start_time) if start_time is not None else None
            end_ts = self._to_timestamp(end_time) if end_time is not None else None

            if start_ts is not None:
                aligned_start = align_timestamp(start_ts, window_seconds)
                aggregates = [a for a in aggregates if a.timestamp >= aligned_start]
            if end_ts is not None:
                aligned_end = align_timestamp(end_ts, window_seconds)
                aggregates = [a for a in aggregates if a.timestamp <= aligned_end]

        return aggregates

    def get_first(self) -> Optional[DataPoint]:
        return self._data[0] if self._data else None

    def get_last(self) -> Optional[DataPoint]:
        return self._data[-1] if self._data else None

    def get_at(self, timestamp: float | datetime.datetime) -> Optional[DataPoint]:
        ts = self._to_timestamp(timestamp)
        idx = bisect_left(self._timestamps, ts)
        if idx < len(self._timestamps) and self._timestamps[idx] == ts:
            return self._data[idx]
        return None

    def delete_before(self, timestamp: float | datetime.datetime) -> int:
        ts = self._to_timestamp(timestamp)
        idx = bisect_left(self._timestamps, ts)
        if idx == 0:
            return 0

        deleted = idx
        self._data = self._data[idx:]
        self._timestamps = self._timestamps[idx:]

        if self._data:
            self._latest_timestamp = self._timestamps[-1]
        else:
            self._latest_timestamp = float("-inf")

        return deleted

    def delete_range(
        self,
        start_time: float | datetime.datetime,
        end_time: float | datetime.datetime,
    ) -> int:
        start_ts = self._to_timestamp(start_time)
        end_ts = self._to_timestamp(end_time)

        if start_ts > end_ts:
            raise InvalidTimeRangeError(start_ts, end_ts)

        left_idx = bisect_left(self._timestamps, start_ts)
        right_idx = bisect_right(self._timestamps, end_ts)

        if left_idx >= right_idx:
            return 0

        deleted = right_idx - left_idx
        self._data = self._data[:left_idx] + self._data[right_idx:]
        self._timestamps = self._timestamps[:left_idx] + self._timestamps[right_idx:]

        if self._data:
            self._latest_timestamp = self._timestamps[-1]
        else:
            self._latest_timestamp = float("-inf")

        return deleted

    def clear(self) -> None:
        self._data.clear()
        self._timestamps.clear()
        self._latest_timestamp = float("-inf")

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def time_range(self) -> Optional[tuple[float, float]]:
        if not self._data:
            return None
        return (self._timestamps[0], self._timestamps[-1])

    def values(self) -> list[float]:
        return [p.value for p in self._data]

    def timestamps(self) -> list[float]:
        return list(self._timestamps)

    @staticmethod
    def _to_timestamp(value: float | datetime.datetime) -> float:
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.timestamp()
        return float(value)


__all__ = [
    "TimeSeries",
]
