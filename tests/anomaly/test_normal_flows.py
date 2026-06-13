from __future__ import annotations

import pytest

from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock


class TestNormalDataNoAnomaly:
    def test_constant_data_not_anomalous(self, detector: AnomalyDetector):
        for _ in range(20):
            point, alert = detector.add_point(5.0)
            assert point.is_anomaly is False
            assert alert is None
        assert detector.get_window_size() == 10
        assert detector.get_mean() == 5.0
        assert detector.get_std() == 0.0

    def test_small_variation_not_anomalous(self, detector: AnomalyDetector):
        for v in [1.0, 2.0, 1.5, 2.5, 1.8, 2.2, 1.9, 2.1, 2.0, 1.7]:
            point, alert = detector.add_point(v)
            assert point.is_anomaly is False
            assert alert is None
        for v in [1.9, 2.0, 2.1, 1.8, 2.2]:
            point, alert = detector.add_point(v)
            assert point.is_anomaly is False
            assert alert is None


class TestOutlierDetection:
    def test_clear_outlier_detected(self, detector: AnomalyDetector):
        for _ in range(10):
            detector.add_point(10.0)
        point, alert = detector.add_point(1000.0)
        assert point.is_anomaly is True
        assert alert is None

    def test_low_outlier_detected(self, detector: AnomalyDetector):
        for _ in range(10):
            detector.add_point(50.0)
        point, alert = detector.add_point(-100.0)
        assert point.is_anomaly is True
        assert alert is None

    def test_outlier_not_added_to_window(self, detector: AnomalyDetector):
        for _ in range(10):
            detector.add_point(10.0)
        detector.add_point(1000.0)
        assert detector.get_window_size() == 10
        assert all(v == 10.0 for v in detector.get_window())
        assert detector.get_mean() == 10.0


class TestConsecutiveAlert:
    def test_consecutive_anomalies_trigger_alert(
        self, detector: AnomalyDetector, manual_clock: ManualClock
    ):
        for _ in range(10):
            detector.add_point(10.0)

        alerts = []
        for i in range(5):
            manual_clock.advance(1.0)
            point, alert = detector.add_point(1000.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1
        assert detector.state.consecutive_anomalies == 5
        assert "consecutive anomalies" in alerts[0].reason

    def test_single_anomaly_no_alert(self, detector: AnomalyDetector):
        for _ in range(10):
            detector.add_point(10.0)
        _, alert = detector.add_point(999.0)
        assert alert is None

    def test_two_anomalies_no_alert(self, detector: AnomalyDetector, manual_clock: ManualClock):
        for _ in range(10):
            detector.add_point(10.0)
        manual_clock.advance(1.0)
        detector.add_point(999.0)
        manual_clock.advance(1.0)
        _, alert = detector.add_point(998.0)
        assert alert is None


class TestCooldown:
    def test_cooldown_suppresses_duplicate_alerts(
        self, detector: AnomalyDetector, manual_clock: ManualClock
    ):
        for _ in range(10):
            detector.add_point(10.0)

        alerts = []
        for i in range(10):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(900.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1

    def test_cooldown_expired_retrigger_alert(
        self, detector: AnomalyDetector, manual_clock: ManualClock
    ):
        for _ in range(10):
            detector.add_point(10.0)

        for i in range(3):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(800.0 + i)
            if alert is not None:
                first_alert = alert

        assert first_alert is not None

        manual_clock.advance(120.0)
        detector.state.consecutive_anomalies = 0

        for i in range(3):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(700.0 + i)
            if alert is not None:
                second_alert = alert
                break

        assert second_alert is not None
        assert second_alert.triggered_at > first_alert.triggered_at


class TestAnomalyDoesNotPolluteBaseline:
    def test_anomaly_not_in_window(self, detector: AnomalyDetector):
        for _ in range(10):
            detector.add_point(10.0)
        mean_before = detector.get_mean()
        detector.add_point(1e6)
        assert detector.get_mean() == mean_before
        assert detector.get_window_size() == 10

    def test_repeated_anomalies_keep_baseline_clean(
        self, detector: AnomalyDetector, manual_clock: ManualClock
    ):
        for _ in range(10):
            detector.add_point(5.0)
        for _ in range(20):
            manual_clock.advance(1.0)
            detector.add_point(500.0)
        assert detector.get_mean() == 5.0
        assert all(v == 5.0 for v in detector.get_window())
