from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Edge:
    from_node: str
    to_node: str


@dataclass
class TopologicalSortResult:
    order: List[str] = field(default_factory=list)
    has_cycle: bool = False
    cycle_nodes: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.has_cycle
