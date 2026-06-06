from datetime import datetime, timedelta
from typing import Callable, List

import pytest

from solocoder_py.scheduler import FairResourcePoolScheduler, Priority, Task


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2025, 1, 1, 0, 0, 0)

    def __call__(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def set(self, when: datetime) -> None:
        self._now = when


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_scheduler(
    fake_clock: FakeClock,
) -> Callable[..., FairResourcePoolScheduler]:
    def _make(
        total_slots: int = 10,
        aging_interval: timedelta = timedelta(seconds=30),
        aging_promotion_step: int = 1,
        aging_threshold: Priority = Priority.LOW,
        max_wait_time: timedelta = timedelta(minutes=2),
    ) -> FairResourcePoolScheduler:
        return FairResourcePoolScheduler(
            total_slots=total_slots,
            aging_interval=aging_interval,
            aging_promotion_step=aging_promotion_step,
            aging_threshold=aging_threshold,
            max_wait_time=max_wait_time,
            clock=fake_clock,
        )

    return _make


@pytest.fixture
def make_task() -> Callable[..., Task]:
    counter = 0

    def _make(
        resource_slots: int = 1,
        priority: Priority = Priority.NORMAL,
        name: str | None = None,
    ) -> Task:
        nonlocal counter
        counter += 1
        return Task(
            id=f"task-{counter}",
            resource_slots=resource_slots,
            priority=priority,
            name=name or f"Task{counter}",
        )

    return _make


@pytest.fixture
def make_batch(make_task: Callable[..., Task]) -> Callable[..., List[Task]]:
    def _make(count: int, **kwargs) -> List[Task]:
        return [make_task(**kwargs) for _ in range(count)]

    return _make
