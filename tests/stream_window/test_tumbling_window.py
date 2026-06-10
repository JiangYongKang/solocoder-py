from __future__ import annotations

import pytest

from solocoder_py.stream_window import (
    AggregationResult,
    AggregationType,
    Event,
    InvalidWindowConfigError,
    LateEventDroppedError,
    TumblingWindowAggregator,
    Window,
)


class TestTumblingWindowCreation:
    def test_default_creation(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        assert agg.window_size_seconds == 10.0
        assert agg.agg_type == AggregationType.COUNT
        assert agg.allowed_lateness_seconds == 0.0
        assert agg.watermark_delay_seconds == 0.0
        assert agg.get_active_window_count() == 0
        assert agg.dropped_late_count == 0

    def test_custom_agg_type(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=5.0,
            agg_type=AggregationType.SUM,
        )
        assert agg.agg_type == AggregationType.SUM

    def test_with_allowed_lateness(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
        )
        assert agg.allowed_lateness_seconds == 5.0

    def test_with_watermark_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=2.0,
        )
        assert agg.watermark_delay_seconds == 2.0

    def test_zero_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            TumblingWindowAggregator(window_size_seconds=0.0)

    def test_negative_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            TumblingWindowAggregator(window_size_seconds=-5.0)

    def test_negative_allowed_lateness_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="allowed_lateness_seconds must be non-negative"):
            TumblingWindowAggregator(
                window_size_seconds=10.0,
                allowed_lateness_seconds=-1.0,
            )

    def test_negative_watermark_delay_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="watermark_delay_seconds must be non-negative"):
            TumblingWindowAggregator(
                window_size_seconds=10.0,
                watermark_delay_seconds=-1.0,
            )


class TestTumblingWindowAssignment:
    def test_event_in_first_window(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        results = agg.on_event(Event(timestamp=5.0))
        assert agg.get_active_window_count() == 1
        state = agg.get_window_state(0.0)
        assert state is not None
        assert state.count == 1
        assert state.window.start == 0.0
        assert state.window.end == 10.0
        assert len(results) == 0

    def test_event_at_window_boundary(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        results = agg.on_event(Event(timestamp=10.0))
        assert agg.get_active_window_count() == 1
        state = agg.get_window_state(10.0)
        assert state is not None
        assert state.count == 1
        assert state.window.start == 10.0
        assert state.window.end == 20.0

    def test_event_at_zero(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        results = agg.on_event(Event(timestamp=0.0))
        state = agg.get_window_state(0.0)
        assert state is not None
        assert state.count == 1

    def test_multiple_events_same_window(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=1.0))
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=9.0))
        state = agg.get_window_state(0.0)
        assert state.count == 3
        assert agg.get_active_window_count() == 1

    def test_events_in_different_windows_with_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=15.0))
        agg.on_event(Event(timestamp=25.0))
        assert agg.get_active_window_count() == 3
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(10.0).count == 1
        assert agg.get_window_state(20.0).count == 1

    def test_non_aligned_window_size_with_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=7.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=8.0))
        assert agg.get_active_window_count() == 2
        state0 = agg.get_window_state(0.0)
        state7 = agg.get_window_state(7.0)
        assert state0 is not None
        assert state0.count == 1
        assert state7 is not None
        assert state7.count == 1

    def test_events_in_different_windows_fire_in_order(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0, agg_type=AggregationType.COUNT)
        r1 = agg.on_event(Event(timestamp=5.0))
        assert len(r1) == 0
        assert agg.get_active_window_count() == 1

        r2 = agg.on_event(Event(timestamp=15.0))
        assert len(r2) == 1
        assert r2[0].window.start == 0.0
        assert r2[0].value == 1
        assert r2[0].is_late_recompute is False
        assert agg.get_active_window_count() == 1

        r3 = agg.on_event(Event(timestamp=25.0))
        assert len(r3) == 1
        assert r3[0].window.start == 10.0
        assert r3[0].value == 1
        assert agg.get_active_window_count() == 1


class TestTumblingWindowWatermarkAndFiring:
    def test_watermark_advances_with_events(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_watermark() == pytest.approx(5.0)
        agg.on_event(Event(timestamp=15.0))
        assert agg.get_watermark() == pytest.approx(15.0)

    def test_window_fires_when_watermark_passes_end(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0, agg_type=AggregationType.COUNT)
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_active_window_count() == 1

        results = agg.on_event(Event(timestamp=10.0))
        assert len(results) == 1
        assert results[0].window.start == 0.0
        assert results[0].window.end == 10.0
        assert results[0].value == 1
        assert results[0].is_late_recompute is False

    def test_fired_window_cleaned_up_when_no_lateness(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=10.0))
        assert agg.get_window_state(0.0) is None
        assert agg.get_active_window_count() == 1

    def test_watermark_at_window_end_fires_window(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=5.0))
        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].window.end == 10.0

    def test_advance_watermark_fires_multiple_windows_with_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=15.0))
        assert agg.get_active_window_count() == 2

        results = agg.advance_watermark(30.0)
        assert len(results) == 2

    def test_watermark_never_goes_backward(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=20.0))
        assert agg.get_watermark() == pytest.approx(20.0)
        with pytest.raises(LateEventDroppedError):
            agg.on_event(Event(timestamp=5.0))
        assert agg.get_watermark() == pytest.approx(20.0)

    def test_empty_window_does_not_fire(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=25.0))
        results = agg.advance_watermark(30.0)
        assert len(results) == 1
        assert results[0].window.start == 20.0

    def test_with_watermark_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=2.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_watermark() == pytest.approx(3.0)

        agg.on_event(Event(timestamp=12.0))
        assert agg.get_watermark() == pytest.approx(10.0)
        state = agg.get_window_state(0.0)
        assert state is None

    def test_fired_window_state_flag_with_lateness(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)
        state = agg.get_window_state(0.0)
        assert state is not None
        assert state.fired is True

    def test_window_cleaned_up_after_lateness_period(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(12.0)
        assert agg.get_window_state(0.0) is not None

        agg.advance_watermark(15.0)
        assert agg.get_window_state(0.0) is None


class TestTumblingWindowLateEvents:
    def test_late_event_within_lateness_triggers_recompute(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)
        state = agg.get_window_state(0.0)
        assert state.fired is True
        assert state.count == 1

        results = agg.on_event(Event(timestamp=7.0))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) == 1
        assert late_results[0].window.start == 0.0
        assert late_results[0].value == 2

    def test_late_event_beyond_lateness_is_dropped(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=2.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(15.0)
        assert agg.dropped_late_count == 0

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=3.0))
        assert agg.dropped_late_count == 1
        assert agg.get_window_state(0.0) is None
        assert excinfo.value.event_timestamp == 3.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 2.0

    def test_event_exactly_at_lateness_boundary_is_dropped(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(15.0)

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=3.0))
        assert agg.dropped_late_count == 1
        assert excinfo.value.event_timestamp == 3.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 5.0

    def test_multiple_late_events_within_lateness(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=10.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(12.0)

        results1 = agg.on_event(Event(timestamp=3.0))
        late1 = [r for r in results1 if r.is_late_recompute]
        assert len(late1) == 1
        assert late1[0].value == 2

        results2 = agg.on_event(Event(timestamp=7.0))
        late2 = [r for r in results2 if r.is_late_recompute]
        assert len(late2) == 1
        assert late2[0].value == 3

    def test_late_event_window_already_cleaned(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=5.0))
        assert agg.dropped_late_count == 1
        assert agg.get_window_state(0.0) is None
        assert excinfo.value.event_timestamp == 5.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 0.0

    def test_late_event_at_window_boundary(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)

        results = agg.on_event(Event(timestamp=9.999))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) == 1
        assert late_results[0].value == 2

    def test_late_event_at_exactly_window_end(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)

        results = agg.on_event(Event(timestamp=10.0))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) == 0
        assert agg.get_window_state(10.0) is not None


class TestTumblingWindowAggregationTypes:
    def test_count_aggregation(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=1.0, value=10))
        agg.on_event(Event(timestamp=2.0, value=20))
        agg.on_event(Event(timestamp=3.0, value=30))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == 3

    def test_sum_aggregation(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
        )
        agg.on_event(Event(timestamp=1.0, value=10))
        agg.on_event(Event(timestamp=2.0, value=20))
        agg.on_event(Event(timestamp=3.0, value=30))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == pytest.approx(60.0)

    def test_avg_aggregation(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.AVG,
        )
        agg.on_event(Event(timestamp=1.0, value=10))
        agg.on_event(Event(timestamp=2.0, value=20))
        agg.on_event(Event(timestamp=3.0, value=30))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == pytest.approx(20.0)

    def test_min_aggregation(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.MIN,
        )
        agg.on_event(Event(timestamp=1.0, value=30))
        agg.on_event(Event(timestamp=2.0, value=10))
        agg.on_event(Event(timestamp=3.0, value=20))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == pytest.approx(10.0)

    def test_max_aggregation(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.MAX,
        )
        agg.on_event(Event(timestamp=1.0, value=30))
        agg.on_event(Event(timestamp=2.0, value=10))
        agg.on_event(Event(timestamp=3.0, value=20))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == pytest.approx(30.0)

    def test_count_with_none_values(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=1.0))
        agg.on_event(Event(timestamp=2.0))
        agg.on_event(Event(timestamp=3.0))

        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].value == 3


class TestTumblingWindowBoundary:
    def test_event_exactly_on_window_start(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        results = agg.on_event(Event(timestamp=0.0))
        state = agg.get_window_state(0.0)
        assert state.count == 1
        assert state.window.contains(0.0) is True

    def test_event_exactly_on_window_end(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=10.0))
        state = agg.get_window_state(10.0)
        assert state is not None
        assert state.count == 1
        assert agg.get_window_state(0.0) is None

    def test_very_small_window_size(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=0.1,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=0.05))
        agg.on_event(Event(timestamp=0.15))
        assert agg.get_active_window_count() == 2

    def test_large_window_size(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=1000.0,
            watermark_delay_seconds=10000.0,
        )
        agg.on_event(Event(timestamp=500.0))
        agg.on_event(Event(timestamp=1500.0))
        assert agg.get_active_window_count() == 2

    def test_single_window_with_all_events(self):
        agg = TumblingWindowAggregator(window_size_seconds=100.0)
        for i in range(100):
            agg.on_event(Event(timestamp=float(i)))
        state = agg.get_window_state(0.0)
        assert state.count == 100

    def test_every_event_in_own_window_with_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=1.0,
            watermark_delay_seconds=100.0,
        )
        for i in range(10):
            agg.on_event(Event(timestamp=float(i)))
        assert agg.get_active_window_count() == 10

    def test_watermark_exactly_equals_window_end(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=5.0))
        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].window.end == 10.0

    def test_watermark_just_before_window_end(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=5.0))
        results = agg.advance_watermark(9.999)
        assert len(results) == 0
        assert agg.get_window_state(0.0) is not None


class TestTumblingWindowEdgeCases:
    def test_no_events_no_windows(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        assert agg.get_active_window_count() == 0
        assert agg.get_watermark() == -1.0

    def test_get_nonexistent_window_state(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        assert agg.get_window_state(100.0) is None

    def test_advance_watermark_no_effect_when_already_ahead(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        agg.on_event(Event(timestamp=50.0))
        results = agg.advance_watermark(10.0)
        assert len(results) == 0
        assert agg.get_watermark() == pytest.approx(50.0)

    def test_get_all_window_states_with_delay(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=15.0))
        agg.on_event(Event(timestamp=25.0))
        states = agg.get_all_window_states()
        assert len(states) == 3
        starts = [s.window.start for s in states]
        assert 0.0 in starts
        assert 10.0 in starts
        assert 20.0 in starts

    def test_result_dataclass_fields(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
        )
        agg.on_event(Event(timestamp=5.0, value=42.0))
        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        result = results[0]
        assert isinstance(result.window, Window)
        assert result.agg_type == AggregationType.SUM
        assert result.value == pytest.approx(42.0)
        assert result.is_late_recompute is False

    def test_multiple_results_from_single_event(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=15.0))
        agg.on_event(Event(timestamp=25.0))

        results = agg.advance_watermark(50.0)
        assert len(results) == 3
        windows = sorted([r.window.start for r in results])
        assert windows == [0.0, 10.0, 20.0]

    def test_late_recompute_correct_value(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
            allowed_lateness_seconds=10.0,
        )
        agg.on_event(Event(timestamp=5.0, value=10.0))
        agg.advance_watermark(10.0)

        results = agg.on_event(Event(timestamp=7.0, value=20.0))
        late = [r for r in results if r.is_late_recompute]
        assert len(late) == 1
        assert late[0].value == pytest.approx(30.0)
        assert late[0].agg_type == AggregationType.SUM


class TestTumblingWindowLateEventDroppedError:
    def test_error_contains_correct_event_timestamp(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=5.0))
        assert excinfo.value.event_timestamp == 5.0

    def test_error_contains_correct_window_end(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=5.0))
        assert excinfo.value.window_end == 10.0

    def test_error_contains_correct_allowed_lateness(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=3.0,
        )
        agg.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError) as excinfo:
            agg.on_event(Event(timestamp=5.0))
        assert excinfo.value.allowed_lateness == 3.0

    def test_error_is_subclass_of_stream_window_error(self):
        from solocoder_py.stream_window import StreamWindowError

        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=20.0))

        with pytest.raises(StreamWindowError):
            agg.on_event(Event(timestamp=5.0))

    def test_error_message_contains_details(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=2.0,
        )
        agg.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError, match="Event at 5.0 dropped"):
            agg.on_event(Event(timestamp=5.0))


class TestTumblingWindowDroppedLateCountSemantics:
    def test_single_dropped_event_counts_as_one(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=20.0))
        assert agg.dropped_late_count == 0

        with pytest.raises(LateEventDroppedError):
            agg.on_event(Event(timestamp=5.0))
        assert agg.dropped_late_count == 1

    def test_multiple_dropped_events_counted_individually(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=50.0))

        with pytest.raises(LateEventDroppedError):
            agg.on_event(Event(timestamp=5.0))
        with pytest.raises(LateEventDroppedError):
            agg.on_event(Event(timestamp=15.0))
        with pytest.raises(LateEventDroppedError):
            agg.on_event(Event(timestamp=25.0))
        assert agg.dropped_late_count == 3

    def test_non_dropped_events_do_not_affect_count(self):
        agg = TumblingWindowAggregator(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)
        assert agg.dropped_late_count == 0

        agg.on_event(Event(timestamp=7.0))
        assert agg.dropped_late_count == 0

    def test_count_starts_at_zero(self):
        agg = TumblingWindowAggregator(window_size_seconds=10.0)
        assert agg.dropped_late_count == 0
