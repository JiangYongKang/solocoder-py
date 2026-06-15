from __future__ import annotations

import pytest

from solocoder_py.batch_window.models import (
    AggregationResult,
    AggregationType,
    Event,
    OutputType,
    Window,
    WindowState,
)


class TestEventModel:
    def test_event_creation_defaults(self):
        event = Event(timestamp=10.0)
        assert event.timestamp == 10.0
        assert event.value is None
        assert event.key is None

    def test_event_creation_with_value(self):
        event = Event(timestamp=10.0, value=42)
        assert event.timestamp == 10.0
        assert event.value == 42

    def test_event_creation_with_key(self):
        event = Event(timestamp=10.0, key="user_1")
        assert event.timestamp == 10.0
        assert event.key == "user_1"

    def test_event_negative_timestamp_raises(self):
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            Event(timestamp=-1.0)

    def test_event_zero_timestamp(self):
        event = Event(timestamp=0.0)
        assert event.timestamp == 0.0

    def test_event_immutable(self):
        event = Event(timestamp=10.0, value=5)
        with pytest.raises(Exception):
            event.timestamp = 20.0


class TestWindowModel:
    def test_window_creation(self):
        window = Window(start=0.0, end=10.0)
        assert window.start == 0.0
        assert window.end == 10.0
        assert window.size == 10.0

    def test_window_negative_start_raises(self):
        with pytest.raises(ValueError, match="window start must be non-negative"):
            Window(start=-1.0, end=10.0)

    def test_window_end_less_than_start_raises(self):
        with pytest.raises(ValueError, match="window end must be greater than start"):
            Window(start=10.0, end=5.0)

    def test_window_end_equals_start_raises(self):
        with pytest.raises(ValueError, match="window end must be greater than start"):
            Window(start=10.0, end=10.0)

    def test_window_contains_timestamp(self):
        window = Window(start=0.0, end=10.0)
        assert window.contains(0.0) is True
        assert window.contains(5.0) is True
        assert window.contains(9.999) is True
        assert window.contains(10.0) is False
        assert window.contains(-1.0) is False

    def test_window_size_property(self):
        window = Window(start=5.0, end=15.0)
        assert window.size == 10.0

    def test_window_immutable(self):
        window = Window(start=0.0, end=10.0)
        with pytest.raises(Exception):
            window.start = 5.0


class TestWindowStateModel:
    def test_window_state_initialization(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.window == window
        assert state.count == 0
        assert state.sum_value == 0.0
        assert state.min_value is None
        assert state.max_value is None
        assert state.is_fired is False
        assert state.is_closed is False
        assert state.final_output_emitted is False

    def test_window_state_add_values(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(10.0)
        state.add(20.0)
        state.add(30.0)
        assert state.count == 3
        assert state.sum_value == 60.0
        assert state.min_value == 10.0
        assert state.max_value == 30.0

    def test_window_state_add_integer_values(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(10)
        state.add(20)
        assert state.sum_value == 30.0

    def test_window_state_get_count_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(1.0)
        state.add(2.0)
        assert state.get_result(AggregationType.COUNT) == 2

    def test_window_state_get_sum_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(10.0)
        state.add(20.0)
        assert state.get_result(AggregationType.SUM) == pytest.approx(30.0)

    def test_window_state_get_avg_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(10.0)
        state.add(20.0)
        state.add(30.0)
        assert state.get_result(AggregationType.AVG) == pytest.approx(20.0)

    def test_window_state_get_min_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(30.0)
        state.add(10.0)
        state.add(20.0)
        assert state.get_result(AggregationType.MIN) == pytest.approx(10.0)

    def test_window_state_get_max_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(30.0)
        state.add(10.0)
        state.add(20.0)
        assert state.get_result(AggregationType.MAX) == pytest.approx(30.0)

    def test_window_state_empty_count_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.COUNT) == 0

    def test_window_state_empty_sum_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.SUM) == pytest.approx(0.0)

    def test_window_state_empty_avg_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.AVG) == pytest.approx(0.0)

    def test_window_state_empty_min_max_result(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.MIN) is None
        assert state.get_result(AggregationType.MAX) is None

    def test_window_state_invalid_agg_type(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        with pytest.raises(ValueError, match="Unknown aggregation type"):
            state.get_result("invalid")


class TestAggregationResultModel:
    def test_aggregation_result_creation(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.FINAL,
        )
        assert result.window == window
        assert result.agg_type == AggregationType.COUNT
        assert result.value == 5
        assert result.output_type == OutputType.FINAL
        assert result.is_late_update is False

    def test_aggregation_result_is_final_property(self):
        window = Window(start=0.0, end=10.0)
        final_result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.FINAL,
        )
        intermediate_result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.INTERMEDIATE,
        )
        assert final_result.is_final is True
        assert intermediate_result.is_final is False

    def test_aggregation_result_is_intermediate_property(self):
        window = Window(start=0.0, end=10.0)
        final_result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.FINAL,
        )
        intermediate_result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.INTERMEDIATE,
        )
        assert final_result.is_intermediate is False
        assert intermediate_result.is_intermediate is True

    def test_aggregation_result_with_late_update(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.SUM,
            value=100.0,
            output_type=OutputType.INTERMEDIATE,
            is_late_update=True,
        )
        assert result.is_late_update is True

    def test_aggregation_result_immutable(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            output_type=OutputType.FINAL,
        )
        with pytest.raises(Exception):
            result.value = 10


class TestAggregationTypeEnum:
    def test_aggregation_type_values(self):
        assert AggregationType.COUNT.value == "count"
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.AVG.value == "avg"
        assert AggregationType.MIN.value == "min"
        assert AggregationType.MAX.value == "max"


class TestOutputTypeEnum:
    def test_output_type_values(self):
        assert OutputType.INTERMEDIATE.value == "intermediate"
        assert OutputType.FINAL.value == "final"
