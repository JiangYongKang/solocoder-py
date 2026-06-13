from __future__ import annotations

import pytest

from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock


class TestWindowNotFull:
    def test_partial_window_uses_available_data(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.add_point(12.0)

        assert detector.get_window_size() == 2
        assert detector.get_mean() == pytest.approx(11.0)

    def test_single_point_window_std_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)
        detector.add_point(5.0)

        assert detector.get_std() == 0.0

    def test_partial_window_detects_outlier(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=1.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for v in [10.0, 11.0, 9.0, 10.5, 9.5]:
            detector.add_point(v)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(1000.0)
        assert point.is_anomaly is True

    def test_partial_window_detects_low_outlier(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=1.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for v in [20.0, 21.0, 19.0, 20.5]:
            detector.add_point(v)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(-500.0)
        assert point.is_anomaly is True


class TestKSigmaZero:
    def test_k_zero_any_deviation_is_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=0.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(10.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(10.0001)
        assert point.is_anomaly is True

    def test_k_zero_exact_match_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=0.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(7.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(7.0)
        assert point.is_anomaly is False

    def test_k_zero_negative_deviation(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=0.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(100.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(99.999)
        assert point.is_anomaly is True


class TestConsecutiveThresholdOne:
    def test_m_1_single_anomaly_triggers_alert(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(5.0)

        manual_clock.advance(1.0)
        _, alert = detector.add_point(500.0)
        assert alert is not None
        assert "consecutive anomalies" in alert.reason

    def test_m_1_each_anomaly_after_cooldown_triggers(
        self, manual_clock: ManualClock
    ):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=10.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(5.0)

        manual_clock.advance(1.0)
        _, alert1 = detector.add_point(500.0)
        assert alert1 is not None

        detector.state.consecutive_anomalies = 0

        manual_clock.advance(1.0)
        _, alert2 = detector.add_point(600.0)
        assert alert2 is None

        manual_clock.advance(100.0)
        detector.state.consecutive_anomalies = 0
        manual_clock.advance(1.0)
        _, alert3 = detector.add_point(700.0)
        assert alert3 is not None


class TestWindowSizeOne:
    def test_n_1_window_holds_one_value(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=1,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        assert detector.get_window_size() == 1
        assert detector.get_window() == [10.0]

        manual_clock.advance(1.0)
        point, _ = detector.add_point(10.0)
        assert point.is_anomaly is False
        assert detector.get_window_size() == 1
        assert detector.get_window() == [10.0]

        manual_clock.advance(1.0)
        point, _ = detector.add_point(20.0)
        assert point.is_anomaly is True
        assert detector.get_window_size() == 1
        assert detector.get_window() == [10.0]

    def test_n_1_detects_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=1,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(100.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(200.0)
        assert point.is_anomaly is True

    def test_n_1_anomaly_not_added(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=1,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(100.0)

        manual_clock.advance(1.0)
        detector.add_point(9999.0)
        assert detector.get_window() == [100.0]


class TestConstantDataStream:
    def test_all_constant_std_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=20,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(30):
            point, alert = detector.add_point(42.0)
            assert point.is_anomaly is False
            assert alert is None

        assert detector.get_std() == 0.0
        assert detector.get_mean() == 42.0

    def test_constant_stream_detects_deviation(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(7.0)

        assert detector.get_std() == 0.0

        manual_clock.advance(1.0)
        point, _ = detector.add_point(8.0)
        assert point.is_anomaly is True

    def test_constant_stream_same_value_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(3.14)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(3.14)
        assert point.is_anomaly is False
