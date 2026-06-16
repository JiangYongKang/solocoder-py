from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from .exceptions import NodeNotFoundError


class DirectedGraph:
    def __init__(self) -> None:
        self._adjacency: Dict[int, Set[int]] = {}
        self._nodes: Set[int] = set()

    def add_node(self, node: int) -> None:
        self._nodes.add(node)
        if node not in self._adjacency:
            self._adjacency[node] = set()

    def add_edge(self, from_node: int, to_node: int) -> None:
        self.add_node(from_node)
        self.add_node(to_node)
        self._adjacency[from_node].add(to_node)

    def add_edges(self, edges: Iterable[Tuple[int, int]]) -> None:
        for from_node, to_node in edges:
            self.add_edge(from_node, to_node)

    def get_neighbors(self, node: int) -> Set[int]:
        if node not in self._adjacency:
            raise NodeNotFoundError(f"Node {node} does not exist in the graph")
        return set(self._adjacency[node])

    def has_node(self, node: int) -> bool:
        return node in self._nodes

    def has_edge(self, from_node: int, to_node: int) -> bool:
        if from_node not in self._adjacency:
            return False
        return to_node in self._adjacency[from_node]

    @property
    def nodes(self) -> List[int]:
        return sorted(self._nodes)

    @property
    def edges(self) -> List[Tuple[int, int]]:
        result: List[Tuple[int, int]] = []
        for from_node in sorted(self._adjacency.keys()):
            for to_node in sorted(self._adjacency[from_node]):
                result.append((from_node, to_node))
        return result

    @property
    def num_nodes(self) -> int:
        return len(self._nodes)

    @property
    def num_edges(self) -> int:
        return sum(len(neighbors) for neighbors in self._adjacency.values())

    def is_empty(self) -> bool:
        return len(self._nodes) == 0

    def get_transpose(self) -> "DirectedGraph":
        transposed = DirectedGraph()
        for node in self._nodes:
            transposed.add_node(node)
        for from_node, to_node in self.edges:
            transposed.add_edge(to_node, from_node)
        return transposed

    def __contains__(self, node: int) -> bool:
        return node in self._nodes

    def __iter__(self) -> Iterable[int]:
        return iter(sorted(self._nodes))
