from __future__ import annotations

import datetime

import pytest

from solocoder_py.timeseries import (
    AggregateValue,
    DataPoint,
    MultiResolutionStore,
    TimeSeries,
)

from .conftest import make_multi_resolution_store, make_timeseries


class TestTimeSeriesWriteQuery:
    def test_write_and_query_single_point(self):
        ts = make_timeseries()
        point = ts.write(1000.0, 42.0)

        assert point.timestamp == 1000.0
        assert point.value == 42.0
        assert len(ts) == 1

        results = ts.query(1000.0, 1000.0)
        assert len(results) == 1
        assert results[0].value == 42.0

    def test_write_multiple_points_and_query_range(self):
        ts = make_timeseries()
        for i in range(10):
            ts.write(1000.0 + i, float(i * 10))

        results = ts.query(1002.0, 1005.0)
        assert len(results) == 4
        assert [p.value for p in results] == [20.0, 30.0, 40.0, 50.0]
        assert [p.timestamp for p in results] == sorted(
            [p.timestamp for p in results]
        )

    def test_write_with_datetime(self):
        ts = make_timeseries()
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        ts.write(dt, 100.0)

        results = ts.query(dt, dt)
        assert len(results) == 1
        assert results[0].value == 100.0
        assert results[0].to_datetime() == dt

    def test_write_with_labels(self):
        ts = make_timeseries()
        ts.write(1000.0, 1.0, labels={"host": "server1", "metric": "cpu"})
        ts.write(1001.0, 2.0, labels={"host": "server2", "metric": "cpu"})
        ts.write(1002.0, 3.0, labels={"host": "server1", "metric": "memory"})

        results = ts.query(labels={"host": "server1"})
        assert len(results) == 2
        assert {p.value for p in results} == {1.0, 3.0}

        results = ts.query(labels={"metric": "cpu"})
        assert len(results) == 2
        assert {p.value for p in results} == {1.0, 2.0}

    def test_overwrite_same_timestamp(self):
        ts = make_timeseries()
        ts.write(1000.0, 10.0)
        ts.write(1000.0, 20.0)

        assert len(ts) == 1
        results = ts.query(1000.0, 1000.0)
        assert results[0].value == 20.0

    def test_query_returns_sorted_by_time(self):
        ts = make_timeseries()
        ts.write(1005.0, 5.0, allow_out_of_order=True)
        ts.write(1001.0, 1.0, allow_out_of_order=True)
        ts.write(1003.0, 3.0, allow_out_of_order=True)

        results = ts.query()
        assert [p.timestamp for p in results] == [1001.0, 1003.0, 1005.0]


class TestDownsampling:
    def test_downsample_avg(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(60):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=30, agg_type="avg")
        assert len(result) == 2
        assert abs(result[0].avg - 14.5) < 0.001
        assert abs(result[1].avg - 44.5) < 0.001

    def test_downsample_max(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(60):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=30, agg_type="max")
        assert len(result) == 2
        assert result[0].max == 29.0
        assert result[1].max == 59.0

    def test_downsample_min(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(60):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=30, agg_type="min")
        assert len(result) == 2
        assert result[0].min == 0.0
        assert result[1].min == 30.0

    def test_downsample_sum(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(60):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=30, agg_type="sum")
        assert len(result) == 2
        assert result[0].sum == 435.0
        assert result[1].sum == 1335.0

    def test_downsample_count(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(60):
            ts.write(base_time + i, float(i))

        result = ts.downsample(window_seconds=30, agg_type="count")
        assert len(result) == 2
        assert result[0].count == 30
        assert result[1].count == 30

    def test_downsample_with_time_range(self):
        ts = make_timeseries()
        base_time = 990.0
        for i in range(120):
            ts.write(base_time + i, float(i))

        result = ts.downsample(
            window_seconds=30,
            agg_type="sum",
            start_time=1020.0,
            end_time=1079.0,
        )
        assert len(result) == 2

    def test_downsample_with_labels(self):
        ts = make_timeseries()
        for i in range(30):
            ts.write(990.0 + i, float(i), labels={"host": "server1"})
        for i in range(30):
            ts.write(1020.0 + i, float(i * 2), labels={"host": "server2"})

        result = ts.downsample(
            window_seconds=30, agg_type="avg", labels={"host": "server1"}
        )
        assert len(result) == 1
        assert abs(result[0].avg - 14.5) < 0.001

        result = ts.downsample(
            window_seconds=30, agg_type="avg", labels={"host": "server2"}
        )
        assert len(result) == 1
        assert abs(result[0].avg - 29.0) < 0.001


class TestMultiResolutionRollup:
    def test_write_raw_auto_rollup_to_all_granularities(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        for i in range(12):
            store.write(base_time + i * 60, float(i))

        raw_data = store.query_raw()
        assert len(raw_data) == 12

        five_min_data = store.query_aggregated("5min")
        assert len(five_min_data) > 0

        hourly_data = store.query_aggregated("hourly")
        assert len(hourly_data) == 1
        assert hourly_data[0].count == 12

        daily_data = store.query_aggregated("daily")
        assert len(daily_data) == 1
        assert daily_data[0].count == 12

    def test_rollup_avg_correctness(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert abs(result[0].avg - 30.0) < 0.001

    def test_rollup_max_correctness(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 50.0, 30.0, 40.0, 20.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].max == 50.0

    def test_rollup_min_correctness(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 50.0, 30.0, 40.0, 20.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].min == 10.0

    def test_rollup_sum_correctness(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].sum == 150.0

    def test_rollup_count_correctness(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, v in enumerate(values):
            store.write(base_time + i * 60, v)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].count == 5

    def test_incremental_rollup(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        store.write(base_time, 10.0)
        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].sum == 10.0
        assert result[0].count == 1

        store.write(base_time + 60, 20.0)
        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].sum == 30.0
        assert result[0].count == 2
        assert abs(result[0].avg - 15.0) < 0.001

    def test_multiple_windows_rollup(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        for i in range(15):
            store.write(base_time + i * 60, float(i))

        result = store.query_aggregated("5min")
        assert len(result) == 3

        assert result[0].count == 5
        assert result[1].count == 5
        assert result[2].count == 5

        assert result[0].sum == 10.0
        assert result[1].sum == 35.0
        assert result[2].sum == 60.0

    def test_query_aggregated_by_granularity(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        for i in range(120):
            store.write(base_time + i * 60, float(i))

        five_min = store.query_aggregated("5min")
        hourly = store.query_aggregated("hourly")
        daily = store.query_aggregated("daily")

        assert len(five_min) == 24
        assert len(hourly) == 2
        assert len(daily) == 1

        assert hourly[0].count == 60
        assert hourly[1].count == 60
        assert daily[0].count == 120

    def test_rollup_with_labels(self):
        store = make_multi_resolution_store()
        base_time = 1704067200.0

        for i in range(10):
            store.write(base_time + i * 60, float(i), labels={"host": "server1"})
            store.write(
                base_time + i * 60, float(i * 2), labels={"host": "server2"}
            )

        result = store.query_aggregated("5min", labels={"host": "server1"})
        assert len(result) == 2
        assert all(a.labels.get("host") == "server1" for a in result)

        result = store.query_aggregated("5min", labels={"host": "server2"})
        assert len(result) == 2
        assert all(a.labels.get("host") == "server2" for a in result)

        combined = store.query_aggregated("5min")
        assert len(combined) == 4


class TestRetentionPolicy:
    def test_clean_expired_raw_data(self):
        store = MultiResolutionStore()
        store.set_retention_policy("raw", retention_seconds=3600)

        current_time = 1704067200.0
        one_hour_ago = current_time - 3600
        two_hours_ago = current_time - 7200

        store.write(two_hours_ago, 1.0)
        store.write(one_hour_ago + 1, 2.0)
        store.write(current_time - 1800, 3.0)

        raw_before = store.query_raw()
        assert len(raw_before) == 3

        deleted = store.clean_expired(current_time=current_time)
        assert deleted["raw"] == 1

        raw_after = store.query_raw()
        assert len(raw_after) == 2
        assert all(p.timestamp >= one_hour_ago for p in raw_after)

    def test_clean_expired_aggregated_data(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300, retention_seconds=86400)

        current_time = 1704067200.0
        two_days_ago = current_time - 172800
        one_day_ago = current_time - 86400

        store.write(two_days_ago, 1.0)
        store.write(one_day_ago + 300, 2.0)
        store.write(current_time - 3600, 3.0)

        agg_before = store.query_aggregated("5min")
        assert len(agg_before) == 3

        deleted = store.clean_expired(current_time=current_time)
        assert deleted["5min"] == 1

        agg_after = store.query_aggregated("5min")
        assert len(agg_after) == 2

    def test_clean_expired_preserves_permanent_data(self):
        store = make_multi_resolution_store()

        current_time = 1704067200.0
        old_time = current_time - 31536000

        store.write(old_time, 1.0)

        agg_before = store.query_aggregated("daily")
        assert len(agg_before) == 1

        deleted = store.clean_expired(current_time=current_time)
        assert deleted["daily"] == 0

        agg_after = store.query_aggregated("daily")
        assert len(agg_after) == 1

    def test_retention_policy_updates(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)

        policy = store.get_retention_policy("5min")
        assert policy.retention_seconds is None

        store.set_retention_policy("5min", retention_seconds=86400)
        policy = store.get_retention_policy("5min")
        assert policy.retention_seconds == 86400

    def test_cleanup_is_window_aligned(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300, retention_seconds=600)

        current_time = 1704067200.0

        for i in range(10):
            store.write(current_time - 900 + i * 60, float(i))

        deleted = store.clean_expired(current_time=current_time)
        assert deleted["5min"] >= 1

        agg_data = store.query_aggregated("5min")
        for agg in agg_data:
            assert agg.timestamp >= current_time - 600


class TestDataPointModel:
    def test_datapoint_creation(self):
        point = DataPoint(timestamp=1000.0, value=42.0)
        assert point.timestamp == 1000.0
        assert point.value == 42.0
        assert point.labels == {}

    def test_datapoint_with_labels(self):
        point = DataPoint(
            timestamp=1000.0, value=42.0, labels={"host": "server1"}
        )
        assert point.labels == {"host": "server1"}

    def test_datapoint_from_datetime(self):
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        point = DataPoint.from_datetime(dt, 42.0)
        assert point.timestamp == dt.timestamp()
        assert point.value == 42.0

    def test_datapoint_to_datetime(self):
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        point = DataPoint(timestamp=dt.timestamp(), value=42.0)
        assert point.to_datetime() == dt


class TestAggregateValueModel:
    def test_aggregate_value_get(self):
        agg = AggregateValue(
            timestamp=1000.0,
            avg=30.0,
            max=50.0,
            min=10.0,
            sum=150.0,
            count=5,
        )
        assert agg.get("avg") == 30.0
        assert agg.get("max") == 50.0
        assert agg.get("min") == 10.0
        assert agg.get("sum") == 150.0
        assert agg.get("count") == 5.0
