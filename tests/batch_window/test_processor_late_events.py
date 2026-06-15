from __future__ import annotations

import pytest

from solocoder_py.batch_window import (
    AggregationResult,
    AggregationType,
    BatchWindowProcessor,
    Event,
    LateEventDroppedError,
    OutputType,
    WindowAlreadyClosedError,
)


class TestBatchWindowProcessorLateEventsWithLateness:
    def test_late_event_within_lateness_triggers_intermediate_update(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)
        state = proc.get_window_state(0.0)
        assert state.is_fired is True
        assert state.count == 1

        results = proc.on_event(Event(timestamp=7.0))
        intermediate_results = [r for r in results if r.is_intermediate and r.is_late_update]
        assert len(intermediate_results) == 1
        assert intermediate_results[0].window.start == 0.0
        assert intermediate_results[0].value == 2
        assert intermediate_results[0].output_type == OutputType.INTERMEDIATE
        assert intermediate_results[0].is_late_update is True

    def test_late_event_beyond_lateness_is_dropped(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=2.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(15.0)
        assert proc.dropped_late_count == 0

        with pytest.raises(LateEventDroppedError) as excinfo:
            proc.on_event(Event(timestamp=3.0))
        assert proc.dropped_late_count == 1
        assert proc.get_window_state(0.0) is None
        assert excinfo.value.event_timestamp == 3.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 2.0

    def test_event_exactly_at_lateness_boundary_is_dropped(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(15.0)

        with pytest.raises(LateEventDroppedError) as excinfo:
            proc.on_event(Event(timestamp=3.0))
        assert proc.dropped_late_count == 1
        assert excinfo.value.event_timestamp == 3.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 5.0

    def test_event_just_within_lateness_boundary_is_accepted(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(14.999)

        results = proc.on_event(Event(timestamp=7.0))
        intermediate_results = [r for r in results if r.is_intermediate and r.is_late_update]
        assert len(intermediate_results) == 1
        assert proc.dropped_late_count == 0

    def test_multiple_late_events_within_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(12.0)

        results1 = proc.on_event(Event(timestamp=3.0))
        late1 = [r for r in results1 if r.is_late_update]
        assert len(late1) == 1
        assert late1[0].value == 2

        results2 = proc.on_event(Event(timestamp=7.0))
        late2 = [r for r in results2 if r.is_late_update]
        assert len(late2) == 1
        assert late2[0].value == 3

    def test_late_event_at_window_boundary_within_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            agg_type=AggregationType.COUNT,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        results = proc.on_event(Event(timestamp=9.999))
        late_results = [r for r in results if r.is_late_update]
        assert len(late_results) == 1
        assert late_results[0].value == 2

    def test_late_event_at_exactly_window_end_belongs_to_next(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            agg_type=AggregationType.COUNT,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        results = proc.on_event(Event(timestamp=10.0))
        late_results = [r for r in results if r.is_late_update]
        assert len(late_results) == 0
        assert proc.get_window_state(10.0) is not None

    def test_sum_aggregation_with_late_updates(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0, value=10.0))
        proc.advance_watermark(10.0)

        results = proc.on_event(Event(timestamp=7.0, value=20.0))
        late = [r for r in results if r.is_late_update]
        assert len(late) == 1
        assert late[0].value == pytest.approx(30.0)
        assert late[0].agg_type == AggregationType.SUM


class TestBatchWindowProcessorLateEventsZeroLateness:
    def test_allowed_lateness_zero_all_late_dropped(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        with pytest.raises(LateEventDroppedError) as excinfo:
            proc.on_event(Event(timestamp=5.0))
        assert proc.dropped_late_count == 1
        assert proc.get_window_state(0.0) is None
        assert excinfo.value.event_timestamp == 5.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 0.0

    def test_allowed_lateness_zero_event_at_window_end_dropped(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=9.999))
        assert proc.dropped_late_count == 1


class TestBatchWindowProcessorThreeLatePaths:
    def test_path1_late_event_within_lateness_triggers_update(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)
        state = proc.get_window_state(0.0)
        assert state.is_fired is True
        assert state.is_closed is False

        results = proc.on_event(Event(timestamp=3.0))
        late_updates = [r for r in results if r.is_late_update]
        assert len(late_updates) == 1
        assert late_updates[0].value == 2
        assert proc.dropped_late_count == 0

    def test_path2_late_event_beyond_lateness_dropped(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=2.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(20.0)
        assert proc.get_window_state(0.0) is None

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))
        assert proc.dropped_late_count == 1

    def test_path3_window_already_closed_rejected(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(15.0)
        assert proc.get_window_state(0.0) is None

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))

        proc.on_event(Event(timestamp=25.0))
        proc.advance_watermark(35.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=22.0))


class TestBatchWindowProcessorOutOfOrderExtreme:
    def test_event_time_out_of_order_within_watermark_delay(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=10.0,
        )
        proc.on_event(Event(timestamp=20.0))
        assert proc.get_watermark() == pytest.approx(10.0)

        proc.on_event(Event(timestamp=5.0))
        state0 = proc.get_window_state(0.0)
        state20 = proc.get_window_state(20.0)
        assert state0 is not None
        assert state0.count == 1
        assert state20 is not None
        assert state20.count == 1

    def test_event_time_out_of_order_exceeding_watermark_delay(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=2.0,
        )
        proc.on_event(Event(timestamp=20.0))
        assert proc.get_watermark() == pytest.approx(18.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))
        assert proc.dropped_late_count == 1

    def test_massive_out_of_order_all_dropped_after_closure(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=100.0))

        for i in range(10):
            with pytest.raises(LateEventDroppedError):
                proc.on_event(Event(timestamp=float(i)))
        assert proc.dropped_late_count == 10
