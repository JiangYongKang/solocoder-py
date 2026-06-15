from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"


@dataclass
class FieldSchema:
    type: FieldType
    required: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    items: Optional["FieldSchema"] = None
    properties: Optional[dict[str, "FieldSchema"]] = None

    def __post_init__(self) -> None:
        if self.type == FieldType.LIST and self.items is None:
            raise ValueError("LIST type must have items schema defined")
        if self.type == FieldType.OBJECT and self.properties is None:
            raise ValueError("OBJECT type must have properties defined")


@dataclass
class Schema:
    properties: dict[str, FieldSchema]
    max_depth: int = 10

    def __post_init__(self) -> None:
        if self.max_depth < 1:
            raise ValueError("max_depth must be at least 1")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[Any] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


__all__ = [
    "FieldType",
    "FieldSchema",
    "Schema",
    "ValidationResult",
]
