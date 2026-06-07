from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional


class SingleFlightError(Exception):
    pass


class WaitTimeoutError(SingleFlightError):
    pass


class CallCancelledError(SingleFlightError):
    pass


@dataclass
class KeyStats:
    key: str
    executions: int = 0
    shared_hits: int = 0
    failures: int = 0

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key cannot be empty")
        if self.executions < 0:
            raise ValueError("executions cannot be negative")
        if self.shared_hits < 0:
            raise ValueError("shared_hits cannot be negative")
        if self.failures < 0:
            raise ValueError("failures cannot be negative")


@dataclass
class _Call:
    key: str
    result: Any = None
    error: Optional[Exception] = None
    done: bool = False
    waiters: int = 0

    def __post_init__(self) -> None:
        self.event = threading.Event()
