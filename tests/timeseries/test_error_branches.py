from __future__ import annotations

import datetime

import pytest

from solocoder_py.timeseries import (
    AggregateValue,
    DataPoint,
    Granularity,
    GranularityExistsError,
    GranularityNotFoundError,
    InvalidAggregationTypeError,
    InvalidTimeRangeError,
    InvalidWindowSizeError,
    MultiResolutionStore,
    OutOfOrderWriteError,
    QueryOptions,
    RetentionPolicy,
    RollupState,
    TimeSeries,
    aggregate_points,
    compute_aggregation,
)
from solocoder_py.timeseries.exceptions import AggregationTypeMismatchError

from .conftest import make_multi_resolution_store, make_timeseries


class TestQueryNoData:
    def test_query_time_range_no_data(self):
        ts = make_timeseries()
        for i in range(10):
            ts.write(1000.0 + i, float(i))

        results = ts.query(2000.0, 3000.0)
        assert results == []

    def test_query_raw_no_data_in_range(self):
        store = make_multi_resolution_store()
        for i in range(10):
            store.write(1704067200.0 + i, float(i))

        results = store.query_raw(1704070000.0, 1704080000.0)
        assert results == []

    def test_query_aggregated_no_data_in_range(self):
        store = make_multi_resolution_store()
        for i in range(10):
            store.write(1704067200.0 + i, float(i))

        results = store.query_aggregated("5min", 1704070000.0, 1704080000.0)
        assert results == []

    def test_downsample_no_data_in_range(self):
        ts = make_timeseries()
        for i in range(10):
            ts.write(1000.0 + i, float(i))

        result = ts.downsample(
            window_seconds=60,
            agg_type="avg",
            start_time=2000.0,
            end_time=3000.0,
        )
        assert result == []


class TestDownsamplingWindowErrors:
    def test_downsample_window_larger_than_data_span_returns_single_agg(self):
        ts = make_timeseries()
        base_time = 1000.0
        for i in range(10):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=86400, agg_type="avg")
        assert len(result) == 1
        assert result[0].count == 10

    def test_downsample_negative_window_size(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        with pytest.raises(InvalidWindowSizeError):
            ts.downsample(window_seconds=-1, agg_type="avg")

    def test_downsample_zero_window_size(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        with pytest.raises(InvalidWindowSizeError):
            ts.downsample(window_seconds=0, agg_type="avg")


class TestOutOfOrderWrite:
    def test_out_of_order_write_raises_error(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)
        ts.write(1001.0, 2.0)

        with pytest.raises(OutOfOrderWriteError) as exc_info:
            ts.write(999.0, 3.0)

        assert exc_info.value.timestamp == 999.0
        assert exc_info.value.latest_timestamp == 1001.0

    def test_out_of_order_write_allowed_with_flag(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)
        ts.write(1001.0, 2.0)

        point = ts.write(999.0, 3.0, allow_out_of_order=True)
        assert point.timestamp == 999.0
        assert point.value == 3.0

        results = ts.query()
        assert len(results) == 3
        assert [p.timestamp for p in results] == [999.0, 1000.0, 1001.0]

    def test_store_out_of_order_write_raises_error(self):
        store = make_multi_resolution_store()
        store.write(1000.0, 1.0)
        store.write(1001.0, 2.0)

        with pytest.raises(OutOfOrderWriteError):
            store.write(999.0, 3.0)

    def test_store_out_of_order_write_allowed_with_flag(self):
        store = make_multi_resolution_store()
        store.write(1000.0, 1.0)
        store.write(1001.0, 2.0)

        point = store.write(999.0, 3.0, allow_out_of_order=True)
        assert point.timestamp == 999.0
        assert point.value == 3.0

        results = store.query_raw()
        assert len(results) == 3

    def test_same_timestamp_is_not_out_of_order(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        ts.write(1000.0, 2.0)
        assert len(ts) == 1
        assert ts.get_at(1000.0).value == 2.0


class TestRetentionPolicyAllDataCleared:
    def test_all_data_cleared_after_retention(self):
        store = MultiResolutionStore()
        store.set_retention_policy("raw", retention_seconds=3600)
        store.add_granularity("5min", 300, retention_seconds=3600)

        current_time = 1704067200.0

        store.write(current_time - 7201, 2.0)
        store.write(current_time - 7200, 1.0)

        deleted = store.clean_expired(current_time=current_time)

        raw_after = store.query_raw()
        assert raw_after == []

        agg_after = store.query_aggregated("5min")
        assert agg_after == []

        assert store.is_empty("raw") is True
        assert store.is_empty("5min") is True

    def test_query_after_all_data_cleared(self):
        store = MultiResolutionStore()
        store.set_retention_policy("raw", retention_seconds=3600)
        store.add_granularity("hourly", 3600, retention_seconds=3600)

        current_time = 1704067200.0
        store.write(current_time - 7200, 1.0)

        store.clean_expired(current_time=current_time)

        raw_result = store.query_raw()
        assert raw_result == []

        agg_result = store.query_aggregated("hourly")
        assert agg_result == []

        time_range = store.time_range("raw")
        assert time_range is None

        time_range_agg = store.time_range("hourly")
        assert time_range_agg is None


class TestAggregationTypeErrors:
    def test_invalid_aggregation_type_in_downsample(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        with pytest.raises(InvalidAggregationTypeError) as exc_info:
            ts.downsample(window_seconds=60, agg_type="invalid")

        assert exc_info.value.agg_type == "invalid"

    def test_invalid_aggregation_type_in_compute(self):
        with pytest.raises(InvalidAggregationTypeError):
            compute_aggregation([1.0, 2.0, 3.0], "invalid")

    def test_invalid_aggregation_type_in_aggregate_points(self):
        points = [DataPoint(timestamp=1000.0, value=1.0)]
        with pytest.raises(InvalidAggregationTypeError):
            aggregate_points(points, 60, "invalid")

    def test_aggregate_value_get_invalid_type(self):
        agg = AggregateValue(
            timestamp=1000.0, avg=1.0, max=2.0, min=0.0, sum=3.0, count=3
        )
        with pytest.raises(ValueError):
            agg.get("invalid")

    def test_query_options_invalid_agg_type(self):
        with pytest.raises(ValueError):
            QueryOptions(agg_type="invalid")


class TestTimeRangeErrors:
    def test_invalid_time_range_start_greater_than_end(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        with pytest.raises(InvalidTimeRangeError) as exc_info:
            ts.query(2000.0, 1000.0)

        assert exc_info.value.start == 2000.0
        assert exc_info.value.end == 1000.0

    def test_store_query_raw_invalid_range(self):
        store = make_multi_resolution_store()
        store.write(1000.0, 1.0)

        with pytest.raises(InvalidTimeRangeError):
            store.query_raw(2000.0, 1000.0)

    def test_store_query_aggregated_invalid_range(self):
        store = make_multi_resolution_store()
        store.write(1000.0, 1.0)

        with pytest.raises(InvalidTimeRangeError):
            store.query_aggregated("5min", 2000.0, 1000.0)

    def test_delete_range_invalid_time_range(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0)

        with pytest.raises(InvalidTimeRangeError):
            ts.delete_range(2000.0, 1000.0)


class TestGranularityErrors:
    def test_add_duplicate_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityExistsError) as exc_info:
            store.add_granularity("5min", 300)
        assert exc_info.value.name == "5min"

    def test_get_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError) as exc_info:
            store.get_granularity("nonexistent")
        assert exc_info.value.name == "nonexistent"

    def test_query_aggregated_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.query_aggregated("nonexistent")

    def test_query_aggregated_raw_raises_error(self):
        store = make_multi_resolution_store()
        with pytest.raises(ValueError):
            store.query_aggregated("raw")

    def test_get_aggregated_at_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.get_aggregated_at("nonexistent", 1000.0)

    def test_get_aggregated_at_raw_raises_error(self):
        store = make_multi_resolution_store()
        with pytest.raises(ValueError):
            store.get_aggregated_at("raw", 1000.0)

    def test_get_rollup_state_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.get_rollup_state("nonexistent", 1000.0)

    def test_is_empty_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.is_empty("nonexistent")

    def test_time_range_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.time_range("nonexistent")

    def test_set_retention_policy_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.set_retention_policy("nonexistent", 3600)

    def test_get_retention_policy_nonexistent_granularity(self):
        store = make_multi_resolution_store()
        with pytest.raises(GranularityNotFoundError):
            store.get_retention_policy("nonexistent")


class TestDataPointValidationErrors:
    def test_datapoint_invalid_timestamp_type(self):
        with pytest.raises(ValueError):
            DataPoint(timestamp="invalid", value=1.0)

    def test_datapoint_invalid_value_type(self):
        with pytest.raises(ValueError):
            DataPoint(timestamp=1000.0, value="invalid")

    def test_datapoint_invalid_labels_type(self):
        with pytest.raises(ValueError):
            DataPoint(timestamp=1000.0, value=1.0, labels="invalid")

    def test_datapoint_invalid_label_key_type(self):
        with pytest.raises(ValueError):
            DataPoint(timestamp=1000.0, value=1.0, labels={123: "value"})

    def test_datapoint_invalid_label_value_type(self):
        with pytest.raises(ValueError):
            DataPoint(timestamp=1000.0, value=1.0, labels={"key": 123})


class TestGranularityModelErrors:
    def test_granularity_empty_name(self):
        with pytest.raises(ValueError):
            Granularity(name="", window_seconds=60)

    def test_granularity_negative_window(self):
        with pytest.raises(ValueError):
            Granularity(name="test", window_seconds=-1)

    def test_granularity_zero_window(self):
        with pytest.raises(ValueError):
            Granularity(name="test", window_seconds=0)

    def test_granularity_negative_retention(self):
        with pytest.raises(ValueError):
            Granularity(name="test", window_seconds=60, retention_seconds=-1)


class TestRetentionPolicyModelErrors:
    def test_retention_policy_empty_name(self):
        with pytest.raises(ValueError):
            RetentionPolicy(granularity_name="", retention_seconds=3600)

    def test_retention_policy_negative_retention(self):
        with pytest.raises(ValueError):
            RetentionPolicy(granularity_name="test", retention_seconds=-1)


class TestAggregateValueModelErrors:
    def test_aggregate_value_negative_count(self):
        with pytest.raises(ValueError):
            AggregateValue(
                timestamp=1000.0,
                avg=1.0,
                max=2.0,
                min=0.0,
                sum=3.0,
                count=-1,
            )


class TestRollupStateErrors:
    def test_empty_rollup_state_returns_none(self):
        state = RollupState(window_start=1000.0)
        assert state.to_aggregate() is None


class TestAggregationTypeMismatch:
    def test_aggregated_data_stores_all_types(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        store.write(base_time, 10.0)
        store.write(base_time + 60, 20.0)
        store.write(base_time + 120, 30.0)

        result = store.query_aggregated("5min")
        assert len(result) == 1

        agg = result[0]
        assert agg.avg == 20.0
        assert agg.max == 30.0
        assert agg.min == 10.0
        assert agg.sum == 60.0
        assert agg.count == 3

        assert agg.get("avg") == 20.0
        assert agg.get("max") == 30.0
        assert agg.get("min") == 10.0
        assert agg.get("sum") == 60.0
        assert agg.get("count") == 3.0

    def test_downsample_agg_type_mismatch_returns_all(self):
        ts = make_timeseries()
        for i in range(5):
            ts.write(1000.0 + i, float(i))

        result_avg = ts.downsample(window_seconds=60, agg_type="avg")
        result_sum = ts.downsample(window_seconds=60, agg_type="sum")

        assert len(result_avg) == 1
        assert len(result_sum) == 1

        assert result_avg[0].avg == result_sum[0].avg
        assert result_avg[0].sum == result_sum[0].sum

    def test_query_aggregated_returns_all_aggregates(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1

        agg = result[0]
        assert agg.avg == 30.0
        assert agg.max == 50.0
        assert agg.min == 10.0
        assert agg.sum == 150.0
        assert agg.count == 5


class TestEdgeErrorCases:
    def test_write_nan_value(self):
        ts = make_timeseries()
        import math

        point = ts.write(1000.0, float("nan"))
        assert math.isnan(point.value)

        result = ts.query(1000.0, 1000.0)
        assert len(result) == 1
        assert math.isnan(result[0].value)

    def test_write_infinity_value(self):
        ts = make_timeseries()
        ts.write(1000.0, float("inf"))
        ts.write(1001.0, float("-inf"))

        result = ts.query()
        assert len(result) == 2
        assert result[0].value == float("inf")
        assert result[1].value == float("-inf")

    def test_downsample_with_nan_values(self):
        ts = make_timeseries()
        import math

        ts.write(1000.0, 10.0)
        ts.write(1001.0, float("nan"))
        ts.write(1002.0, 30.0)

        result = ts.downsample(window_seconds=60, agg_type="sum")
        assert len(result) == 1
        assert math.isnan(result[0].sum)

    def test_very_large_timestamp(self):
        ts = make_timeseries()
        large_ts = 1e18
        ts.write(large_ts, 42.0)

        result = ts.query(large_ts, large_ts)
        assert len(result) == 1
        assert result[0].timestamp == large_ts

    def test_very_small_timestamp(self):
        ts = make_timeseries()
        small_ts = -1e18
        ts.write(small_ts, 42.0, allow_out_of_order=True)

        result = ts.query(small_ts, small_ts)
        assert len(result) == 1
        assert result[0].timestamp == small_ts
