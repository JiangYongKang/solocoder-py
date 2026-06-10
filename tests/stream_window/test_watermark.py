from __future__ import annotations

import pytest

from solocoder_py.stream_window import WatermarkGenerator


class TestWatermarkGeneratorCreation:
    def test_default_delay(self):
        gen = WatermarkGenerator()
        assert gen.delay_seconds == 0.0
        assert gen.max_event_time == -1.0

    def test_positive_delay(self):
        gen = WatermarkGenerator(delay_seconds=5.0)
        assert gen.delay_seconds == 5.0

    def test_zero_delay(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        assert gen.delay_seconds == 0.0

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError, match="delay_seconds must be non-negative"):
            WatermarkGenerator(delay_seconds=-1.0)

    def test_initial_watermark(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        assert gen.get_watermark() == -1.0


class TestWatermarkGeneratorObserveEvent:
    def test_first_event_sets_max(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(10.0)
        assert gen.max_event_time == 10.0
        assert gen.get_watermark() == pytest.approx(8.0)

    def test_later_event_advances_max(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(10.0)
        gen.observe_event(15.0)
        assert gen.max_event_time == 15.0
        assert gen.get_watermark() == pytest.approx(13.0)

    def test_earlier_event_does_not_retreat(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(10.0)
        gen.observe_event(5.0)
        assert gen.max_event_time == 10.0
        assert gen.get_watermark() == pytest.approx(8.0)

    def test_event_at_zero(self):
        gen = WatermarkGenerator(delay_seconds=1.0)
        gen.observe_event(0.0)
        assert gen.max_event_time == 0.0
        assert gen.get_watermark() == pytest.approx(-1.0)

    def test_negative_timestamp_raises(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            gen.observe_event(-5.0)

    def test_observe_returns_watermark(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        result = gen.observe_event(10.0)
        assert result == pytest.approx(8.0)

    def test_zero_delay_watermark_equals_event_time(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(10.0)
        assert gen.get_watermark() == pytest.approx(10.0)


class TestWatermarkGeneratorAdvance:
    def test_advance_watermark_forward(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        result = gen.advance_watermark(20.0)
        assert result == pytest.approx(20.0)
        assert gen.get_watermark() == pytest.approx(20.0)
        assert gen.max_event_time == pytest.approx(22.0)

    def test_advance_watermark_backward_does_not_retreat(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.advance_watermark(20.0)
        result = gen.advance_watermark(10.0)
        assert result == pytest.approx(20.0)
        assert gen.get_watermark() == pytest.approx(20.0)

    def test_advance_watermark_zero(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        result = gen.advance_watermark(0.0)
        assert result == pytest.approx(0.0)
        assert gen.get_watermark() == pytest.approx(0.0)

    def test_advance_negative_watermark_raises(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        with pytest.raises(ValueError, match="watermark must be non-negative"):
            gen.advance_watermark(-5.0)

    def test_advance_after_observe(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(10.0)
        gen.advance_watermark(15.0)
        assert gen.get_watermark() == pytest.approx(15.0)
        assert gen.max_event_time == pytest.approx(17.0)

    def test_advance_less_than_observe(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(20.0)
        gen.advance_watermark(15.0)
        assert gen.get_watermark() == pytest.approx(18.0)
        assert gen.max_event_time == pytest.approx(20.0)


class TestWatermarkGeneratorIsWindowExpired:
    def test_window_not_expired_when_no_events(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        assert gen.is_window_expired(10.0) is False

    def test_window_not_expired_when_watermark_before_end(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(10.0)
        assert gen.is_window_expired(10.0) is False

    def test_window_expired_when_watermark_at_end(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(10.0)
        assert gen.is_window_expired(10.0) is True

    def test_window_expired_when_watermark_after_end(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(15.0)
        assert gen.is_window_expired(10.0) is True

    def test_window_expired_with_allowed_lateness(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(12.0)
        assert gen.is_window_expired(10.0, allowed_lateness=5.0) is False
        gen.observe_event(16.0)
        assert gen.is_window_expired(10.0, allowed_lateness=5.0) is True

    def test_window_expired_exactly_at_end_plus_lateness(self):
        gen = WatermarkGenerator(delay_seconds=0.0)
        gen.observe_event(15.0)
        assert gen.is_window_expired(10.0, allowed_lateness=5.0) is True

    def test_with_delay_and_lateness(self):
        gen = WatermarkGenerator(delay_seconds=2.0)
        gen.observe_event(20.0)
        assert gen.get_watermark() == pytest.approx(18.0)
        assert gen.is_window_expired(10.0, allowed_lateness=5.0) is True
        assert gen.is_window_expired(15.0, allowed_lateness=5.0) is False
