from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from .exceptions import InvalidDeadlineError


@dataclass
class TimeoutContextInfo:
    context_id: str
    deadline: float
    created_at: float
    is_cancelled: bool
    is_expired: bool
    cancel_reason: Optional[str] = None
    parent_id: Optional[str] = None
