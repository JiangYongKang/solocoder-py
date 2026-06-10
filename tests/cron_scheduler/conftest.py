from datetime import datetime, timezone
from typing import Callable

import pytest
from zoneinfo import ZoneInfo

from solocoder_py.cron_scheduler import CronParser, CronScheduler


@pytest.fixture
def make_parser() -> Callable[..., CronParser]:
    def _make() -> CronParser:
        return CronParser()
    return _make


@pytest.fixture
def make_scheduler() -> Callable[..., CronScheduler]:
    def _make(expression: str, timezone_name: str = "UTC") -> CronScheduler:
        return CronScheduler(expression=expression, timezone_name=timezone_name)
    return _make


@pytest.fixture
def utc() -> timezone:
    return timezone.utc


@pytest.fixture
def make_utc_datetime() -> Callable[..., datetime]:
    def _make(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
        return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)
    return _make


@pytest.fixture
def make_zoned_datetime() -> Callable[..., datetime]:
    def _make(
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        tz_name: str = "UTC",
    ) -> datetime:
        return datetime(year, month, day, hour, minute, 0, tzinfo=ZoneInfo(tz_name))
    return _make
