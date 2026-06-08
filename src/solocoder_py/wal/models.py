from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LogEntry:
    lsn: int
    data: Any
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.lsn < 0:
            raise ValueError("LSN must be non-negative")
