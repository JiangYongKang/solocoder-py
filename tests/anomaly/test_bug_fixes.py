from __future__ import annotations

import pytest

from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock


class TestWindowTwoPointsAnomalyDetection:
    def test_two_points_different_values_detects_outlier(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.add_point(20.0)

        assert detector.get_window_size() == 2
        assert detector.get_mean() == pytest.approx(15.0)
        assert detector.get_std() == pytest.approx(7.0711, rel=1e-3)

        manual_clock.advance(1.0)
        point, alert = detector.add_point(1000.0)
        assert point.is_anomaly is True
        assert alert is not None
        assert "consecutive anomalies" in alert.reason

    def test_two_points_detects_low_outlier(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.add_point(20.0)

        manual_clock.advance(1.0)
        point, alert = detector.add_point(-500.0)
        assert point.is_anomaly is True
        assert alert is not None

    def test_two_points_within_band_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.add_point(20.0)

        mean = detector.get_mean()
        std = detector.get_std()

        within_band_value = mean + 0.5 * std
        manual_clock.advance(1.0)
        point, alert = detector.add_point(within_band_value)
        assert point.is_anomaly is False
        assert alert is None
        assert detector.get_window_size() == 3

    def test_two_points_identical_std_zero_detects_different(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(15.0)
        detector.add_point(15.0)

        assert detector.get_std() == 0.0

        manual_clock.advance(1.0)
        point, alert = detector.add_point(16.0)
        assert point.is_anomaly is True
        assert alert is not None

    def test_two_points_identical_std_zero_same_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(15.0)
        detector.add_point(15.0)

        manual_clock.advance(1.0)
        point, alert = detector.add_point(15.0)
        assert point.is_anomaly is False
        assert alert is None
        assert detector.get_window_size() == 3

    def test_two_points_negative_values_detects_outlier(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(-10.0)
        detector.add_point(-20.0)

        assert detector.get_mean() == pytest.approx(-15.0)
        assert detector.get_std() == pytest.approx(7.0711, rel=1e-3)

        manual_clock.advance(1.0)
        point, alert = detector.add_point(-1000.0)
        assert point.is_anomaly is True
        assert alert is not None

    def test_two_points_does_not_pollute_baseline(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.add_point(20.0)

        mean_before = detector.get_mean()
        window_before = detector.get_window()

        manual_clock.advance(1.0)
        detector.add_point(1000.0)

        assert detector.get_mean() == mean_before
        assert detector.get_window() == window_before
        assert detector.get_window_size() == 2


class TestAlertAnomalyListLength:
    def test_alert_contains_only_consecutive_anomalies(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(10.0)

        manual_clock.advance(1.0)
        detector.add_point(999.0)
        manual_clock.advance(1.0)
        detector.add_point(998.0)

        detector.state.consecutive_anomalies = 0

        for _ in range(5):
            manual_clock.advance(1.0)
            detector.add_point(10.0)

        alerts = []
        for i in range(3):
            manual_clock.advance(1.0)
            point, alert = detector.add_point(500.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1
        assert len(alerts[0].anomaly_points) == 3
        for ap in alerts[0].anomaly_points:
            assert ap.value >= 500.0

    def test_alert_list_matches_consecutive_count(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=2,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(5.0)

        for i in range(5):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(100.0 + i)
            if alert is not None:
                assert len(alert.anomaly_points) == detector.state.consecutive_anomalies
                break

    def test_many_flags_small_consecutive_returns_only_consecutive(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=20,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(20):
            detector.add_point(10.0)

        manual_clock.advance(1.0)
        detector.add_point(999.0)
        detector.state.consecutive_anomalies = 0

        for i in range(18):
            manual_clock.advance(1.0)
            detector.add_point(10.0)

        alerts = []
        for i in range(3):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(500.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1
        assert len(alerts[0].anomaly_points) == 3
        assert len(detector.get_recent_anomalies()) == 4
        for ap in alerts[0].anomaly_points:
            assert 500.0 <= ap.value <= 502.0

    def test_consecutive_threshold_1_returns_single_point(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(10.0)

        manual_clock.advance(1.0)
        _, alert = detector.add_point(999.0)

        assert alert is not None
        assert len(alert.anomaly_points) == 1
        assert alert.anomaly_points[0].value == 999.0


class TestEmptyWindowDeviation:
    def test_first_point_deviation_is_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        point, alert = detector.add_point(42.0)
        assert point.deviation == 0.0
        assert point.is_anomaly is False
        assert alert is None

    def test_first_point_negative_deviation_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)

        point, _ = detector.add_point(-100.0)
        assert point.deviation == 0.0

    def test_first_point_zero_deviation_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)

        point, _ = detector.add_point(0.0)
        assert point.deviation == 0.0

    def test_second_point_deviation_from_first(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)

        point1, _ = detector.add_point(10.0)
        assert point1.deviation == 0.0

        point2, _ = detector.add_point(20.0)
        assert point2.deviation == pytest.approx(10.0)

    def test_reset_after_first_point_deviation_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)

        detector.add_point(10.0)
        detector.reset()

        point, _ = detector.add_point(20.0)
        assert point.deviation == 0.0

    def test_window_size_1_first_point_deviation_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(window_size=1)
        detector = AnomalyDetector(config=config, clock=manual_clock)

        point, _ = detector.add_point(100.0)
        assert point.deviation == 0.0
