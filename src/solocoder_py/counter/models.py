from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DimensionSchema:
    levels: list[str]

    @property
    def max_depth(self) -> int:
        return len(self.levels)

    def validate_path(self, path_parts: list[str]) -> None:
        if not path_parts:
            from .exceptions import DimensionPathError
            raise DimensionPathError("dimension path cannot be empty")
        if len(path_parts) > self.max_depth:
            from .exceptions import DimensionPathError
            raise DimensionPathError(
                f"path depth {len(path_parts)} exceeds max depth {self.max_depth}"
            )
        for part in path_parts:
            if not part:
                from .exceptions import DimensionPathError
                raise DimensionPathError("dimension segment cannot be empty")

    def is_full_path(self, path_parts: list[str]) -> bool:
        return len(path_parts) == self.max_depth

    def level_name(self, depth: int) -> Optional[str]:
        if 0 < depth <= self.max_depth:
            return self.levels[depth - 1]
        return None


@dataclass
class CounterNode:
    path: tuple[str, ...]
    count: int = 0
    children: dict[str, "CounterNode"] = field(default_factory=dict)


@dataclass
class CounterState:
    schema: DimensionSchema
    counts: dict[tuple[str, ...], int] = field(default_factory=dict)

    def total(self) -> int:
        top_level_counts = [v for k, v in self.counts.items() if len(k) == 1]
        return sum(top_level_counts)


