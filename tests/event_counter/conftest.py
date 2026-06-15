import threading
from datetime import datetime, timedelta, timezone

import pytest

from solocoder_py.event_counter import EventCounter, Event, Granularity
from solocoder_py.event_counter.models import GranularityConfig


@pytest.fixture
def base_time():
    return datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def short_retention_configs():
    return {
        Granularity.MINUTE: GranularityConfig(retention=timedelta(hours=2)),
        Granularity.HOUR: GranularityConfig(retention=timedelta(days=7)),
        Granularity.DAY: GranularityConfig(retention=timedelta(days=90)),
    }


@pytest.fixture
def expiry_test_configs():
    return {
        Granularity.MINUTE: GranularityConfig(retention=timedelta(minutes=30)),
        Granularity.HOUR: GranularityConfig(retention=timedelta(hours=6)),
        Granularity.DAY: GranularityConfig(retention=timedelta(days=30)),
    }


@pytest.fixture
def make_counter(short_retention_configs):
    def _make_counter(clock=None):
        return EventCounter(
            granularity_configs=short_retention_configs,
            clock=clock,
        )
    return _make_counter


@pytest.fixture
def counter(make_counter, base_time):
    return make_counter(clock=lambda: base_time)


@pytest.fixture
def thread_safe_counter(make_counter, base_time):
    return make_counter(clock=lambda: base_time)
