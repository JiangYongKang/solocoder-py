from __future__ import annotations

import pytest

from solocoder_py.rate_cap import (
    ManualClock,
    RateCapConfig,
    SubjectQuotas,
    WindowConfig,
)


@pytest.fixture
def simple_clock():
    return ManualClock(start_time=0.0)


@pytest.fixture
def single_window_config():
    return RateCapConfig(
        windows=[
            WindowConfig(
                name="1min",
                window_seconds=60.0,
                max_operations=100,
            )
        ],
    )


@pytest.fixture
def multi_window_config():
    return RateCapConfig(
        windows=[
            WindowConfig(name="1min", window_seconds=60.0, max_operations=100),
            WindowConfig(name="1hour", window_seconds=3600.0, max_operations=1000),
        ],
    )


@pytest.fixture
def subject_quotas_config():
    return RateCapConfig(
        windows=[
            WindowConfig(name="1min", window_seconds=60.0, max_operations=1000),
            WindowConfig(name="1hour", window_seconds=3600.0, max_operations=10000),
        ],
        subject_quotas={
            "user-001": SubjectQuotas(
                subject_id="user-001",
                per_window_quotas={"1min": 50, "1hour": 500},
            ),
            "user-002": SubjectQuotas(
                subject_id="user-002",
                per_window_quotas={"1min": 30},
            ),
        },
        default_subject_quotas={"1min": 100, "1hour": 1000},
    )


@pytest.fixture
def granular_window_config():
    return RateCapConfig(
        windows=[
            WindowConfig(
                name="1min-granular",
                window_seconds=60.0,
                max_operations=100,
                slide_granularity_seconds=1.0,
            )
        ],
    )
