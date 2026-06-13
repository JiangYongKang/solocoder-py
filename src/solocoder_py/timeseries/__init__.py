from __future__ import annotations

from .aggregator import (
    aggregate_points,
    align_timestamp,
    compute_aggregation,
)
from .exceptions import (
    AggregationTypeMismatchError,
    GranularityExistsError,
    GranularityNotFoundError,
    InvalidAggregationTypeError,
    InvalidGranularityError,
    InvalidTimeRangeError,
    InvalidTimestampError,
    InvalidValueError,
    InvalidWindowSizeError,
    OutOfOrderWriteError,
    TimeSeriesError,
)
from .models import (
    AggregateValue,
    DataPoint,
    Granularity,
    QueryOptions,
    RetentionPolicy,
    RollupState,
)
from .store import AggregateTimeSeries, MultiResolutionStore
from .timeseries import TimeSeries

__all__ = [
    "TimeSeries",
    "MultiResolutionStore",
    "AggregateTimeSeries",
    "DataPoint",
    "AggregateValue",
    "Granularity",
    "RetentionPolicy",
    "RollupState",
    "QueryOptions",
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
    "aggregate_points",
    "align_timestamp",
    "compute_aggregation",
]

__version__ = "0.1.0"
