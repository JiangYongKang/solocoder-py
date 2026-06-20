from __future__ import annotations

import pytest

from solocoder_py.telemetry.models import LateDataStrategy, WindowConfig
from solocoder_py.telemetry.window import OrderWindow


class TestInOrderData:
    def test_all_in_order_data_accepted(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": 1},
            {"timestamp": 101.0, "value": 2},
            {"timestamp": 102.0, "value": 3},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 3
        assert len(late) == 0

    def test_in_order_data_sorted_correctly(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 200.0, "value": "b"},
            {"timestamp": 300.0, "value": "c"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 3
        assert len(late) == 0
        sorted_data = window.flush()
        timestamps = [r["timestamp"] for r in sorted_data]
        assert timestamps == [100.0, 200.0, 300.0]


class TestWithinWindowOutOfOrder:
    def test_within_tolerance_accepted_and_resorted(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 120.0, "value": "b"},
            {"timestamp": 105.0, "value": "c"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 3
        assert len(late) == 0
        sorted_data = window.flush()
        timestamps = [r["timestamp"] for r in sorted_data]
        assert timestamps == [100.0, 105.0, 120.0]

    def test_just_within_tolerance_boundary(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 130.0, "value": "a"},
            {"timestamp": 100.0, "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 2
        assert len(late) == 0

    def test_multiple_out_of_order_within_window(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 115.0, "value": "b"},
            {"timestamp": 105.0, "value": "c"},
            {"timestamp": 110.0, "value": "d"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 4
        assert len(late) == 0
        sorted_data = window.flush()
        timestamps = [r["timestamp"] for r in sorted_data]
        assert timestamps == [100.0, 105.0, 110.0, 115.0]


class TestBeyondWindowLateData:
    def test_beyond_tolerance_marked_late(self):
        config = WindowConfig(
            tolerance_seconds=30.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.LOG,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 150.0, "value": "b"},
            {"timestamp": 110.0, "value": "c"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 2
        assert len(late) == 1
        assert late[0]["value"] == "c"

    def test_just_beyond_tolerance_boundary(self):
        config = WindowConfig(
            tolerance_seconds=30.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.LOG,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 131.0, "value": "a"},
            {"timestamp": 100.0, "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 1
        assert len(late) == 1
        assert late[0]["value"] == "b"


class TestLateDataStrategy:
    def test_discard_strategy(self):
        config = WindowConfig(
            tolerance_seconds=5.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.DISCARD,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 50.0, "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 1
        assert len(late) == 1

    def test_callback_strategy(self):
        late_records = []
        config = WindowConfig(
            tolerance_seconds=5.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.CALLBACK,
        )
        window = OrderWindow(config, on_late=late_records.append)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 50.0, "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(late_records) == 1
        assert late_records[0]["value"] == "b"


class TestWindowZeroTolerance:
    def test_zero_tolerance_all_out_of_order_are_late(self):
        config = WindowConfig(
            tolerance_seconds=0.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.DISCARD,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 99.9, "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 1
        assert len(late) == 1
        assert late[0]["value"] == "b"

    def test_zero_tolerance_in_order_accepted(self):
        config = WindowConfig(
            tolerance_seconds=0.0,
            timestamp_field="timestamp",
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 100.0, "value": "b"},
            {"timestamp": 101.0, "value": "c"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 3
        assert len(late) == 0


class TestMissingTimestamp:
    def test_missing_timestamp_treated_as_late(self):
        config = WindowConfig(
            tolerance_seconds=30.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.DISCARD,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 1
        assert len(late) == 1

    def test_invalid_timestamp_treated_as_late(self):
        config = WindowConfig(
            tolerance_seconds=30.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.DISCARD,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": "not_a_number", "value": "b"},
        ]
        accepted, late = window.process(records)
        assert len(accepted) == 1
        assert len(late) == 1


class TestFlushAndReset:
    def test_flush_returns_sorted_data(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 110.0, "value": "b"},
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 120.0, "value": "c"},
        ]
        window.process(records)
        sorted_data = window.flush()
        timestamps = [r["timestamp"] for r in sorted_data]
        assert timestamps == [100.0, 110.0, 120.0]

    def test_flush_clears_window(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [{"timestamp": 100.0, "value": "a"}]
        window.process(records)
        window.flush()
        assert window.window_size == 0
        assert window.high_watermark is None

    def test_reset_clears_everything(self):
        config = WindowConfig(
            tolerance_seconds=5.0,
            timestamp_field="timestamp",
            late_data_strategy=LateDataStrategy.DISCARD,
        )
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 50.0, "value": "b"},
        ]
        window.process(records)
        window.reset()
        assert window.window_size == 0
        assert window.high_watermark is None
        assert len(window.late_data) == 0


class TestHighWatermark:
    def test_high_watermark_tracks_max_timestamp(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)

        records = [
            {"timestamp": 100.0, "value": "a"},
            {"timestamp": 150.0, "value": "b"},
            {"timestamp": 120.0, "value": "c"},
        ]
        window.process(records)
        assert window.high_watermark == 150.0

    def test_high_watermark_initially_none(self):
        config = WindowConfig(tolerance_seconds=30.0, timestamp_field="timestamp")
        window = OrderWindow(config)
        assert window.high_watermark is None
