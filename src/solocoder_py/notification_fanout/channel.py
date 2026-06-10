from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from .models import Notification


class NotificationChannel(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def deliver(self, notification: Notification) -> None:
        ...


class InMemoryChannel(NotificationChannel):
    def __init__(self, channel_name: str) -> None:
        self._name = channel_name
        self._delivered: list[Notification] = []
        self._failure_count: int = 0
        self._fail_next_n: int = 0
        self._delay_seconds: float = 0.0
        self._should_timeout: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def delivered_count(self) -> int:
        return len(self._delivered)

    @property
    def delivered(self) -> list[Notification]:
        return list(self._delivered)

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def set_fail_next_n(self, n: int) -> None:
        self._fail_next_n = n

    def set_delay(self, seconds: float) -> None:
        self._delay_seconds = seconds

    def set_should_timeout(self, flag: bool) -> None:
        self._should_timeout = flag

    def reset(self) -> None:
        self._delivered.clear()
        self._failure_count = 0
        self._fail_next_n = 0
        self._delay_seconds = 0.0
        self._should_timeout = False

    def deliver(self, notification: Notification) -> None:
        if self._should_timeout:
            time.sleep(3600)
            return

        if self._delay_seconds > 0:
            time.sleep(self._delay_seconds)

        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            self._failure_count += 1
            raise RuntimeError(
                f"Channel '{self._name}' simulated delivery failure"
            )

        self._delivered.append(notification)
