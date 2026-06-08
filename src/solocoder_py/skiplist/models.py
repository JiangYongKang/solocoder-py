from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SkipListNode:
    score: float
    value: Any
    level: int
    forward: list[Optional["SkipListNode"]]
    span: list[int]


@dataclass
class RangeQueryResult:
    score: float
    value: Any
