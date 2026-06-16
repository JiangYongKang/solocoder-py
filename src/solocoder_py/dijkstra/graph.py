from __future__ import annotations

import heapq
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .exceptions import (
    DijkstraError,
    NegativeWeightError,
    NodeNotFoundError,
    UnreachableNodeError,
)
from .models import Edge, ShortestPathResult


class WeightedDigraph:
    def __init__(self) -> None:
        self._adjacency: Dict[str, Dict[str, float]] = {}

    @property
    def node_count(self) -> int:
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adjacency.values())

    def has_node(self, node: str) -> bool:
        return node in self._adjacency

    def has_edge(self, from_node: str, to_node: str) -> bool:
        return from_node in self._adjacency and to_node in self._adjacency[from_node]

    def add_node(self, node: str) -> None:
        if not node:
            raise DijkstraError("Node identifier cannot be empty")
        if node not in self._adjacency:
            self._adjacency[node] = {}

    def add_edge(self, from_node: str, to_node: str, weight: float) -> None:
        if weight < 0:
            raise NegativeWeightError(
                f"Dijkstra algorithm requires non-negative weights, got {weight} "
                f"for edge '{from_node}' -> '{to_node}'"
            )
        self.add_node(from_node)
        self.add_node(to_node)
        self._adjacency[from_node][to_node] = weight

    def get_edge_weight(self, from_node: str, to_node: str) -> float:
        if not self.has_edge(from_node, to_node):
            raise DijkstraError(
                f"Edge not found: '{from_node}' -> '{to_node}'"
            )
        return self._adjacency[from_node][to_node]

    def get_neighbors(self, node: str) -> Iterable[Tuple[str, float]]:
        if node not in self._adjacency:
            raise NodeNotFoundError(f"Node not found: {node}")
        return self._adjacency[node].items()

    def get_nodes(self) -> List[str]:
        return sorted(self._adjacency.keys())

    def get_edges(self) -> List[Edge]:
        edges: List[Edge] = []
        for from_node, neighbors in self._adjacency.items():
            for to_node, weight in neighbors.items():
                edges.append(Edge(from_node=from_node, to_node=to_node, weight=weight))
        return edges

    def remove_node(self, node: str) -> None:
        if node not in self._adjacency:
            raise NodeNotFoundError(f"Node not found: {node}")
        del self._adjacency[node]
        for neighbors in self._adjacency.values():
            neighbors.pop(node, None)

    def remove_edge(self, from_node: str, to_node: str) -> None:
        if not self.has_edge(from_node, to_node):
            raise DijkstraError(
                f"Edge not found: '{from_node}' -> '{to_node}'"
            )
        del self._adjacency[from_node][to_node]


class Dijkstra:
    def __init__(self, graph: Optional[WeightedDigraph] = None) -> None:
        self._graph: WeightedDigraph = graph or WeightedDigraph()

    @property
    def graph(self) -> WeightedDigraph:
        return self._graph

    def add_node(self, node: str) -> None:
        self._graph.add_node(node)

    def add_edge(self, from_node: str, to_node: str, weight: float) -> None:
        self._graph.add_edge(from_node, to_node, weight)

    def shortest_paths(
        self,
        source: str,
        target: Optional[str] = None,
    ) -> ShortestPathResult:
        if not self._graph.has_node(source):
            raise NodeNotFoundError(f"Source node not found: {source}")
        if target is not None and not self._graph.has_node(target):
            raise NodeNotFoundError(f"Target node not found: {target}")

        distances: Dict[str, float] = {
            node: float("inf") for node in self._graph.get_nodes()
        }
        distances[source] = 0.0

        predecessors: Dict[str, Optional[str]] = {
            node: None for node in self._graph.get_nodes()
        }

        visited: List[str] = []
        visited_set: Set[str] = set()

        priority_queue: List[Tuple[float, str]] = [(0.0, source)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_node in visited_set:
                continue

            visited.append(current_node)
            visited_set.add(current_node)

            if target is not None and current_node == target:
                return ShortestPathResult(
                    source=source,
                    distances=distances,
                    predecessors=predecessors,
                    visited=visited,
                    target=target,
                    terminated_early=True,
                )

            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in self._graph.get_neighbors(current_node):
                if neighbor in visited_set:
                    continue
                new_distance = current_distance + weight
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor))

        return ShortestPathResult(
            source=source,
            distances=distances,
            predecessors=predecessors,
            visited=visited,
            target=target,
            terminated_early=False,
        )

    def shortest_path(
        self,
        source: str,
        target: str,
    ) -> Tuple[float, List[str]]:
        result = self.shortest_paths(source, target)
        if not result.is_reachable(target):
            raise UnreachableNodeError(
                f"Node '{target}' is unreachable from source '{source}'"
            )
        return result.get_distance(target), result.get_path(target)
