from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogEntry:
    key: str
    value: Any
    logical_offset: int = 0
    physical_offset: int = 0
    timestamp: float = 0.0
    tombstone: bool = False

    def size(self) -> int:
        key_bytes = len(self.key.encode("utf-8"))
        value_bytes = len(str(self.value).encode("utf-8"))
        return key_bytes + value_bytes + 8 + 8 + 8 + 1
