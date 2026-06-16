from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .exceptions import NodeNotFoundError
from .models import Cycle, DirectedGraph, NodeColor


class CycleDetector:
    def __init__(self, graph: Optional[DirectedGraph] = None) -> None:
        self._graph: DirectedGraph = graph if graph is not None else DirectedGraph()

    @property
    def graph(self) -> DirectedGraph:
        return self._graph

    def set_graph(self, graph: DirectedGraph) -> None:
        self._graph = graph

    def has_node(self, node: Any) -> bool:
        return self._graph.has_node(node)

    def add_node(self, node: Any) -> None:
        self._graph.add_node(node)

    def add_edge(self, from_node: Any, to_node: Any) -> None:
        self._graph.add_edge(from_node, to_node)

    def _run_dfs(self, start_nodes: List[Any]) -> List[Cycle]:
        adjacency = self._graph.get_adjacency()
        color: Dict[Any, NodeColor] = {node: NodeColor.WHITE for node in adjacency}
        recursion_stack: List[Any] = []
        found_cycles: Set[Cycle] = set()

        def dfs(node: Any) -> None:
            color[node] = NodeColor.GRAY
            recursion_stack.append(node)

            for neighbor in adjacency.get(node, []):
                if color[neighbor] == NodeColor.GRAY:
                    idx = recursion_stack.index(neighbor)
                    cycle_nodes = recursion_stack[idx:]
                    found_cycles.add(Cycle(nodes=cycle_nodes))
                elif color[neighbor] == NodeColor.WHITE:
                    dfs(neighbor)

            recursion_stack.pop()
            color[node] = NodeColor.BLACK

        for node in start_nodes:
            if color[node] == NodeColor.WHITE:
                dfs(node)

        return sorted(found_cycles, key=lambda c: (len(c), c.canonical_key()))

    def detect_cycles(self) -> List[Cycle]:
        if self._graph.node_count == 0:
            return []
        return self._run_dfs(self._graph.get_nodes())

    def detect_cycles_from_node(self, start_node: Any) -> List[Cycle]:
        if not self._graph.has_node(start_node):
            raise NodeNotFoundError(f"Node not found: {start_node}")
        return self._run_dfs([start_node])

    def has_cycle(self) -> bool:
        return len(self.detect_cycles()) > 0

    def get_cycle_nodes(self) -> Set[Any]:
        nodes: Set[Any] = set()
        for cycle in self.detect_cycles():
            nodes.update(cycle.nodes)
        return nodes
