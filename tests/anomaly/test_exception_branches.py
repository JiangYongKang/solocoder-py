from __future__ import annotations

import pytest

from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock


class TestEmptyWindowQuery:
    def test_empty_window_mean_is_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)
        assert detector.get_mean() == 0.0

    def test_empty_window_std_is_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)
        assert detector.get_std() == 0.0

    def test_empty_window_is_empty_list(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)
        assert detector.get_window() == []
        assert detector.get_window_size() == 0

    def test_empty_window_anomaly_ratio_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)
        assert detector.get_anomaly_ratio() == 0.0
        assert detector.get_recent_anomaly_ratio() == 0.0

    def test_empty_window_recent_anomalies_empty(self, manual_clock: ManualClock):
        config = AnomalyConfig()
        detector = AnomalyDetector(config=config, clock=manual_clock)
        assert detector.get_recent_anomalies() == []
        assert detector.get_recent_anomalies(limit=10) == []

    def test_empty_window_first_point_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)
        point, alert = detector.add_point(42.0)
        assert point.is_anomaly is False
        assert alert is None


class TestStdZeroNewPointJudgment:
    def test_std_zero_same_value_not_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=3.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(100.0)

        assert detector.get_std() == 0.0

        manual_clock.advance(1.0)
        point, _ = detector.add_point(100.0)
        assert point.is_anomaly is False

    def test_std_zero_different_value_is_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=3.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(100.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(101.0)
        assert point.is_anomaly is True

    def test_std_zero_small_difference_anomaly(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=3.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(0.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(1e-9)
        assert point.is_anomaly is True


class TestCooldownExpiredReAlert:
    def test_cooldown_just_ended_retrigger(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=2,
            cooldown_seconds=30.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(10.0)

        alerts = []
        for i in range(2):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(500.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1
        first_alert_time = alerts[0].triggered_at

        detector.state.consecutive_anomalies = 0

        manual_clock.advance(30.0)
        for i in range(2):
            manual_clock.advance(1.0)
            _, alert = detector.add_point(600.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 2
        assert alerts[1].triggered_at >= first_alert_time + 30.0

    def test_cooldown_not_ended_no_retrigger(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=2,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(10.0)

        alerts = []
        for i in range(5):
            manual_clock.advance(5.0)
            _, alert = detector.add_point(500.0 + i)
            if alert is not None:
                alerts.append(alert)

        assert len(alerts) == 1


class TestResetFunction:
    def test_reset_clears_window(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(5.0)

        assert detector.get_window_size() == 10
        detector.reset()
        assert detector.get_window_size() == 0
        assert detector.get_window() == []

    def test_reset_clears_anomaly_history(self, manual_clock: ManualClock):
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
        detector.add_point(999.0)
        assert len(detector.get_recent_anomalies()) > 0

        detector.reset()
        assert detector.get_recent_anomalies() == []

    def test_reset_clears_consecutive_anomalies(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(5.0)

        for _ in range(3):
            manual_clock.advance(1.0)
            detector.add_point(999.0)

        assert detector.state.consecutive_anomalies >= 3
        detector.reset()
        assert detector.state.consecutive_anomalies == 0

    def test_reset_clears_last_alert_time(self, manual_clock: ManualClock):
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
        detector.add_point(999.0)
        assert detector.state.last_alert_time is not None

        detector.reset()
        assert detector.state.last_alert_time is None

    def test_reset_clears_totals(self, manual_clock: ManualClock):
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
        detector.add_point(999.0)

        assert detector.state.total_points_seen > 0
        assert detector.state.total_anomalies_seen > 0

        detector.reset()
        assert detector.state.total_points_seen == 0
        assert detector.state.total_anomalies_seen == 0

    def test_reset_then_add_points_works(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=5,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(5):
            detector.add_point(100.0)

        detector.reset()

        for _ in range(5):
            detector.add_point(200.0)

        assert detector.get_mean() == 200.0
        assert detector.get_window_size() == 5


class TestNegativeAndZeroValues:
    def test_negative_values_normal_range(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for v in [-10.0, -9.5, -10.5, -10.2, -9.8]:
            point, alert = detector.add_point(v)
            assert point.is_anomaly is False
            assert alert is None

    def test_negative_value_outlier_detected(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(-50.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(-5000.0)
        assert point.is_anomaly is True

    def test_zero_values_in_stream(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=3,
            cooldown_seconds=60.0,
            max_anomaly_ratio=0.3,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            point, alert = detector.add_point(0.0)
            assert point.is_anomaly is False
            assert alert is None

        assert detector.get_mean() == 0.0
        assert detector.get_std() == 0.0

    def test_zero_deviation_from_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(0.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(0.0)
        assert point.is_anomaly is False

    def test_mixed_negative_positive_zero(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        values = [-2.0, -1.0, 0.0, 1.0, 2.0, -1.5, 1.5, -0.5, 0.5, 0.0]
        for v in values:
            point, _ = detector.add_point(v)
            assert point.is_anomaly is False

        manual_clock.advance(1.0)
        point, _ = detector.add_point(1000.0)
        assert point.is_anomaly is True

    def test_negative_outlier_above_band(self, manual_clock: ManualClock):
        config = AnomalyConfig(
            window_size=10,
            k_sigma=2.0,
            consecutive_threshold=1,
            cooldown_seconds=60.0,
            max_anomaly_ratio=1.0,
        )
        detector = AnomalyDetector(config=config, clock=manual_clock)

        for _ in range(10):
            detector.add_point(-100.0)

        manual_clock.advance(1.0)
        point, _ = detector.add_point(100.0)
        assert point.is_anomaly is True


class TestConfigValidation:
    def test_window_size_zero_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(window_size=0)

    def test_window_size_negative_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(window_size=-1)

    def test_k_sigma_negative_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(k_sigma=-1.0)

    def test_consecutive_threshold_zero_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(consecutive_threshold=0)

    def test_cooldown_negative_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(cooldown_seconds=-1.0)

    def test_max_anomaly_ratio_above_one_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(max_anomaly_ratio=1.1)

    def test_max_anomaly_ratio_negative_raises(self):
        with pytest.raises(Exception):
            AnomalyConfig(max_anomaly_ratio=-0.1)
