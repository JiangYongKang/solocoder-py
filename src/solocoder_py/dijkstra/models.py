from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Edge:
    from_node: str
    to_node: str
    weight: float


@dataclass
class ShortestPathResult:
    source: str
    distances: Dict[str, float] = field(default_factory=dict)
    predecessors: Dict[str, Optional[str]] = field(default_factory=dict)
    visited: List[str] = field(default_factory=list)
    target: Optional[str] = None
    terminated_early: bool = False

    def get_distance(self, node: str) -> float:
        if node not in self.distances:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(f"Node not found in result: {node}")
        return self.distances[node]

    def get_path(self, target: str) -> List[str]:
        if target not in self.predecessors:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(f"Node not found in result: {target}")
        if self.distances.get(target) == float("inf"):
            from .exceptions import UnreachableNodeError
            raise UnreachableNodeError(
                f"Node '{target}' is unreachable from source '{self.source}'"
            )
        path: List[str] = []
        current: Optional[str] = target
        while current is not None:
            path.append(current)
            current = self.predecessors.get(current)
        path.reverse()
        return path

    def is_reachable(self, node: str) -> bool:
        if node not in self.distances:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(f"Node not found in result: {node}")
        return self.distances[node] != float("inf")
