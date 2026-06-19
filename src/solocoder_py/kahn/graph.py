from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Set

from .exceptions import (
    CycleDetectedError,
    KahnError,
    NodeNotFoundError,
)
from .models import Edge, TopologicalSortResult


class Digraph:
    def __init__(self) -> None:
        self._adjacency: Dict[str, Set[str]] = {}
        self._in_degree: Dict[str, int] = {}

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
            raise KahnError("Node identifier cannot be empty")
        if node not in self._adjacency:
            self._adjacency[node] = set()
            self._in_degree[node] = 0

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.add_node(from_node)
        self.add_node(to_node)
        if to_node not in self._adjacency[from_node]:
            self._adjacency[from_node].add(to_node)
            self._in_degree[to_node] += 1

    def get_in_degree(self, node: str) -> int:
        if node not in self._in_degree:
            raise NodeNotFoundError(f"Node not found: {node}")
        return self._in_degree[node]

    def get_neighbors(self, node: str) -> Iterable[str]:
        if node not in self._adjacency:
            raise NodeNotFoundError(f"Node not found: {node}")
        return sorted(self._adjacency[node])

    def get_nodes(self) -> List[str]:
        return sorted(self._adjacency.keys())

    def get_edges(self) -> List[Edge]:
        edges: List[Edge] = []
        for from_node in sorted(self._adjacency.keys()):
            for to_node in sorted(self._adjacency[from_node]):
                edges.append(Edge(from_node=from_node, to_node=to_node))
        return edges

    def remove_node(self, node: str) -> None:
        if node not in self._adjacency:
            raise NodeNotFoundError(f"Node not found: {node}")
        for neighbor in self._adjacency[node]:
            self._in_degree[neighbor] -= 1
        del self._adjacency[node]
        del self._in_degree[node]
        for neighbors in self._adjacency.values():
            neighbors.discard(node)

    def remove_edge(self, from_node: str, to_node: str) -> None:
        if not self.has_edge(from_node, to_node):
            raise KahnError(
                f"Edge not found: '{from_node}' -> '{to_node}'"
            )
        self._adjacency[from_node].discard(to_node)
        self._in_degree[to_node] -= 1


class KahnTopologicalSort:
    def __init__(self, graph: Optional[Digraph] = None) -> None:
        self._graph: Digraph = graph or Digraph()

    @property
    def graph(self) -> Digraph:
        return self._graph

    def add_node(self, node: str) -> None:
        self._graph.add_node(node)

    def add_edge(self, from_node: str, to_node: str) -> None:
        self._graph.add_edge(from_node, to_node)

    def sort(self) -> TopologicalSortResult:
        in_degree: Dict[str, int] = {
            node: self._graph.get_in_degree(node)
            for node in self._graph.get_nodes()
        }

        queue: Deque[str] = deque()
        for node in self._graph.get_nodes():
            if in_degree[node] == 0:
                queue.append(node)

        topo_order: List[str] = []
        visited_count = 0

        while queue:
            node = queue.popleft()
            topo_order.append(node)
            visited_count += 1

            for neighbor in self._graph.get_neighbors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        total_nodes = self._graph.node_count
        has_cycle = visited_count < total_nodes

        cycle_nodes: List[str] = []
        if has_cycle:
            visited_set = set(topo_order)
            for node in self._graph.get_nodes():
                if node not in visited_set:
                    cycle_nodes.append(node)

        return TopologicalSortResult(
            order=topo_order,
            has_cycle=has_cycle,
            cycle_nodes=cycle_nodes,
        )

    def detect_cycle(self) -> List[str]:
        result = self.sort()
        return result.cycle_nodes

    def enumerate_all_topological_orders(self) -> List[List[str]]:
        result = self.sort()
        if result.has_cycle:
            raise CycleDetectedError(
                "Cannot enumerate topological orders: graph contains a cycle",
                cycle_nodes=result.cycle_nodes,
            )

        in_degree: Dict[str, int] = {
            node: self._graph.get_in_degree(node)
            for node in self._graph.get_nodes()
        }

        results: List[List[str]] = []
        self._backtrack([], in_degree, set(), results)
        return results

    def _backtrack(
        self,
        current: List[str],
        in_degree: Dict[str, int],
        visited: Set[str],
        results: List[List[str]],
    ) -> None:
        total_nodes = self._graph.node_count
        if len(current) == total_nodes:
            results.append(list(current))
            return

        available: List[str] = []
        for node in self._graph.get_nodes():
            if node not in visited and in_degree[node] == 0:
                available.append(node)

        for node in available:
            current.append(node)
            visited.add(node)

            for neighbor in self._graph.get_neighbors(node):
                in_degree[neighbor] -= 1

            self._backtrack(current, in_degree, visited, results)

            for neighbor in self._graph.get_neighbors(node):
                in_degree[neighbor] += 1

            visited.remove(node)
            current.pop()
