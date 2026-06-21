from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class FutureState(str, Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    REJECTED = "REJECTED"


@dataclass
class SettledResult:
    status: str
    value: Any = None
    reason: Optional[Exception] = None

    @classmethod
    def fulfilled(cls, value: Any) -> "SettledResult":
        return cls(status="fulfilled", value=value)

    @classmethod
    def rejected(cls, reason: Exception) -> "SettledResult":
        return cls(status="rejected", reason=reason)
