from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


@dataclass
class ConfigChange:
    key: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None


@dataclass
class ChangeEvent:
    version: str
    timestamp: datetime
    changes: Tuple[ConfigChange, ...]
    is_rollback: bool = False


ConfigListener = Callable[[ChangeEvent], None]


@dataclass
class ConfigVersion:
    version: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    is_rollback: bool = False

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("version cannot be empty")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def has_key(self, key: str) -> bool:
        return key in self.data

    def keys(self) -> Tuple[str, ...]:
        return tuple(sorted(self.data.keys()))
