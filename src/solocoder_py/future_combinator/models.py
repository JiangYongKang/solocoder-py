from __future__ import annotations

from enum import Enum


class FutureState(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
