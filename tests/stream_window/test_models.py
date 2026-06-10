from __future__ import annotations

import pytest

from solocoder_py.stream_window import (
    AggregationResult,
    AggregationType,
    Event,
    InvalidWindowConfigError,
    StreamWindowError,
    Window,
    WindowState,
)


class TestEvent:
    def test_event_creation(self):
        event = Event(timestamp=10.5, value=42, key="test")
        assert event.timestamp == 10.5
        assert event.value == 42
        assert event.key == "test"

    def test_event_default_values(self):
        event = Event(timestamp=5.0)
        assert event.value is None
        assert event.key is None

    def test_event_negative_timestamp_raises(self):
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            Event(timestamp=-1.0)

    def test_event_zero_timestamp(self):
        event = Event(timestamp=0.0)
        assert event.timestamp == 0.0

    def test_event_frozen(self):
        event = Event(timestamp=10.0)
        with pytest.raises(AttributeError):
            event.timestamp = 20.0


class TestWindow:
    def test_window_creation(self):
        window = Window(start=0.0, end=10.0)
        assert window.start == 0.0
        assert window.end == 10.0
        assert window.size == 10.0

    def test_window_negative_start_raises(self):
        with pytest.raises(ValueError, match="window start must be non-negative"):
            Window(start=-1.0, end=10.0)

    def test_window_end_before_start_raises(self):
        with pytest.raises(ValueError, match="window end must be greater than start"):
            Window(start=10.0, end=5.0)

    def test_window_end_equals_start_raises(self):
        with pytest.raises(ValueError, match="window end must be greater than start"):
            Window(start=5.0, end=5.0)

    def test_window_contains(self):
        window = Window(start=0.0, end=10.0)
        assert window.contains(0.0) is True
        assert window.contains(5.0) is True
        assert window.contains(9.999) is True
        assert window.contains(10.0) is False
        assert window.contains(-1.0) is False

    def test_window_size_property(self):
        window = Window(start=5.0, end=15.0)
        assert window.size == 10.0

    def test_window_frozen(self):
        window = Window(start=0.0, end=10.0)
        with pytest.raises(AttributeError):
            window.start = 5.0


class TestWindowState:
    def test_state_initial(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.count == 0
        assert state.sum_value == 0.0
        assert state.min_value is None
        assert state.max_value is None
        assert state.fired is False

    def test_state_add_single_value(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(5.0)
        assert state.count == 1
        assert state.sum_value == 5.0
        assert state.min_value == 5.0
        assert state.max_value == 5.0

    def test_state_add_multiple_values(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(3.0)
        state.add(7.0)
        state.add(5.0)
        assert state.count == 3
        assert state.sum_value == 15.0
        assert state.min_value == 3.0
        assert state.max_value == 7.0

    def test_state_add_integer(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(10)
        state.add(20)
        assert state.count == 2
        assert state.sum_value == 30.0

    def test_get_result_count_empty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.COUNT) == 0

    def test_get_result_count_nonempty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(5.0)
        state.add(10.0)
        assert state.get_result(AggregationType.COUNT) == 2

    def test_get_result_sum_empty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.SUM) == 0.0

    def test_get_result_sum_nonempty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(3.0)
        state.add(7.0)
        assert state.get_result(AggregationType.SUM) == 10.0

    def test_get_result_avg_empty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.AVG) == 0.0

    def test_get_result_avg_nonempty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(2.0)
        state.add(4.0)
        state.add(6.0)
        assert state.get_result(AggregationType.AVG) == pytest.approx(4.0)

    def test_get_result_min_empty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.MIN) is None

    def test_get_result_min_nonempty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(5.0)
        state.add(3.0)
        state.add(7.0)
        assert state.get_result(AggregationType.MIN) == 3.0

    def test_get_result_max_empty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        assert state.get_result(AggregationType.MAX) is None

    def test_get_result_max_nonempty(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        state.add(5.0)
        state.add(3.0)
        state.add(7.0)
        assert state.get_result(AggregationType.MAX) == 7.0

    def test_get_result_unknown_type_raises(self):
        window = Window(start=0.0, end=10.0)
        state = WindowState(window=window)
        with pytest.raises(ValueError, match="Unknown aggregation type"):
            state.get_result("unknown")


class TestAggregationResult:
    def test_result_creation(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
            is_late_recompute=False,
        )
        assert result.window == window
        assert result.agg_type == AggregationType.COUNT
        assert result.value == 5
        assert result.is_late_recompute is False

    def test_result_late_recompute(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.SUM,
            value=100.0,
            is_late_recompute=True,
        )
        assert result.is_late_recompute is True

    def test_result_frozen(self):
        window = Window(start=0.0, end=10.0)
        result = AggregationResult(
            window=window,
            agg_type=AggregationType.COUNT,
            value=5,
        )
        with pytest.raises(AttributeError):
            result.value = 10


class TestExceptions:
    def test_stream_window_error_is_exception(self):
        assert issubclass(StreamWindowError, Exception)

    def test_invalid_window_config_error_inheritance(self):
        assert issubclass(InvalidWindowConfigError, StreamWindowError)

    def test_invalid_window_config_raises_directly(self):
        with pytest.raises(StreamWindowError):
            raise InvalidWindowConfigError("test error")
