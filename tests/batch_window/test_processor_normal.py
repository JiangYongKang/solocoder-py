from __future__ import annotations

import pytest

from solocoder_py.batch_window import (
    AggregationResult,
    AggregationType,
    BatchWindowProcessor,
    Event,
    InvalidWindowConfigError,
    LateEventDroppedError,
    OutputType,
    Window,
    WindowAlreadyClosedError,
)


class TestBatchWindowProcessorCreation:
    def test_default_creation(self):
        proc = BatchWindowProcessor(window_size_seconds=10.0)
        assert proc.window_size_seconds == 10.0
        assert proc.agg_type == AggregationType.COUNT
        assert proc.allowed_lateness_seconds == 0.0
        assert proc.watermark_delay_seconds == 5.0
        assert proc.get_active_window_count() == 0
        assert proc.dropped_late_count == 0
        assert proc.rejected_closed_count == 0

    def test_custom_agg_type(self):
        proc = BatchWindowProcessor(
            window_size_seconds=5.0,
            agg_type=AggregationType.SUM,
        )
        assert proc.agg_type == AggregationType.SUM

    def test_with_allowed_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
        )
        assert proc.allowed_lateness_seconds == 5.0

    def test_with_watermark_delay(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=2.0,
        )
        assert proc.watermark_delay_seconds == 2.0

    def test_zero_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            BatchWindowProcessor(window_size_seconds=0.0)

    def test_negative_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            BatchWindowProcessor(window_size_seconds=-5.0)

    def test_negative_allowed_lateness_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="allowed_lateness_seconds must be non-negative"):
            BatchWindowProcessor(
                window_size_seconds=10.0,
                allowed_lateness_seconds=-1.0,
            )

    def test_negative_watermark_delay_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="watermark_delay_seconds must be non-negative"):
            BatchWindowProcessor(
                window_size_seconds=10.0,
                watermark_delay_seconds=-1.0,
            )


class TestBatchWindowProcessorNormalFlow:
    def test_event_in_first_window_no_output(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        results = proc.on_event(Event(timestamp=5.0))
        assert proc.get_active_window_count() == 1
        state = proc.get_window_state(0.0)
        assert state is not None
        assert state.count == 1
        assert state.window.start == 0.0
        assert state.window.end == 10.0
        assert len(results) == 0

    def test_window_fires_when_watermark_passes_end_no_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        assert proc.get_active_window_count() == 1

        results = proc.on_event(Event(timestamp=10.0))
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].window.start == 0.0
        assert final_results[0].window.end == 10.0
        assert final_results[0].value == 1
        assert final_results[0].output_type == OutputType.FINAL
        assert final_results[0].is_late_update is False

    def test_fired_window_cleaned_up_when_no_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=10.0))
        assert proc.get_window_state(0.0) is None
        assert proc.get_active_window_count() == 1

    def test_watermark_advances_with_events_default_delay(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=5.0,
        )
        proc.on_event(Event(timestamp=10.0))
        assert proc.get_watermark() == pytest.approx(5.0)
        proc.on_event(Event(timestamp=20.0))
        assert proc.get_watermark() == pytest.approx(15.0)

    def test_multiple_events_same_window(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=1.0))
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=9.0))
        state = proc.get_window_state(0.0)
        assert state.count == 3
        assert proc.get_active_window_count() == 1

    def test_events_in_different_windows(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=15.0))
        proc.on_event(Event(timestamp=25.0))
        assert proc.get_active_window_count() == 3
        assert proc.get_window_state(0.0).count == 1
        assert proc.get_window_state(10.0).count == 1
        assert proc.get_window_state(20.0).count == 1

    def test_events_in_different_windows_fire_in_order_no_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        r1 = proc.on_event(Event(timestamp=5.0))
        assert len(r1) == 0

        r2 = proc.on_event(Event(timestamp=15.0))
        final_r2 = [r for r in r2 if r.is_final]
        assert len(final_r2) == 1
        assert final_r2[0].window.start == 0.0
        assert final_r2[0].value == 1

        r3 = proc.on_event(Event(timestamp=25.0))
        final_r3 = [r for r in r3 if r.is_final]
        assert len(final_r3) == 1
        assert final_r3[0].window.start == 10.0
        assert final_r3[0].value == 1

    def test_sum_aggregation(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=1.0, value=10))
        proc.on_event(Event(timestamp=2.0, value=20))
        proc.on_event(Event(timestamp=3.0, value=30))

        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].value == pytest.approx(60.0)

    def test_avg_aggregation(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.AVG,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=1.0, value=10))
        proc.on_event(Event(timestamp=2.0, value=20))
        proc.on_event(Event(timestamp=3.0, value=30))

        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].value == pytest.approx(20.0)

    def test_count_with_none_values(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=1.0))
        proc.on_event(Event(timestamp=2.0))
        proc.on_event(Event(timestamp=3.0))

        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].value == 3


class TestBatchWindowProcessorWindowAssignmentBoundary:
    def test_event_at_window_boundary_belongs_to_next_window(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=10.0))
        state = proc.get_window_state(10.0)
        assert state is not None
        assert state.count == 1
        assert state.window.start == 10.0
        assert state.window.end == 20.0
        assert proc.get_window_state(0.0) is None

    def test_event_at_zero(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=0.0))
        state = proc.get_window_state(0.0)
        assert state is not None
        assert state.count == 1

    def test_event_exactly_on_window_start(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=0.0))
        state = proc.get_window_state(0.0)
        assert state.count == 1
        assert state.window.contains(0.0) is True

    def test_event_exactly_on_window_end_belongs_to_next(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=10.0))
        state = proc.get_window_state(10.0)
        assert state is not None
        assert state.count == 1
        assert proc.get_window_state(0.0) is None

    def test_event_at_9_999_belongs_to_first_window(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=9.999))
        state = proc.get_window_state(0.0)
        assert state is not None
        assert state.count == 1

    def test_non_aligned_window_size(self):
        proc = BatchWindowProcessor(
            window_size_seconds=7.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=8.0))
        assert proc.get_active_window_count() == 2
        state0 = proc.get_window_state(0.0)
        state7 = proc.get_window_state(7.0)
        assert state0 is not None
        assert state0.count == 1
        assert state7 is not None
        assert state7.count == 1

    def test_very_small_window_size(self):
        proc = BatchWindowProcessor(
            window_size_seconds=0.1,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=0.05))
        proc.on_event(Event(timestamp=0.15))
        assert proc.get_active_window_count() == 2


class TestBatchWindowProcessorEmptyWindow:
    def test_empty_window_does_not_fire(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=25.0))
        results = proc.advance_watermark(30.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].window.start == 20.0

    def test_no_events_no_output(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        results = proc.advance_watermark(100.0)
        assert len(results) == 0
        assert proc.get_final_output_count() == 0

    def test_gap_in_windows_no_output_for_empty(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        all_results = []
        all_results.extend(proc.on_event(Event(timestamp=5.0)))
        all_results.extend(proc.on_event(Event(timestamp=35.0)))
        all_results.extend(proc.advance_watermark(50.0))
        final_results = [r for r in all_results if r.is_final]
        assert len(final_results) == 2
        window_starts = sorted([r.window.start for r in final_results])
        assert window_starts == [0.0, 30.0]


class TestBatchWindowProcessorWatermarkAdvance:
    def test_advance_watermark_fires_window(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=5.0))
        assert proc.get_active_window_count() == 1

        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].window.end == 10.0

    def test_advance_watermark_fires_multiple_windows(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=15.0))
        assert proc.get_active_window_count() == 2

        results = proc.advance_watermark(30.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 2

    def test_watermark_never_goes_backward(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=20.0))
        assert proc.get_watermark() == pytest.approx(20.0)
        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))
        assert proc.get_watermark() == pytest.approx(20.0)

    def test_advance_watermark_no_effect_when_already_ahead(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=50.0))
        results = proc.advance_watermark(10.0)
        assert len(results) == 0
        assert proc.get_watermark() == pytest.approx(50.0)

    def test_watermark_exactly_equals_window_end(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].window.end == 10.0

    def test_watermark_just_before_window_end_no_fire(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        results = proc.advance_watermark(9.999)
        assert len(results) == 0
        assert proc.get_window_state(0.0) is not None

    def test_default_watermark_delay_5_seconds(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
        )
        proc.on_event(Event(timestamp=5.0))
        assert proc.get_watermark() == pytest.approx(0.0)
        assert proc.get_window_state(0.0).is_fired is False

        proc.on_event(Event(timestamp=15.0))
        assert proc.get_watermark() == pytest.approx(10.0)
