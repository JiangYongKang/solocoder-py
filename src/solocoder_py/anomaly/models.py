from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..seat.clock import Clock, SystemClock
from .exceptions import AnomalyConfigError


@dataclass(frozen=True)
class AnomalyPoint:
    value: float
    timestamp: float
    is_anomaly: bool
    deviation: float = 0.0


@dataclass(frozen=True)
class AlertEvent:
    reason: str
    triggered_at: float
    anomaly_points: list[AnomalyPoint]
    window_mean: float
    window_std: float


@dataclass
class AnomalyConfig:
    window_size: int = 100
    k_sigma: float = 2.0
    consecutive_threshold: int = 3
    cooldown_seconds: float = 60.0
    max_anomaly_ratio: float = 0.3
    anomaly_history_limit: int = 1000

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise AnomalyConfigError("window_size must be >= 1")
        if self.k_sigma < 0:
            raise AnomalyConfigError("k_sigma must be >= 0")
        if self.consecutive_threshold < 1:
            raise AnomalyConfigError("consecutive_threshold must be >= 1")
        if self.cooldown_seconds < 0:
            raise AnomalyConfigError("cooldown_seconds must be >= 0")
        if not 0 <= self.max_anomaly_ratio <= 1:
            raise AnomalyConfigError("max_anomaly_ratio must be in [0, 1]")
        if self.anomaly_history_limit < 0:
            raise AnomalyConfigError("anomaly_history_limit must be >= 0")


@dataclass
class DetectorState:
    window: list[float] = field(default_factory=list)
    anomaly_history: list[AnomalyPoint] = field(default_factory=list)
    consecutive_anomalies: int = 0
    last_alert_time: Optional[float] = None
    total_points_seen: int = 0
    total_anomalies_seen: int = 0


__all__ = [
    "AnomalyPoint",
    "AlertEvent",
    "AnomalyConfig",
    "DetectorState",
    "Clock",
    "SystemClock",
]
