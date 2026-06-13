from __future__ import annotations


class TimeSeriesError(Exception):
    pass


class InvalidTimestampError(TimeSeriesError):
    def __init__(self, timestamp: object) -> None:
        super().__init__(f"Invalid timestamp: {timestamp}")
        self.timestamp = timestamp


class InvalidValueError(TimeSeriesError):
    def __init__(self, value: object) -> None:
        super().__init__(f"Invalid value: {value}")
        self.value = value


class InvalidGranularityError(TimeSeriesError):
    def __init__(self, granularity: str) -> None:
        super().__init__(f"Invalid granularity: {granularity}")
        self.granularity = granularity


class GranularityExistsError(TimeSeriesError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Granularity '{name}' already exists")
        self.name = name


class GranularityNotFoundError(TimeSeriesError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Granularity '{name}' not found")
        self.name = name


class InvalidAggregationTypeError(TimeSeriesError):
    def __init__(self, agg_type: str) -> None:
        super().__init__(f"Invalid aggregation type: {agg_type}")
        self.agg_type = agg_type


class InvalidTimeRangeError(TimeSeriesError):
    def __init__(self, start: float, end: float) -> None:
        super().__init__(f"Invalid time range: start={start}, end={end}")
        self.start = start
        self.end = end


class InvalidWindowSizeError(TimeSeriesError):
    def __init__(self, window_seconds: int) -> None:
        super().__init__(f"Invalid window size: {window_seconds}")
        self.window_seconds = window_seconds


class OutOfOrderWriteError(TimeSeriesError):
    def __init__(self, timestamp: float, latest_timestamp: float) -> None:
        super().__init__(
            f"Out-of-order write: timestamp={timestamp} is earlier than latest={latest_timestamp}"
        )
        self.timestamp = timestamp
        self.latest_timestamp = latest_timestamp


class AggregationTypeMismatchError(TimeSeriesError):
    def __init__(self, requested: str, stored: str) -> None:
        super().__init__(
            f"Aggregation type mismatch: requested '{requested}', but data was stored with '{stored}'"
        )
        self.requested = requested
        self.stored = stored


__all__ = [
    "TimeSeriesError",
    "InvalidTimestampError",
    "InvalidValueError",
    "InvalidGranularityError",
    "GranularityExistsError",
    "GranularityNotFoundError",
    "InvalidAggregationTypeError",
    "InvalidTimeRangeError",
    "InvalidWindowSizeError",
    "OutOfOrderWriteError",
    "AggregationTypeMismatchError",
]
