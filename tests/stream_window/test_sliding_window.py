from __future__ import annotations

import pytest

from solocoder_py.stream_window import (
    AggregationResult,
    AggregationType,
    Event,
    InvalidWindowConfigError,
    SlidingWindowAggregator,
    Window,
)


class TestSlidingWindowCreation:
    def test_default_creation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        assert agg.window_size_seconds == 10.0
        assert agg.slide_seconds == 5.0
        assert agg.agg_type == AggregationType.COUNT
        assert agg.allowed_lateness_seconds == 0.0
        assert agg.watermark_delay_seconds == 0.0
        assert agg.get_active_window_count() == 0
        assert agg.dropped_late_count == 0

    def test_slide_equals_window_size(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=10.0,
        )
        assert agg.slide_seconds == 10.0

    def test_with_custom_agg_type(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.SUM,
        )
        assert agg.agg_type == AggregationType.SUM

    def test_with_allowed_lateness(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            allowed_lateness_seconds=3.0,
        )
        assert agg.allowed_lateness_seconds == 3.0

    def test_with_watermark_delay(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=2.0,
        )
        assert agg.watermark_delay_seconds == 2.0

    def test_zero_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            SlidingWindowAggregator(window_size_seconds=0.0, slide_seconds=5.0)

    def test_negative_window_size_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="window_size_seconds must be positive"):
            SlidingWindowAggregator(window_size_seconds=-10.0, slide_seconds=5.0)

    def test_zero_slide_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="slide_seconds must be positive"):
            SlidingWindowAggregator(window_size_seconds=10.0, slide_seconds=0.0)

    def test_negative_slide_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="slide_seconds must be positive"):
            SlidingWindowAggregator(window_size_seconds=10.0, slide_seconds=-5.0)

    def test_slide_greater_than_window_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="slide_seconds must be <= window_size_seconds"):
            SlidingWindowAggregator(window_size_seconds=10.0, slide_seconds=15.0)

    def test_negative_allowed_lateness_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="allowed_lateness_seconds must be non-negative"):
            SlidingWindowAggregator(
                window_size_seconds=10.0,
                slide_seconds=5.0,
                allowed_lateness_seconds=-1.0,
            )

    def test_negative_watermark_delay_raises(self):
        with pytest.raises(InvalidWindowConfigError, match="watermark_delay_seconds must be non-negative"):
            SlidingWindowAggregator(
                window_size_seconds=10.0,
                slide_seconds=5.0,
                watermark_delay_seconds=-1.0,
            )


class TestSlidingWindowAssignment:
    def test_event_belongs_to_multiple_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=7.0))
        assert agg.get_active_window_count() == 2
        assert agg.get_window_state(0.0) is not None
        assert agg.get_window_state(5.0) is not None
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(5.0).count == 1

    def test_event_at_window_start_boundary(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_active_window_count() == 2
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(5.0).count == 1

    def test_event_at_window_end_boundary(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=10.0))
        assert agg.get_active_window_count() == 2
        assert agg.get_window_state(5.0).count == 1
        assert agg.get_window_state(10.0).count == 1
        assert agg.get_window_state(0.0) is None

    def test_event_at_zero(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=0.0))
        assert agg.get_active_window_count() == 1
        assert agg.get_window_state(0.0).count == 1

    def test_half_overlap(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=3.0))
        assert agg.get_active_window_count() == 1
        agg.on_event(Event(timestamp=7.0))
        assert agg.get_window_state(0.0).count == 2
        assert agg.get_window_state(5.0).count == 1

    def test_events_spread_across_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=2.0))
        agg.on_event(Event(timestamp=7.0))
        agg.on_event(Event(timestamp=12.0))
        assert agg.get_active_window_count() == 3
        assert agg.get_window_state(0.0).count == 2
        assert agg.get_window_state(5.0).count == 2
        assert agg.get_window_state(10.0).count == 1

    def test_many_overlapping_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=2.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=9.0))
        assert agg.get_active_window_count() == 5

    def test_slide_equals_window_no_overlap(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_active_window_count() == 1
        assert agg.get_window_state(0.0).count == 1

    def test_slide_equals_window_behaves_like_tumbling(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=10.0,
            agg_type=AggregationType.COUNT,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.on_event(Event(timestamp=15.0))
        assert agg.get_active_window_count() == 2
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(10.0).count == 1

        results = agg.advance_watermark(20.0)
        assert len(results) == 2

    def test_late_timestamp_creates_correct_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=100.0))
        assert agg.get_active_window_count() == 2
        assert agg.get_window_state(95.0) is not None
        assert agg.get_window_state(100.0) is not None


class TestSlidingWindowWatermarkAndFiring:
    def test_watermark_advances_with_events(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_watermark() == pytest.approx(5.0)
        agg.on_event(Event(timestamp=20.0))
        assert agg.get_watermark() == pytest.approx(20.0)

    def test_window_fires_when_watermark_passes_end(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=5.0))
        results = agg.advance_watermark(10.0)
        assert len(results) == 1
        assert results[0].window.start == 0.0
        assert results[0].window.end == 10.0
        assert results[0].value == 1

    def test_multiple_windows_fire_at_once(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=2.0))
        agg.on_event(Event(timestamp=7.0))
        assert agg.get_active_window_count() == 2

        results = agg.advance_watermark(20.0)
        assert len(results) == 2

    def test_fired_windows_cleaned_up_when_no_lateness(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)
        assert agg.get_window_state(0.0) is None
        assert agg.get_window_state(5.0) is not None

    def test_with_watermark_delay(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=2.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_watermark() == pytest.approx(3.0)

        agg.on_event(Event(timestamp=12.0))
        assert agg.get_watermark() == pytest.approx(10.0)
        assert agg.get_window_state(0.0) is None

    def test_empty_window_does_not_fire(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        agg.on_event(Event(timestamp=25.0))
        results = agg.advance_watermark(30.0)
        fired_starts = [r.window.start for r in results]
        assert 20.0 in fired_starts
        assert 15.0 not in fired_starts

    def test_window_stays_after_fire_with_lateness(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(10.0)
        assert agg.get_window_state(0.0) is not None
        assert agg.get_window_state(0.0).fired is True

    def test_window_cleaned_up_after_lateness(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(12.0)
        assert agg.get_window_state(0.0) is not None

        agg.advance_watermark(15.0)
        assert agg.get_window_state(0.0) is None


class TestSlidingWindowLateEvents:
    def test_late_event_within_lateness_triggers_recompute(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=7.0))
        agg.advance_watermark(10.0)

        assert agg.get_window_state(0.0).fired is True

        results = agg.on_event(Event(timestamp=3.0))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) == 1
        assert late_results[0].window.start == 0.0
        assert late_results[0].value == 2

    def test_late_event_in_multiple_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=2.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=9.0))
        agg.advance_watermark(10.0)

        fired_count = sum(1 for s in agg.get_all_window_states() if s.fired)
        assert fired_count >= 1

        results = agg.on_event(Event(timestamp=3.0))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) >= 1

    def test_late_event_beyond_lateness_is_dropped(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=2.0,
        )
        agg.on_event(Event(timestamp=5.0))
        agg.advance_watermark(15.0)
        initial_dropped = agg.dropped_late_count

        agg.on_event(Event(timestamp=3.0))
        assert agg.dropped_late_count > initial_dropped

    def test_late_event_counted_per_window(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            allowed_lateness_seconds=0.0,
        )
        agg.on_event(Event(timestamp=20.0))
        initial_dropped = agg.dropped_late_count
        agg.on_event(Event(timestamp=5.0))
        assert agg.dropped_late_count > initial_dropped

    def test_late_recompute_updates_value(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
        )
        agg.on_event(Event(timestamp=3.0))
        agg.advance_watermark(10.0)
        state = agg.get_window_state(0.0)
        assert state.fired is True

        results = agg.on_event(Event(timestamp=5.0))
        late_results = [r for r in results if r.is_late_recompute]
        assert len(late_results) == 1
        assert late_results[0].value == 2


class TestSlidingWindowAggregationTypes:
    def test_count_aggregation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.COUNT,
        )
        agg.on_event(Event(timestamp=3.0, value=10))
        agg.on_event(Event(timestamp=7.0, value=20))

        results = agg.advance_watermark(10.0)
        first_window = [r for r in results if r.window.start == 0.0][0]
        assert first_window.value == 2

    def test_sum_aggregation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.SUM,
        )
        agg.on_event(Event(timestamp=3.0, value=10))
        agg.on_event(Event(timestamp=7.0, value=20))

        results = agg.advance_watermark(10.0)
        first_window = [r for r in results if r.window.start == 0.0][0]
        assert first_window.value == pytest.approx(30.0)

    def test_avg_aggregation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.AVG,
        )
        agg.on_event(Event(timestamp=3.0, value=10))
        agg.on_event(Event(timestamp=7.0, value=30))

        results = agg.advance_watermark(10.0)
        first_window = [r for r in results if r.window.start == 0.0][0]
        assert first_window.value == pytest.approx(20.0)

    def test_min_aggregation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.MIN,
        )
        agg.on_event(Event(timestamp=3.0, value=30))
        agg.on_event(Event(timestamp=7.0, value=10))

        results = agg.advance_watermark(10.0)
        first_window = [r for r in results if r.window.start == 0.0][0]
        assert first_window.value == pytest.approx(10.0)

    def test_max_aggregation(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.MAX,
        )
        agg.on_event(Event(timestamp=3.0, value=30))
        agg.on_event(Event(timestamp=7.0, value=10))

        results = agg.advance_watermark(10.0)
        first_window = [r for r in results if r.window.start == 0.0][0]
        assert first_window.value == pytest.approx(30.0)


class TestSlidingWindowBoundary:
    def test_event_exactly_on_slide_boundary(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(5.0).count == 1

    def test_event_just_before_window_end(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=9.999))
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(5.0).count == 1

    def test_event_just_after_window_start(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.001))
        assert agg.get_window_state(0.0).count == 1
        assert agg.get_window_state(5.0).count == 1

    def test_watermark_exactly_at_window_end(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        agg.on_event(Event(timestamp=3.0))
        results = agg.advance_watermark(10.0)
        assert len(results) >= 1
        assert any(r.window.end == 10.0 for r in results)

    def test_very_small_slide(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=1.0,
            slide_seconds=0.2,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=0.9))
        assert agg.get_active_window_count() == 5

    def test_large_window_small_slide(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=1.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=9.0))
        assert agg.get_active_window_count() == 10


class TestSlidingWindowEdgeCases:
    def test_no_events_no_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        assert agg.get_active_window_count() == 0
        assert agg.get_watermark() == -1.0

    def test_get_nonexistent_window_state(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
        )
        assert agg.get_window_state(100.0) is None

    def test_get_all_window_states(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=7.0))
        states = agg.get_all_window_states()
        assert len(states) == 2
        starts = [s.window.start for s in states]
        assert 0.0 in starts
        assert 5.0 in starts

    def test_result_has_correct_type(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            agg_type=AggregationType.SUM,
        )
        agg.on_event(Event(timestamp=5.0, value=42.0))
        results = agg.advance_watermark(10.0)
        assert len(results) >= 1
        assert isinstance(results[0], AggregationResult)
        assert results[0].agg_type == AggregationType.SUM
        assert results[0].value == pytest.approx(42.0)

    def test_single_event_counted_in_all_containing_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=2.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=5.0))
        states = agg.get_all_window_states()
        for state in states:
            assert state.count == 1
        assert len(states) == 3
        starts = sorted(s.window.start for s in states)
        assert starts == [0.0, 2.0, 4.0]

    def test_event_at_exact_window_end_belongs_to_next_windows(self):
        agg = SlidingWindowAggregator(
            window_size_seconds=10.0,
            slide_seconds=5.0,
            watermark_delay_seconds=100.0,
        )
        agg.on_event(Event(timestamp=10.0))
        assert agg.get_window_state(0.0) is None
        assert agg.get_window_state(5.0).count == 1
        assert agg.get_window_state(10.0).count == 1
