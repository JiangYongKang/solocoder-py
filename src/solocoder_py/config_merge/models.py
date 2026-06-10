from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ConfigLayerType(str, Enum):
    DEFAULT = "default"
    ENVIRONMENT = "environment"
    OVERRIDE = "override"


class ArrayMergeStrategy(str, Enum):
    REPLACE = "replace"
    APPEND = "append"


@dataclass
class ConfigLayer:
    layer_type: ConfigLayerType
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.data, dict):
            raise TypeError("data must be a dict")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def has_key(self, key: str) -> bool:
        return key in self.data

    def keys(self):
        return tuple(sorted(self.data.keys()))

    def clear(self) -> None:
        self.data.clear()

    def update(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")
        self.data.update(data)
