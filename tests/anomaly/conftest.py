from __future__ import annotations

import pytest

from solocoder_py.seat.clock import ManualClock
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector


@pytest.fixture
def base_timestamp() -> float:
    return 1718150400.0


@pytest.fixture
def manual_clock(base_timestamp: float) -> ManualClock:
    return ManualClock(start_time=base_timestamp)


@pytest.fixture
def default_config() -> AnomalyConfig:
    return AnomalyConfig(
        window_size=10,
        k_sigma=2.0,
        consecutive_threshold=3,
        cooldown_seconds=60.0,
        max_anomaly_ratio=0.3,
        anomaly_history_limit=100,
    )


@pytest.fixture
def detector(default_config: AnomalyConfig, manual_clock: ManualClock) -> AnomalyDetector:
    return AnomalyDetector(config=default_config, clock=manual_clock)
