from __future__ import annotations

import datetime
import time
from bisect import bisect_left, bisect_right
from typing import Iterable, Iterator, Optional

from .exceptions import (
    GranularityExistsError,
    GranularityNotFoundError,
    InvalidAggregationTypeError,
    InvalidTimeRangeError,
    OutOfOrderWriteError,
)
from .models import AggregateValue, DataPoint, Granularity, RetentionPolicy, RollupState


class AggregateTimeSeries:
    def __init__(self, granularity: Granularity) -> None:
        self._granularity = granularity
        self._data: dict[tuple[float, tuple], AggregateValue] = {}
        self._windows: list[float] = []
        self._latest_window: float = float("-inf")

    @property
    def granularity(self) -> Granularity:
        return self._granularity

    @property
    def latest_window(self) -> float:
        return self._latest_window

    def __len__(self) -> int:
        return len(self._data)

    def write_aggregate(self, aggregate: AggregateValue) -> None:
        labels_key = tuple(sorted(aggregate.labels.items()))
        key = (aggregate.timestamp, labels_key)
        self._data[key] = aggregate

        if aggregate.timestamp not in [k[0] for k in self._data.keys()]:
            pass

        if aggregate.timestamp > self._latest_window:
            self._latest_window = aggregate.timestamp

        self._rebuild_index()

    def update_rollup(
        self,
        window_start: float,
        value: float,
        labels: dict[str, str],
        rollup_states: dict[tuple[float, tuple], RollupState],
    ) -> AggregateValue:
        labels_key = tuple(sorted(labels.items()))
        key = (window_start, labels_key)

        if key not in rollup_states:
            rollup_states[key] = RollupState(window_start=window_start)

        rollup_states[key].update(value)

        aggregate = rollup_states[key].to_aggregate(labels)
        if aggregate is not None:
            self._data[key] = aggregate

            if window_start > self._latest_window:
                self._latest_window = window_start

            self._rebuild_index()
            return aggregate

        raise ValueError("Failed to create aggregate from rollup state")

    def query(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        labels: Optional[dict[str, str]] = None,
        agg_type: Optional[str] = None,
    ) -> list[AggregateValue]:
        if agg_type is not None and agg_type not in {"avg", "max", "min", "sum", "count"}:
            raise InvalidAggregationTypeError(agg_type)

        if not self._data:
            return []

        results = sorted(self._data.values(), key=lambda a: (a.timestamp, tuple(sorted(a.labels.items()))))

        if start_time is not None:
            results = [a for a in results if a.timestamp >= start_time]
        if end_time is not None:
            results = [a for a in results if a.timestamp <= end_time]

        if labels:
            results = [
                a for a in results
                if all(a.labels.get(k) == v for k, v in labels.items())
            ]

        return results

    def get_at(self, window_start: float, labels: Optional[dict[str, str]] = None) -> Optional[AggregateValue]:
        labels_key = tuple(sorted((labels or {}).items()))
        key = (window_start, labels_key)
        return self._data.get(key)

    def delete_before(self, timestamp: float) -> int:
        to_delete = [
            key for key in self._data.keys()
            if key[0] < timestamp
        ]
        deleted = len(to_delete)
        for key in to_delete:
            del self._data[key]

        if self._data:
            self._latest_window = max(k[0] for k in self._data.keys())
        else:
            self._latest_window = float("-inf")

        self._rebuild_index()
        return deleted

    def clear(self) -> None:
        self._data.clear()
        self._windows.clear()
        self._latest_window = float("-inf")

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def time_range(self) -> Optional[tuple[float, float]]:
        if not self._data:
            return None
        windows = [k[0] for k in self._data.keys()]
        return (min(windows), max(windows))

    def _rebuild_index(self) -> None:
        self._windows = sorted({k[0] for k in self._data.keys()})


class MultiResolutionStore:
    def __init__(self, name: str = "default") -> None:
        self._name = name
        self._raw_data: list[DataPoint] = []
        self._raw_timestamps: list[float] = []
        self._latest_raw_timestamp: float = float("-inf")

        self._granularities: dict[str, Granularity] = {}
        self._aggregate_series: dict[str, AggregateTimeSeries] = {}
        self._rollup_states: dict[str, dict[tuple[float, tuple], RollupState]] = {}
        self._retention_policies: dict[str, RetentionPolicy] = {}

        self.add_granularity("raw", 1, retention_seconds=None)

    @property
    def name(self) -> str:
        return self._name

    @property
    def raw_data_count(self) -> int:
        return len(self._raw_data)

    @property
    def granularities(self) -> list[str]:
        return sorted(self._granularities.keys())

    def add_granularity(
        self,
        name: str,
        window_seconds: int,
        retention_seconds: Optional[int] = None,
    ) -> Granularity:
        if name in self._granularities:
            raise GranularityExistsError(name)

        granularity = Granularity(
            name=name,
            window_seconds=window_seconds,
            retention_seconds=retention_seconds,
        )

        self._granularities[name] = granularity
        self._aggregate_series[name] = AggregateTimeSeries(granularity)
        self._rollup_states[name] = {}
        self._retention_policies[name] = RetentionPolicy(
            granularity_name=name,
            retention_seconds=retention_seconds,
        )

        return granularity

    def set_retention_policy(
        self,
        granularity_name: str,
        retention_seconds: Optional[int],
    ) -> RetentionPolicy:
        if granularity_name not in self._granularities:
            raise GranularityNotFoundError(granularity_name)

        policy = RetentionPolicy(
            granularity_name=granularity_name,
            retention_seconds=retention_seconds,
        )
        self._retention_policies[granularity_name] = policy
        self._granularities[granularity_name] = Granularity(
            name=granularity_name,
            window_seconds=self._granularities[granularity_name].window_seconds,
            retention_seconds=retention_seconds,
        )
        return policy

    def get_granularity(self, name: str) -> Granularity:
        if name not in self._granularities:
            raise GranularityNotFoundError(name)
        return self._granularities[name]

    def get_retention_policy(self, granularity_name: str) -> RetentionPolicy:
        if granularity_name not in self._retention_policies:
            raise GranularityNotFoundError(granularity_name)
        return self._retention_policies[granularity_name]

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

        if not allow_out_of_order and ts < self._latest_raw_timestamp:
            raise OutOfOrderWriteError(ts, self._latest_raw_timestamp)

        idx = bisect_left(self._raw_timestamps, ts)
        if idx < len(self._raw_timestamps) and self._raw_timestamps[idx] == ts:
            self._raw_data[idx] = point
        else:
            self._raw_data.insert(idx, point)
            self._raw_timestamps.insert(idx, ts)

        if ts > self._latest_raw_timestamp:
            self._latest_raw_timestamp = ts

        self._rollup(point)

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

    def _rollup(self, point: DataPoint) -> None:
        for name, granularity in self._granularities.items():
            if name == "raw":
                continue

            window_start = granularity.align_timestamp(point.timestamp)
            series = self._aggregate_series[name]
            states = self._rollup_states[name]

            series.update_rollup(
                window_start=window_start,
                value=point.value,
                labels=point.labels,
                rollup_states=states,
            )

    def query_raw(
        self,
        start_time: Optional[float | datetime.datetime] = None,
        end_time: Optional[float | datetime.datetime] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> list[DataPoint]:
        start_ts = self._to_timestamp(start_time) if start_time is not None else None
        end_ts = self._to_timestamp(end_time) if end_time is not None else None

        if start_ts is not None and end_ts is not None and start_ts > end_ts:
            raise InvalidTimeRangeError(start_ts, end_ts)

        if not self._raw_data:
            return []

        left_idx = 0
        if start_ts is not None:
            left_idx = bisect_left(self._raw_timestamps, start_ts)

        right_idx = len(self._raw_data)
        if end_ts is not None:
            right_idx = bisect_right(self._raw_timestamps, end_ts)

        results = self._raw_data[left_idx:right_idx]

        if labels:
            results = [
                p for p in results
                if all(p.labels.get(k) == v for k, v in labels.items())
            ]

        return results

    def query_aggregated(
        self,
        granularity_name: str,
        start_time: Optional[float | datetime.datetime] = None,
        end_time: Optional[float | datetime.datetime] = None,
        labels: Optional[dict[str, str]] = None,
        agg_type: Optional[str] = None,
    ) -> list[AggregateValue]:
        if granularity_name not in self._aggregate_series:
            raise GranularityNotFoundError(granularity_name)

        if granularity_name == "raw":
            raise ValueError(
                "query_aggregated is for aggregated granularities. "
                "Use query_raw for raw data."
            )

        start_ts = self._to_timestamp(start_time) if start_time is not None else None
        end_ts = self._to_timestamp(end_time) if end_time is not None else None

        if start_ts is not None and end_ts is not None and start_ts > end_ts:
            raise InvalidTimeRangeError(start_ts, end_ts)

        granularity = self._granularities[granularity_name]
        if start_ts is not None:
            start_ts = granularity.align_timestamp(start_ts)
        if end_ts is not None:
            end_ts = granularity.align_timestamp(end_ts)

        series = self._aggregate_series[granularity_name]
        return series.query(
            start_time=start_ts,
            end_time=end_ts,
            labels=labels,
            agg_type=agg_type,
        )

    def downsample_raw(
        self,
        window_seconds: int,
        agg_type: str = "avg",
        start_time: Optional[float | datetime.datetime] = None,
        end_time: Optional[float | datetime.datetime] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> list[AggregateValue]:
        from .aggregator import aggregate_points

        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if agg_type not in {"avg", "max", "min", "sum", "count"}:
            raise InvalidAggregationTypeError(agg_type)

        points = self.query_raw(
            start_time=start_time, end_time=end_time, labels=labels
        )

        if not points:
            return []

        return aggregate_points(points, window_seconds, agg_type)

    def clean_expired(self, current_time: Optional[float] = None) -> dict[str, int]:
        if current_time is None:
            current_time = time.time()

        results: dict[str, int] = {}

        for name, policy in self._retention_policies.items():
            if policy.retention_seconds is None:
                results[name] = 0
                continue

            cutoff = current_time - policy.retention_seconds
            granularity = self._granularities[name]

            if name == "raw":
                deleted = self._delete_raw_before(cutoff)
            else:
                aligned_cutoff = granularity.align_timestamp(cutoff)
                series = self._aggregate_series[name]
                deleted = series.delete_before(aligned_cutoff)

                self._clean_rollup_states(name, aligned_cutoff)

            results[name] = deleted

        return results

    def _delete_raw_before(self, timestamp: float) -> int:
        idx = bisect_left(self._raw_timestamps, timestamp)
        if idx == 0:
            return 0

        deleted = idx
        self._raw_data = self._raw_data[idx:]
        self._raw_timestamps = self._raw_timestamps[idx:]

        if self._raw_data:
            self._latest_raw_timestamp = self._raw_timestamps[-1]
        else:
            self._latest_raw_timestamp = float("-inf")

        return deleted

    def _clean_rollup_states(self, granularity_name: str, cutoff: float) -> None:
        states = self._rollup_states.get(granularity_name, {})
        to_delete = [key for key in states.keys() if key[0] < cutoff]
        for key in to_delete:
            del states[key]

    def force_clean_all(self) -> dict[str, int]:
        results: dict[str, int] = {}

        results["raw"] = len(self._raw_data)
        self._raw_data.clear()
        self._raw_timestamps.clear()
        self._latest_raw_timestamp = float("-inf")

        for name, series in self._aggregate_series.items():
            if name == "raw":
                continue
            results[name] = len(series)
            series.clear()
            self._rollup_states[name].clear()

        return results

    def get_raw_at(self, timestamp: float | datetime.datetime) -> Optional[DataPoint]:
        ts = self._to_timestamp(timestamp)
        idx = bisect_left(self._raw_timestamps, ts)
        if idx < len(self._raw_timestamps) and self._raw_timestamps[idx] == ts:
            return self._raw_data[idx]
        return None

    def get_aggregated_at(
        self,
        granularity_name: str,
        window_start: float | datetime.datetime,
        labels: Optional[dict[str, str]] = None,
    ) -> Optional[AggregateValue]:
        if granularity_name not in self._aggregate_series:
            raise GranularityNotFoundError(granularity_name)

        if granularity_name == "raw":
            raise ValueError(
                "get_aggregated_at is for aggregated granularities. "
                "Use get_raw_at for raw data."
            )

        ts = self._to_timestamp(window_start)
        series = self._aggregate_series[granularity_name]
        return series.get_at(ts, labels)

    def get_rollup_state(
        self,
        granularity_name: str,
        window_start: float | datetime.datetime,
        labels: Optional[dict[str, str]] = None,
    ) -> Optional[RollupState]:
        if granularity_name not in self._rollup_states:
            raise GranularityNotFoundError(granularity_name)

        ts = self._to_timestamp(window_start)
        labels_key = tuple(sorted((labels or {}).items()))
        key = (ts, labels_key)
        return self._rollup_states[granularity_name].get(key)

    def is_empty(self, granularity_name: Optional[str] = None) -> bool:
        if granularity_name is None:
            return len(self._raw_data) == 0 and all(
                series.is_empty()
                for name, series in self._aggregate_series.items()
                if name != "raw"
            )

        if granularity_name == "raw":
            return len(self._raw_data) == 0

        if granularity_name not in self._aggregate_series:
            raise GranularityNotFoundError(granularity_name)

        return self._aggregate_series[granularity_name].is_empty()

    def time_range(
        self, granularity_name: str = "raw"
    ) -> Optional[tuple[float, float]]:
        if granularity_name == "raw":
            if not self._raw_data:
                return None
            return (self._raw_timestamps[0], self._raw_timestamps[-1])

        if granularity_name not in self._aggregate_series:
            raise GranularityNotFoundError(granularity_name)

        return self._aggregate_series[granularity_name].time_range()

    def clear(self) -> None:
        self._raw_data.clear()
        self._raw_timestamps.clear()
        self._latest_raw_timestamp = float("-inf")

        for series in self._aggregate_series.values():
            series.clear()

        for states in self._rollup_states.values():
            states.clear()

    @staticmethod
    def _to_timestamp(value: float | datetime.datetime) -> float:
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.timestamp()
        return float(value)


__all__ = [
    "AggregateTimeSeries",
    "MultiResolutionStore",
]
