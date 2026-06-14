from __future__ import annotations

import pytest

from solocoder_py.timeseries import (
    Granularity,
    MultiResolutionStore,
    RollupState,
    TimeSeries,
    align_timestamp,
)


class TestNegativeTimestampAlignment:
    def test_aggregator_align_positive(self):
        assert align_timestamp(100.0, 60) == 60.0
        assert align_timestamp(120.0, 60) == 120.0
        assert align_timestamp(179.0, 60) == 120.0
        assert align_timestamp(180.0, 60) == 180.0

    def test_aggregator_align_negative(self):
        assert align_timestamp(-1.0, 60) == -60.0
        assert align_timestamp(-59.0, 60) == -60.0
        assert align_timestamp(-60.0, 60) == -60.0
        assert align_timestamp(-61.0, 60) == -120.0
        assert align_timestamp(-120.0, 60) == -120.0

    def test_aggregator_align_zero(self):
        assert align_timestamp(0.0, 60) == 0.0
        assert align_timestamp(0.5, 60) == 0.0
        assert align_timestamp(-0.5, 60) == -60.0

    def test_granularity_align_positive(self):
        g = Granularity(name="test", window_seconds=300)
        assert g.align_timestamp(100.0) == 0.0
        assert g.align_timestamp(300.0) == 300.0
        assert g.align_timestamp(599.0) == 300.0
        assert g.align_timestamp(600.0) == 600.0

    def test_granularity_align_negative(self):
        g = Granularity(name="test", window_seconds=300)
        assert g.align_timestamp(-1.0) == -300.0
        assert g.align_timestamp(-299.0) == -300.0
        assert g.align_timestamp(-300.0) == -300.0
        assert g.align_timestamp(-301.0) == -600.0
        assert g.align_timestamp(-600.0) == -600.0

    def test_consistency_positive_negative(self):
        g = Granularity(name="test", window_seconds=60)
        for ts in [-120, -60, -1, 0, 1, 60, 120]:
            assert align_timestamp(float(ts), 60) == g.align_timestamp(float(ts))

    def test_timeseries_downsample_negative_timestamps(self):
        ts = TimeSeries()
        ts.write(-59.0, 10.0, allow_out_of_order=True)
        ts.write(-30.0, 20.0, allow_out_of_order=True)
        ts.write(-1.0, 30.0, allow_out_of_order=True)
        ts.write(1.0, 40.0)
        ts.write(30.0, 50.0)
        ts.write(59.0, 60.0)

        result = ts.downsample(window_seconds=60, agg_type="sum")
        assert len(result) == 2
        assert result[0].timestamp == -60.0
        assert result[0].sum == 60.0
        assert result[1].timestamp == 0.0
        assert result[1].sum == 150.0

    def test_multi_resolution_store_negative_timestamps(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)

        store.write(-500.0, 1.0, allow_out_of_order=True)
        store.write(-400.0, 2.0, allow_out_of_order=True)
        store.write(-100.0, 3.0, allow_out_of_order=True)
        store.write(-50.0, 4.0, allow_out_of_order=True)

        result = store.query_aggregated("5min")
        timestamps = sorted([a.timestamp for a in result])
        assert -600.0 in timestamps
        assert -300.0 in timestamps


class TestOverwriteRollupConsistency:
    def test_overwrite_same_labels_same_value(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        store.write(base, 10.0, labels={"host": "server1"})
        agg_before = store.query_aggregated("5min")
        assert agg_before[0].count == 1
        assert agg_before[0].sum == 10.0

        store.write(base, 10.0, labels={"host": "server1"})
        agg_after = store.query_aggregated("5min")
        assert agg_after[0].count == 1
        assert agg_after[0].sum == 10.0

    def test_overwrite_same_labels_different_value_sum_count(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        store.write(base, 10.0, labels={"host": "server1"})
        agg_before = store.query_aggregated("5min")
        assert agg_before[0].count == 1
        assert agg_before[0].sum == 10.0
        assert agg_before[0].avg == 10.0

        store.write(base, 20.0, labels={"host": "server1"})
        agg_after = store.query_aggregated("5min")
        assert agg_after[0].count == 1
        assert agg_after[0].sum == 20.0
        assert agg_after[0].avg == 20.0

    def test_overwrite_same_labels_no_double_count(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        for i in range(3):
            store.write(base + i, float(i + 1), labels={"host": "server1"})

        agg_before = store.query_aggregated("5min")[0]
        assert agg_before.count == 3
        assert agg_before.sum == 6.0
        assert agg_before.avg == 2.0

        store.write(base + 1, 100.0, labels={"host": "server1"}, allow_out_of_order=True)

        agg_after = store.query_aggregated("5min")[0]
        assert agg_after.count == 3
        assert agg_after.sum == 104.0
        assert abs(agg_after.avg - 104.0 / 3) < 0.001

    def test_overwrite_change_labels_removes_ghost(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        store.write(base, 10.0, labels={"host": "server1"})
        server1_before = store.query_aggregated("5min", labels={"host": "server1"})
        server2_before = store.query_aggregated("5min", labels={"host": "server2"})
        assert len(server1_before) == 1
        assert len(server2_before) == 0

        store.write(base, 20.0, labels={"host": "server2"})
        server1_after = store.query_aggregated("5min", labels={"host": "server1"})
        server2_after = store.query_aggregated("5min", labels={"host": "server2"})
        assert len(server1_after) == 0
        assert len(server2_after) == 1
        assert server2_after[0].sum == 20.0
        assert server2_after[0].count == 1

    def test_overwrite_multiple_points_consistency(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        for i in range(5):
            store.write(base + i * 10, float(i), labels={"host": "server1"})

        agg_1 = store.query_aggregated("5min")[0]
        assert agg_1.count == 5
        assert agg_1.sum == 10.0

        store.write(base + 10, 50.0, labels={"host": "server1"}, allow_out_of_order=True)
        store.write(base + 30, 60.0, labels={"host": "server1"}, allow_out_of_order=True)

        agg_2 = store.query_aggregated("5min")[0]
        assert agg_2.count == 5
        assert agg_2.sum == 0 + 50 + 2 + 60 + 4
        assert agg_2.max == 60.0
        assert agg_2.min == 0.0

    def test_overwrite_min_max_correctness(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        store.write(base, 10.0, labels={"host": "server1"})
        store.write(base + 1, 50.0, labels={"host": "server1"})
        store.write(base + 2, 30.0, labels={"host": "server1"})

        agg_before = store.query_aggregated("5min")[0]
        assert agg_before.max == 50.0
        assert agg_before.min == 10.0

        store.write(base + 1, 5.0, labels={"host": "server1"}, allow_out_of_order=True)

        agg_after = store.query_aggregated("5min")[0]
        assert agg_after.max == 30.0
        assert agg_after.min == 5.0

    def test_overwrite_across_multiple_granularities(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        store.add_granularity("hourly", 3600)
        base = 1704067200.0

        for i in range(5):
            store.write(base + i * 10, float(i))

        store.write(base + 10, 100.0, allow_out_of_order=True)

        five_min = store.query_aggregated("5min")[0]
        hourly = store.query_aggregated("hourly")[0]

        expected_sum = 0 + 100 + 2 + 3 + 4
        assert five_min.sum == expected_sum
        assert five_min.count == 5
        assert hourly.sum == expected_sum
        assert hourly.count == 5

    def test_overwrite_to_empty_then_add(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)
        base = 1704067200.0

        store.write(base, 10.0, labels={"host": "server1"})
        assert len(store.query_aggregated("5min")) == 1

        store.write(base, 20.0, labels={"host": "server2"})
        server1 = store.query_aggregated("5min", labels={"host": "server1"})
        server2 = store.query_aggregated("5min", labels={"host": "server2"})
        assert len(server1) == 0
        assert len(server2) == 1
        assert server2[0].sum == 20.0

        store.write(base + 1, 30.0, labels={"host": "server1"})
        server1 = store.query_aggregated("5min", labels={"host": "server1"})
        server2 = store.query_aggregated("5min", labels={"host": "server2"})
        assert len(server1) == 1
        assert server1[0].sum == 30.0
        assert len(server2) == 1
        assert server2[0].sum == 20.0


class TestRollupStateReset:
    def test_reset_clears_all_fields(self):
        state = RollupState(window_start=1000.0)
        state.update(10.0)
        state.update(20.0)
        assert state.count == 2
        assert state.sum == 30.0
        assert state.min == 10.0
        assert state.max == 20.0

        state.reset()
        assert state.count == 0
        assert state.sum == 0.0
        assert state.min == float("inf")
        assert state.max == float("-inf")
        assert state.to_aggregate() is None

    def test_rebuild_from_values(self):
        state = RollupState(window_start=1000.0)
        state.update(999.0)

        state.rebuild_from_values([1.0, 2.0, 3.0, 4.0, 5.0])
        assert state.count == 5
        assert state.sum == 15.0
        assert state.min == 1.0
        assert state.max == 5.0

        agg = state.to_aggregate()
        assert agg is not None
        assert agg.count == 5
        assert agg.avg == 3.0

    def test_rebuild_from_empty_values(self):
        state = RollupState(window_start=1000.0)
        state.update(10.0)

        state.rebuild_from_values([])
        assert state.count == 0
        assert state.to_aggregate() is None


class TestDeadCodeCleanup:
    def test_aggregate_time_series_no_windows_attr(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)

        series = store._aggregate_series["5min"]
        assert not hasattr(series, "_windows")

    def test_write_aggregate_works(self):
        store = MultiResolutionStore()
        store.add_granularity("5min", 300)

        from solocoder_py.timeseries import AggregateValue
        agg = AggregateValue(
            timestamp=1000.0,
            avg=15.0,
            max=20.0,
            min=10.0,
            sum=30.0,
            count=2,
            labels={},
        )
        store._aggregate_series["5min"].write_aggregate(agg)

        result = store.query_aggregated("5min")
        assert len(result) == 1
        assert result[0].timestamp == 1000.0
        assert result[0].sum == 30.0
