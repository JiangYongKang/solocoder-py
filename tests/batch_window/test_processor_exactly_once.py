from __future__ import annotations

import pytest

from solocoder_py.batch_window import (
    AggregationResult,
    AggregationType,
    BatchWindowProcessor,
    Event,
    LateEventDroppedError,
    OutputType,
)
from solocoder_py.batch_window.source import MemoryEventSource


class TestBatchWindowProcessorExactlyOnceSemantics:
    def test_final_output_emitted_only_once_no_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=7.0))

        results = proc.advance_watermark(10.0)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 1
        assert final_results[0].value == 2
        assert proc.get_final_output_count() == 1

        results2 = proc.advance_watermark(20.0)
        final_results2 = [r for r in results2 if r.is_final and r.window.start == 0.0]
        assert len(final_results2) == 0
        assert proc.get_final_output_count() == 1

    def test_final_output_emitted_only_once_with_lateness(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=7.0))

        intermediate_results = proc.advance_watermark(10.0)
        intermediates = [r for r in intermediate_results if r.is_intermediate]
        assert len(intermediates) == 1
        assert intermediates[0].value == 2
        assert intermediates[0].output_type == OutputType.INTERMEDIATE
        assert proc.get_final_output_count() == 0

        proc.on_event(Event(timestamp=3.0))
        proc.on_event(Event(timestamp=8.0))

        final_results = proc.advance_watermark(15.0)
        finals = [r for r in final_results if r.is_final]
        assert len(finals) == 1
        assert finals[0].value == 4
        assert finals[0].output_type == OutputType.FINAL
        assert proc.get_final_output_count() == 1

        results_after = proc.advance_watermark(30.0)
        finals_after = [r for r in results_after if r.is_final and r.window.start == 0.0]
        assert len(finals_after) == 0
        assert proc.get_final_output_count() == 1

    def test_intermediate_updates_show_cumulative_values(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.SUM,
            allowed_lateness_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0, value=10.0))

        r1 = proc.advance_watermark(10.0)
        inter1 = [x for x in r1 if x.is_intermediate]
        assert len(inter1) == 1
        assert inter1[0].value == pytest.approx(10.0)

        r2 = proc.on_event(Event(timestamp=3.0, value=20.0))
        inter2 = [x for x in r2 if x.is_intermediate and x.is_late_update]
        assert len(inter2) == 1
        assert inter2[0].value == pytest.approx(30.0)

        r3 = proc.on_event(Event(timestamp=7.0, value=15.0))
        inter3 = [x for x in r3 if x.is_intermediate and x.is_late_update]
        assert len(inter3) == 1
        assert inter3[0].value == pytest.approx(45.0)

        r4 = proc.advance_watermark(20.0)
        final = [x for x in r4 if x.is_final]
        assert len(final) == 1
        assert final[0].value == pytest.approx(45.0)

    def test_distinguish_intermediate_and_final(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))

        r1 = proc.advance_watermark(10.0)
        assert len(r1) == 1
        assert r1[0].is_intermediate is True
        assert r1[0].is_final is False
        assert r1[0].is_late_update is False

        proc.on_event(Event(timestamp=7.0))

        r2 = proc.advance_watermark(15.0)
        assert len(r2) == 1
        assert r2[0].is_intermediate is False
        assert r2[0].is_final is True
        assert r2[0].is_late_update is True

    def test_multiple_windows_each_final_once(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        all_results = []
        all_results.extend(proc.on_event(Event(timestamp=5.0)))
        all_results.extend(proc.on_event(Event(timestamp=15.0)))
        all_results.extend(proc.on_event(Event(timestamp=25.0)))
        all_results.extend(proc.advance_watermark(50.0))

        final_results = [r for r in all_results if r.is_final]
        assert len(final_results) == 3
        assert proc.get_final_output_count() == 3
        window_starts = sorted([r.window.start for r in final_results])
        assert window_starts == [0.0, 10.0, 20.0]

        results2 = proc.advance_watermark(100.0)
        final_results2 = [r for r in results2 if r.is_final]
        assert len(final_results2) == 0
        assert proc.get_final_output_count() == 3

    def test_window_closed_no_more_events_accepted(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=7.0))

        assert proc.get_window_state(0.0) is None
        assert proc.get_final_output_count() == 1

    def test_get_final_output_windows(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=25.0))
        proc.advance_watermark(50.0)

        final_windows = proc.get_final_output_windows()
        assert len(final_windows) >= 1
        starts = [w.start for w in final_windows]
        assert 20.0 in starts


class TestBatchWindowProcessorReset:
    def test_reset_clears_all_state(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=2.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=15.0))
        proc.dropped_late_count

        proc.reset()
        assert proc.get_active_window_count() == 0
        assert proc.dropped_late_count == 0
        assert proc.rejected_closed_count == 0
        assert proc.get_final_output_count() == 0
        assert proc.get_watermark() == -1.0
        assert proc.watermark_delay_seconds == 2.0
        assert proc.allowed_lateness_seconds == 5.0


class TestBatchWindowProcessorProcessSource:
    def test_process_source_all_events(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        source = MemoryEventSource()
        source.add_events([
            Event(timestamp=1.0),
            Event(timestamp=5.0),
            Event(timestamp=12.0),
            Event(timestamp=15.0),
        ])

        results = proc.process_source(source)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) == 2
        window_values = {r.window.start: r.value for r in final_results}
        assert window_values[0.0] == 2
        assert window_values[10.0] == 2

    def test_process_source_handles_late_events_gracefully(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            agg_type=AggregationType.COUNT,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        source = MemoryEventSource()
        source.add_events([
            Event(timestamp=25.0),
            Event(timestamp=5.0),
            Event(timestamp=15.0),
            Event(timestamp=3.0),
        ])

        results = proc.process_source(source)
        final_results = [r for r in results if r.is_final]
        assert len(final_results) >= 1
        assert proc.dropped_late_count >= 2


class TestBatchWindowProcessorDroppedCount:
    def test_single_dropped_event_counts_as_one(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=20.0))
        assert proc.dropped_late_count == 0

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))
        assert proc.dropped_late_count == 1

    def test_multiple_dropped_events_counted_individually(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=50.0))

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=5.0))
        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=15.0))
        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=25.0))
        assert proc.dropped_late_count == 3

    def test_non_dropped_events_do_not_affect_count(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=5.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)
        assert proc.dropped_late_count == 0

        proc.on_event(Event(timestamp=7.0))
        assert proc.dropped_late_count == 0


class TestBatchWindowProcessorErrorAttributes:
    def test_late_event_dropped_error_attributes(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=3.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError) as excinfo:
            proc.on_event(Event(timestamp=5.0))
        assert excinfo.value.event_timestamp == 5.0
        assert excinfo.value.window_end == 10.0
        assert excinfo.value.allowed_lateness == 3.0

    def test_late_event_dropped_error_message(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=2.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=20.0))

        with pytest.raises(LateEventDroppedError, match="Event at 5.0 dropped"):
            proc.on_event(Event(timestamp=5.0))
