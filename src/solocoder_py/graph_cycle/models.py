from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class NodeColor(str, Enum):
    WHITE = "WHITE"
    GRAY = "GRAY"
    BLACK = "BLACK"


@dataclass
class Cycle:
    nodes: List[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.nodes = list(self.nodes)

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self):
        return iter(self.nodes)

    def __getitem__(self, index):
        return self.nodes[index]

    def canonical_key(self) -> Tuple[Any, ...]:
        if not self.nodes:
            return tuple()
        nodes = self.nodes
        min_idx = 0
        for i in range(1, len(nodes)):
            if nodes[i] < nodes[min_idx]:
                min_idx = i
        rotated = nodes[min_idx:] + nodes[:min_idx]
        return tuple(rotated)

    def is_self_loop(self) -> bool:
        return len(self.nodes) == 1

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cycle):
            return NotImplemented
        return self.canonical_key() == other.canonical_key()

    def __hash__(self) -> int:
        return hash(self.canonical_key())

    def __repr__(self) -> str:
        return f"Cycle(nodes={self.nodes!r})"


@dataclass
class DirectedGraph:
    _adjacency: Dict[Any, List[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized: Dict[Any, List[Any]] = {}
        for node, neighbors in self._adjacency.items():
            if node not in normalized:
                normalized[node] = []
            seen = set()
            for neighbor in neighbors:
                if neighbor not in normalized:
                    normalized[neighbor] = []
                if neighbor not in seen:
                    seen.add(neighbor)
                    normalized[node].append(neighbor)
        self._adjacency = normalized

    @property
    def node_count(self) -> int:
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adjacency.values())

    def has_node(self, node: Any) -> bool:
        return node in self._adjacency

    def get_nodes(self) -> List[Any]:
        return list(self._adjacency.keys())

    def get_neighbors(self, node: Any) -> List[Any]:
        if node not in self._adjacency:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(f"Node not found: {node}")
        return list(self._adjacency[node])

    def add_node(self, node: Any) -> None:
        if node not in self._adjacency:
            self._adjacency[node] = []

    def add_edge(self, from_node: Any, to_node: Any) -> None:
        if from_node not in self._adjacency:
            self._adjacency[from_node] = []
        if to_node not in self._adjacency:
            self._adjacency[to_node] = []
        if to_node not in self._adjacency[from_node]:
            self._adjacency[from_node].append(to_node)

    def get_adjacency(self) -> Dict[Any, List[Any]]:
        return {node: list(neighbors) for node, neighbors in self._adjacency.items()}
