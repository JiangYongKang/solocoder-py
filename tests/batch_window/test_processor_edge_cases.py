from __future__ import annotations

import pytest

from solocoder_py.batch_window import (
    AggregationType,
    BatchWindowProcessor,
    BatchWindowError,
    Event,
    InvalidWindowConfigError,
    LateEventDroppedError,
    WindowAlreadyClosedError,
)
from solocoder_py.batch_window.exceptions import BatchWindowError as BaseError


class TestBatchWindowProcessorExceptionHierarchy:
    def test_late_event_dropped_is_subclass_of_batch_window_error(self):
        assert issubclass(LateEventDroppedError, BatchWindowError)

    def test_invalid_config_is_subclass_of_batch_window_error(self):
        assert issubclass(InvalidWindowConfigError, BatchWindowError)

    def test_window_already_closed_is_subclass_of_batch_window_error(self):
        assert issubclass(WindowAlreadyClosedError, BatchWindowError)

    def test_catch_base_exception_catches_all(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=20.0))
        with pytest.raises(BaseError):
            proc.on_event(Event(timestamp=5.0))


class TestBatchWindowProcessorInvalidConfig:
    def test_window_size_zero_invalid(self):
        with pytest.raises(InvalidWindowConfigError):
            BatchWindowProcessor(window_size_seconds=0.0)

    def test_window_size_negative_invalid(self):
        with pytest.raises(InvalidWindowConfigError):
            BatchWindowProcessor(window_size_seconds=-10.0)

    def test_allowed_lateness_negative_invalid(self):
        with pytest.raises(InvalidWindowConfigError):
            BatchWindowProcessor(
                window_size_seconds=10.0,
                allowed_lateness_seconds=-1.0,
            )

    def test_watermark_delay_negative_invalid(self):
        with pytest.raises(InvalidWindowConfigError):
            BatchWindowProcessor(
                window_size_seconds=10.0,
                watermark_delay_seconds=-5.0,
            )


class TestBatchWindowProcessorWatermarkRegressionDefense:
    def test_watermark_does_not_go_backward_on_old_events(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=50.0))
        watermark_before = proc.get_watermark()
        assert watermark_before == pytest.approx(50.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=10.0))

        assert proc.get_watermark() == pytest.approx(50.0)

    def test_advance_watermark_does_not_go_backward(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=50.0))
        watermark_before = proc.get_watermark()

        proc.advance_watermark(10.0)
        assert proc.get_watermark() == watermark_before

    def test_observe_event_does_not_regress_max_event_time(self):
        from solocoder_py.batch_window.watermark import WatermarkGenerator

        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(100.0)
        max_before = gen.max_event_time

        gen.observe_event(50.0)
        assert gen.max_event_time == max_before
        assert gen.get_watermark() == pytest.approx(100.0)


class TestBatchWindowProcessorWindowClosedRejection:
    def test_events_to_closed_window_are_rejected(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=7.0))

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=3.0))

        with pytest.raises(LateEventDroppedError):
            proc.on_event(Event(timestamp=9.999))

    def test_multiple_events_to_closed_window_all_rejected(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        rejected_count = 0
        for ts in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]:
            try:
                proc.on_event(Event(timestamp=ts))
            except LateEventDroppedError:
                rejected_count += 1

        assert rejected_count == 9
        assert proc.dropped_late_count == 9

    def test_closed_window_state_cleaned(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=0.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.advance_watermark(10.0)

        assert proc.get_window_state(0.0) is None
        assert proc.get_active_window_count() == 0


class TestBatchWindowProcessorHighOutOfOrder:
    def test_extreme_out_of_order_beyond_watermark_delay(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=1.0,
        )
        proc.on_event(Event(timestamp=100.0))
        assert proc.get_watermark() == pytest.approx(99.0)

        for ts in range(0, 90):
            with pytest.raises(LateEventDroppedError):
                proc.on_event(Event(timestamp=float(ts)))

        assert proc.dropped_late_count == 90

    def test_out_of_order_within_watermark_delay_handled(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            allowed_lateness_seconds=0.0,
            watermark_delay_seconds=20.0,
        )
        proc.on_event(Event(timestamp=25.0))
        assert proc.get_watermark() == pytest.approx(5.0)

        results = proc.on_event(Event(timestamp=5.0))
        assert proc.get_window_state(0.0) is not None
        assert proc.get_window_state(0.0).count == 1


class TestBatchWindowProcessorEdgeCases:
    def test_no_events_no_windows(self):
        proc = BatchWindowProcessor(window_size_seconds=10.0)
        assert proc.get_active_window_count() == 0
        assert proc.get_watermark() == -1.0

    def test_get_nonexistent_window_state(self):
        proc = BatchWindowProcessor(window_size_seconds=10.0)
        assert proc.get_window_state(100.0) is None

    def test_get_all_window_states(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=100.0,
        )
        proc.on_event(Event(timestamp=5.0))
        proc.on_event(Event(timestamp=15.0))
        proc.on_event(Event(timestamp=25.0))
        states = proc.get_all_window_states()
        assert len(states) == 3
        starts = [s.window.start for s in states]
        assert 0.0 in starts
        assert 10.0 in starts
        assert 20.0 in starts

    def test_event_with_negative_timestamp_rejected(self):
        proc = BatchWindowProcessor(
            window_size_seconds=10.0,
            watermark_delay_seconds=0.0,
        )
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            Event(timestamp=-1.0)

    def test_final_output_windows_empty(self):
        proc = BatchWindowProcessor(window_size_seconds=10.0)
        assert proc.get_final_output_windows() == []

    def test_large_window_size(self):
        proc = BatchWindowProcessor(
            window_size_seconds=1000.0,
            watermark_delay_seconds=10000.0,
        )
        proc.on_event(Event(timestamp=500.0))
        proc.on_event(Event(timestamp=1500.0))
        assert proc.get_active_window_count() == 2

    def test_single_window_all_events(self):
        proc = BatchWindowProcessor(
            window_size_seconds=100.0,
            watermark_delay_seconds=1000.0,
        )
        for i in range(100):
            proc.on_event(Event(timestamp=float(i)))
        state = proc.get_window_state(0.0)
        assert state.count == 100

    def test_every_event_in_own_window(self):
        proc = BatchWindowProcessor(
            window_size_seconds=1.0,
            watermark_delay_seconds=100.0,
        )
        for i in range(10):
            proc.on_event(Event(timestamp=float(i)))
        assert proc.get_active_window_count() == 10
