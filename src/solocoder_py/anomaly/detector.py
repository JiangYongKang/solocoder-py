from __future__ import annotations

import math
from collections import deque
from typing import Optional

from .exceptions import AnomalyConfigError
from .models import AlertEvent, AnomalyConfig, AnomalyPoint, Clock, DetectorState, SystemClock


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


class AnomalyDetector:
    def __init__(
        self,
        config: Optional[AnomalyConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config: AnomalyConfig = config or AnomalyConfig()
        self._clock: Clock = clock or SystemClock()
        self._state = DetectorState()
        self._window: deque[float] = deque(maxlen=self._config.window_size)
        self._recent_point_flags: deque[bool] = deque(maxlen=self._config.window_size)

    @property
    def config(self) -> AnomalyConfig:
        return self._config

    @property
    def state(self) -> DetectorState:
        return self._state

    def update_config(self, config: AnomalyConfig) -> None:
        if config.window_size < self._config.window_size:
            while len(self._window) > config.window_size:
                self._window.popleft()
            while len(self._recent_point_flags) > config.window_size:
                self._recent_point_flags.popleft()
        self._window = deque(self._window, maxlen=config.window_size)
        self._recent_point_flags = deque(self._recent_point_flags, maxlen=config.window_size)
        self._config = config

    def add_point(self, value: float) -> tuple[AnomalyPoint, Optional[AlertEvent]]:
        timestamp = self._clock.now()
        window_list = list(self._window)
        current_mean = _mean(window_list)
        current_std = _std(window_list)

        is_anomaly = self._is_anomaly(value, current_mean, current_std)
        if window_list:
            deviation = abs(value - current_mean)
        else:
            deviation = 0.0

        point = AnomalyPoint(
            value=value,
            timestamp=timestamp,
            is_anomaly=is_anomaly,
            deviation=deviation,
        )

        self._state.total_points_seen += 1
        self._recent_point_flags.append(is_anomaly)

        if is_anomaly:
            self._state.total_anomalies_seen += 1
            self._state.consecutive_anomalies += 1
            self._append_anomaly_history(point)
        else:
            self._state.consecutive_anomalies = 0
            self._window.append(value)
            self._state.window = list(self._window)

        alert = self._check_alert(point, current_mean, current_std)

        return point, alert

    def _is_anomaly(self, value: float, mean: float, std: float) -> bool:
        window_len = len(self._window)
        if window_len == 0:
            return False

        if self._config.window_size > 1 and window_len == 1:
            return False

        k = self._config.k_sigma

        if std == 0:
            return value != mean

        upper = mean + k * std
        lower = mean - k * std
        return value > upper or value < lower

    def _check_alert(
        self, point: AnomalyPoint, current_mean: float, current_std: float
    ) -> Optional[AlertEvent]:
        if not point.is_anomaly:
            return None

        now = point.timestamp
        if (
            self._state.last_alert_time is not None
            and now - self._state.last_alert_time < self._config.cooldown_seconds
        ):
            return None

        reasons: list[str] = []
        if self._state.consecutive_anomalies >= self._config.consecutive_threshold:
            reasons.append(
                f"consecutive anomalies ({self._state.consecutive_anomalies}) "
                f">= threshold ({self._config.consecutive_threshold})"
            )

        flags_len = len(self._recent_point_flags)
        if flags_len > 0:
            anomaly_count_in_recent = sum(1 for f in self._recent_point_flags if f)
            ratio = anomaly_count_in_recent / flags_len
            if ratio >= self._config.max_anomaly_ratio and self._config.max_anomaly_ratio <= 1.0:
                reasons.append(
                    f"anomaly ratio ({ratio:.3f}) >= threshold ({self._config.max_anomaly_ratio})"
                )

        if not reasons:
            return None

        recent_anomalies = self._get_recent_anomalies_for_alert()
        alert = AlertEvent(
            reason="; ".join(reasons),
            triggered_at=now,
            anomaly_points=recent_anomalies,
            window_mean=current_mean,
            window_std=current_std,
        )
        self._state.last_alert_time = now
        return alert

    def _get_recent_anomalies_for_alert(self) -> list[AnomalyPoint]:
        limit = min(
            self._state.consecutive_anomalies,
            len(self._state.anomaly_history),
        )
        return list(self._state.anomaly_history[-limit:])

    def _append_anomaly_history(self, point: AnomalyPoint) -> None:
        self._state.anomaly_history.append(point)
        if (
            self._config.anomaly_history_limit > 0
            and len(self._state.anomaly_history) > self._config.anomaly_history_limit
        ):
            self._state.anomaly_history = self._state.anomaly_history[
                -self._config.anomaly_history_limit :
            ]

    def get_mean(self) -> float:
        return _mean(list(self._window))

    def get_std(self) -> float:
        return _std(list(self._window))

    def get_window(self) -> list[float]:
        return list(self._window)

    def get_window_size(self) -> int:
        return len(self._window)

    def get_recent_anomalies(self, limit: Optional[int] = None) -> list[AnomalyPoint]:
        if limit is None:
            return list(self._state.anomaly_history)
        return list(self._state.anomaly_history[-limit:])

    def get_anomaly_ratio(self) -> float:
        if self._state.total_points_seen == 0:
            return 0.0
        return self._state.total_anomalies_seen / self._state.total_points_seen

    def get_recent_anomaly_ratio(self) -> float:
        total = len(self._recent_point_flags)
        if total == 0:
            return 0.0
        return sum(1 for f in self._recent_point_flags if f) / total

    def reset(self) -> None:
        self._window.clear()
        self._recent_point_flags.clear()
        self._state = DetectorState()


__all__ = [
    "AnomalyDetector",
    "_mean",
    "_std",
]
