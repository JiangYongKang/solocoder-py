from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class MaskingStrategy(str, Enum):
    MASKING = "masking"
    TOKENIZATION = "tokenization"
    GENERALIZATION = "generalization"


@dataclass
class MaskingConfig:
    keep_prefix: int = 3
    keep_suffix: int = 4
    mask_char: str = "*"

    def __post_init__(self) -> None:
        if self.keep_prefix < 0:
            raise ValueError("keep_prefix must be non-negative")
        if self.keep_suffix < 0:
            raise ValueError("keep_suffix must be non-negative")
        if len(self.mask_char) != 1:
            raise ValueError("mask_char must be exactly one character")


@dataclass
class TokenizationConfig:
    token_prefix: str = "TKN_"
    token_length: int = 16
    use_hash: bool = True

    def __post_init__(self) -> None:
        if self.token_length < 8:
            raise ValueError("token_length must be at least 8")


@dataclass
class GeneralizationLevel:
    level: int
    description: str
    generalize_func: Callable[[Any], Any]


@dataclass
class GeneralizationConfig:
    levels: list[GeneralizationLevel] = field(default_factory=list)
    default_level: int = 0

    def __post_init__(self) -> None:
        if self.default_level < 0:
            raise ValueError("default_level must be non-negative")
        if self.levels and self.default_level >= len(self.levels):
            raise ValueError(
                f"default_level {self.default_level} out of range for {len(self.levels)} levels"
            )

    def get_max_level(self) -> int:
        return len(self.levels) - 1 if self.levels else 0


@dataclass
class FieldRule:
    field_name: str
    strategy: MaskingStrategy
    config: Optional[dict[str, Any]] = None
    quasi_identifier: bool = False


@dataclass
class DataRecord:
    id: str
    data: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "data": dict(self.data)}


@dataclass
class KAnonymityReport:
    k: int
    total_records: int
    quasi_identifiers: list[str]
    equivalence_classes: dict[tuple, list[DataRecord]] = field(default_factory=dict)
    violating_classes: list[tuple] = field(default_factory=list)
    is_anonymous: bool = False

    @property
    def violating_count(self) -> int:
        return len(self.violating_classes)

    @property
    def total_classes(self) -> int:
        return len(self.equivalence_classes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "total_records": self.total_records,
            "quasi_identifiers": self.quasi_identifiers,
            "total_equivalence_classes": self.total_classes,
            "violating_classes_count": self.violating_count,
            "is_anonymous": self.is_anonymous,
            "violating_classes": [
                {
                    "quasi_values": list(cls),
                    "size": len(self.equivalence_classes[cls]),
                }
                for cls in self.violating_classes
            ],
        }


__all__ = [
    "MaskingStrategy",
    "MaskingConfig",
    "TokenizationConfig",
    "GeneralizationLevel",
    "GeneralizationConfig",
    "FieldRule",
    "DataRecord",
    "KAnonymityReport",
]
