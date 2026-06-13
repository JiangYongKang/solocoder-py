from __future__ import annotations

import datetime

import pytest

from solocoder_py.timeseries import (
    AggregateValue,
    DataPoint,
    Granularity,
    MultiResolutionStore,
    RetentionPolicy,
    RollupState,
    TimeSeries,
)

from .conftest import make_multi_resolution_store, make_timeseries


class TestEmptyTimeSeries:
    def test_query_empty_series(self):
        ts = make_timeseries()
        results = ts.query()
        assert results == []

    def test_query_empty_series_with_time_range(self):
        ts = make_timeseries()
        results = ts.query(1000.0, 2000.0)
        assert results == []

    def test_downsample_empty_series(self):
        ts = make_timeseries()
        result = ts.downsample(window_seconds=60, agg_type="avg")
        assert result == []

    def test_get_first_last_empty(self):
        ts = make_timeseries()
        assert ts.get_first() is None
        assert ts.get_last() is None

    def test_is_empty(self):
        ts = make_timeseries()
        assert ts.is_empty() is True

        ts.write(1000.0, 1.0)
        assert ts.is_empty() is False

    def test_len_empty(self):
        ts = make_timeseries()
        assert len(ts) == 0

    def test_time_range_empty(self):
        ts = make_timeseries()
        assert ts.time_range() is None


class TestSingleDataPoint:
    def test_single_point_aggregation(self):
        ts = make_timeseries()
        ts.write(1000.0, 42.0)

        result = ts.downsample(window_seconds=60, agg_type="avg")
        assert len(result) == 1
        assert result[0].avg == 42.0
        assert result[0].max == 42.0
        assert result[0].min == 42.0
        assert result[0].sum == 42.0
        assert result[0].count == 1

    def test_single_point_query(self):
        ts = make_timeseries()
        ts.write(1000.0, 42.0)

        results = ts.query(999.0, 1001.0)
        assert len(results) == 1
        assert results[0].value == 42.0

    def test_single_point_rollup(self):
        store = make_multi_resolution_store()
        store.write(1704067200.0, 42.0)

        for g in ["5min", "hourly", "daily"]:
            result = store.query_aggregated(g)
            assert len(result) == 1
            assert result[0].count == 1
            assert result[0].avg == 42.0


class TestSingleWindowAggregation:
    def test_window_with_one_point(self):
        ts = make_timeseries()
        base_time = 1000.0

        ts.write(base_time, 10.0)
        for i in range(1, 10):
            ts.write(base_time + 120 + i, float(i))

        result = ts.downsample(window_seconds=60, agg_type="sum")

        window_sums = {}
        for agg in result:
            window_sums[agg.timestamp] = agg.sum

        first_window = int(base_time / 60) * 60
        assert window_sums.get(first_window) == 10.0

    def test_window_boundary_exact(self):
        ts = make_timeseries()
        window_size = 60

        ts.write(0.0, 1.0)
        ts.write(59.999, 2.0)
        ts.write(60.0, 3.0)
        ts.write(119.999, 4.0)
        ts.write(120.0, 5.0)

        result = ts.downsample(window_seconds=window_size, agg_type="sum")
        assert len(result) == 3
        assert result[0].timestamp == 0.0
        assert result[0].sum == 3.0
        assert result[1].timestamp == 60.0
        assert result[1].sum == 7.0
        assert result[2].timestamp == 120.0
        assert result[2].sum == 5.0

    def test_exact_window_boundary_timestamp(self):
        granularity = Granularity(name="5min", window_seconds=300)

        ts = 1704067200.0
        aligned = granularity.align_timestamp(ts)
        assert aligned == ts

        ts = 1704067201.0
        aligned = granularity.align_timestamp(ts)
        assert aligned == 1704067200.0

        ts = 1704067499.0
        aligned = granularity.align_timestamp(ts)
        assert aligned == 1704067200.0

        ts = 1704067500.0
        aligned = granularity.align_timestamp(ts)
        assert aligned == 1704067500.0


class TestRetentionPolicyBoundaries:
    def test_cross_retention_boundary_cleanup(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300, retention_seconds=600)

        current_time = 1704067200.0

        store.write(current_time - 1000, 1.0)
        store.write(current_time - 700, 2.0)
        store.write(current_time - 400, 3.0)
        store.write(current_time - 100, 4.0)

        agg_before = store.query_aggregated("5min")
        assert len(agg_before) == 4

        deleted = store.clean_expired(current_time=current_time)

        agg_after = store.query_aggregated("5min")
        for agg in agg_after:
            assert agg.timestamp >= current_time - 600

    def test_cleanup_precise_to_window_boundary(self):
        store = MultiResolutionStore()
        store.add_granularity("hourly", 3600, retention_seconds=7200)

        current_time = 1704067200.0

        aligned_2h_ago = int((current_time - 7200) / 3600) * 3600
        aligned_1h_ago = int((current_time - 3600) / 3600) * 3600
        aligned_3h_ago = int((current_time - 10800) / 3600) * 3600

        store.write(aligned_3h_ago + 100, 1.0)
        store.write(aligned_2h_ago + 100, 2.0)
        store.write(aligned_1h_ago + 100, 3.0)

        deleted = store.clean_expired(current_time=current_time)

        agg_after = store.query_aggregated("hourly")
        timestamps = [a.timestamp for a in agg_after]

        assert aligned_3h_ago not in timestamps
        assert aligned_2h_ago in timestamps
        assert aligned_1h_ago in timestamps

    def test_all_data_expired_cleanup(self):
        store = MultiResolutionStore()
        store.set_retention_policy("raw", retention_seconds=3600)
        store.add_granularity("5min", 300, retention_seconds=3600)

        current_time = 1704067200.0

        store.write(current_time - 7201, 2.0)
        store.write(current_time - 7200, 1.0)

        deleted = store.clean_expired(current_time=current_time)
        assert deleted["raw"] == 2
        assert deleted["5min"] >= 1

        raw_after = store.query_raw()
        assert raw_after == []

        agg_after = store.query_aggregated("5min")
        assert agg_after == []

    def test_partial_window_not_dropped(self):
        store = MultiResolutionStore()
        store.add_granularity("hourly", 3600, retention_seconds=3600)

        current_time = 1704067200.0
        cutoff = current_time - 3600

        aligned_cutoff = int(cutoff / 3600) * 3600

        store.write(aligned_cutoff + 100, 1.0)
        store.write(aligned_cutoff + 1800, 2.0)
        store.write(aligned_cutoff + 3599, 3.0)

        deleted = store.clean_expired(current_time=current_time)

        agg_after = store.query_aggregated("hourly")
        assert len(agg_after) == 1
        assert agg_after[0].timestamp == aligned_cutoff
        assert agg_after[0].count == 3


class TestWindowBoundaryTimestamps:
    def test_timestamp_at_window_start(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        store.write(base_time, 10.0)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].timestamp == base_time

    def test_timestamp_at_window_end(self):
        store = make_multi_resolution_store()
        window_size = 300
        base_time = 1704067200.0

        store.write(base_time + window_size - 0.001, 10.0)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].timestamp == base_time

    def test_timestamp_exactly_on_boundary(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        store.write(base_time, 10.0)
        store.write(base_time + 300, 20.0)
        store.write(base_time + 600, 30.0)

        result = store.query_aggregated("5min")
        assert len(result) == 3
        assert result[0].timestamp == base_time
        assert result[1].timestamp == base_time + 300
        assert result[2].timestamp == base_time + 600

        assert result[0].sum == 10.0
        assert result[1].sum == 20.0
        assert result[2].sum == 30.0


class TestRollupStateEdgeCases:
    def test_empty_rollup_state(self):
        state = RollupState(window_start=1000.0)
        assert state.count == 0
        assert state.to_aggregate() is None

    def test_rollup_state_single_value(self):
        state = RollupState(window_start=1000.0)
        state.update(42.0)

        agg = state.to_aggregate()
        assert agg is not None
        assert agg.count == 1
        assert agg.avg == 42.0
        assert agg.max == 42.0
        assert agg.min == 42.0
        assert agg.sum == 42.0

    def test_rollup_state_merge(self):
        state1 = RollupState(window_start=1000.0)
        state1.update(10.0)
        state1.update(20.0)

        state2 = RollupState(window_start=1000.0)
        state2.update(30.0)
        state2.update(40.0)

        state1.merge(state2)

        agg = state1.to_aggregate()
        assert agg is not None
        assert agg.count == 4
        assert agg.sum == 100.0
        assert agg.min == 10.0
        assert agg.max == 40.0
        assert abs(agg.avg - 25.0) < 0.001

    def test_rollup_state_negative_values(self):
        state = RollupState(window_start=1000.0)
        state.update(-10.0)
        state.update(20.0)
        state.update(-5.0)

        agg = state.to_aggregate()
        assert agg is not None
        assert agg.count == 3
        assert agg.sum == 5.0
        assert agg.min == -10.0
        assert agg.max == 20.0
        assert abs(agg.avg - 5.0 / 3) < 0.001


class TestGranularityModel:
    def test_granularity_align_timestamp(self):
        g = Granularity(name="5min", window_seconds=300)
        assert g.align_timestamp(1000.0) == 900.0
        assert g.align_timestamp(1200.0) == 1200.0
        assert g.align_timestamp(1499.0) == 1200.0

    def test_granularity_with_retention(self):
        g = Granularity(
            name="5min", window_seconds=300, retention_seconds=86400
        )
        assert g.retention_seconds == 86400

    def test_granularity_permanent(self):
        g = Granularity(name="daily", window_seconds=86400, retention_seconds=None)
        assert g.retention_seconds is None


class TestDataPointEdgeCases:
    def test_datapoint_integer_values(self):
        point = DataPoint(timestamp=1000, value=42)
        assert isinstance(point.timestamp, float)
        assert isinstance(point.value, float)

    def test_datapoint_with_naive_datetime(self):
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        point = DataPoint.from_datetime(dt, 42.0)
        assert point.to_datetime().tzinfo == datetime.timezone.utc

    def test_datapoint_with_utc_datetime(self):
        dt = datetime.datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
        )
        point = DataPoint.from_datetime(dt, 42.0)
        assert point.to_datetime() == dt

    def test_datapoint_with_empty_labels(self):
        point = DataPoint(timestamp=1000.0, value=42.0, labels={})
        assert point.labels == {}

    def test_datapoint_with_multiple_labels(self):
        labels = {"host": "server1", "region": "us-east", "metric": "cpu"}
        point = DataPoint(timestamp=1000.0, value=42.0, labels=labels)
        assert point.labels == labels


class TestDownsamplingEdgeCases:
    def test_downsample_window_larger_than_data_span(self):
        ts = make_timeseries()
        base_time = 1000.0
        for i in range(10):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=86400, agg_type="avg")
        assert len(result) == 1
        assert result[0].count == 10
        assert abs(result[0].avg - 4.5) < 0.001

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

    def test_downsample_with_different_agg_types(self):
        ts = make_timeseries()
        ts.write(1000.0, 10.0)
        ts.write(1001.0, 20.0)
        ts.write(1002.0, 30.0)

        for agg_type in ["avg", "max", "min", "sum", "count"]:
            result = ts.downsample(window_seconds=60, agg_type=agg_type)
            assert len(result) == 1

    def test_downsample_with_fractional_timestamps(self):
        ts = make_timeseries()
        ts.write(1000.123, 10.0)
        ts.write(1000.456, 20.0)
        ts.write(1000.789, 30.0)

        result = ts.downsample(window_seconds=1, agg_type="sum")
        assert len(result) == 1
        assert result[0].sum == 60.0

    def test_downsample_with_negative_values(self):
        ts = make_timeseries()
        ts.write(1000.0, -10.0)
        ts.write(1001.0, 20.0)
        ts.write(1002.0, -5.0)

        result = ts.downsample(window_seconds=60, agg_type="sum")
        assert len(result) == 1
        assert result[0].sum == 5.0
        assert result[0].min == -10.0
        assert result[0].max == 20.0


class TestMultiResolutionEdgeCases:
    def test_query_raw_with_no_data(self):
        store = make_multi_resolution_store()
        result = store.query_raw()
        assert result == []

    def test_query_aggregated_with_no_data(self):
        store = make_multi_resolution_store()
        result = store.query_aggregated("5min")
        assert result == []

    def test_get_rollup_state_not_exists(self):
        store = make_multi_resolution_store()
        state = store.get_rollup_state("5min", 1000.0)
        assert state is None

    def test_get_rollup_state_exists(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        store.write(base_time, 10.0)
        store.write(base_time + 60, 20.0)

        state = store.get_rollup_state("5min", base_time)
        assert state is not None
        assert state.count == 2
        assert state.sum == 30.0

    def test_many_granularities(self):
        store = MultiResolutionStore()
        for i in range(10):
            store.add_granularity(f"g{i}", (i + 1) * 60)

        assert len(store.granularities) == 11

        store.write(1704067200.0, 42.0)

        for g in store.granularities:
            if g == "raw":
                continue
            result = store.query_aggregated(g)
            assert len(result) == 1
            assert result[0].count == 1

    def test_write_many_points(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        points = [(base_time + i, float(i)) for i in range(1000)]
        result = store.write_many(points)

        assert len(result) == 1000
        assert store.raw_data_count == 1000

        hourly = store.query_aggregated("hourly")
        assert len(hourly) == 1
        assert hourly[0].count == 1000
