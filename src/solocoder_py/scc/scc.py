from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .exceptions import EmptyGraphError, NodeNotFoundError
from .graph import DirectedGraph
from .models import SCCResult, CondensationGraph


class TarjanSCC:
    def __init__(self, graph: DirectedGraph) -> None:
        self._graph = graph
        self._disc: Dict[int, int] = {}
        self._low: Dict[int, int] = {}
        self._stack: List[int] = []
        self._stack_set: Set[int] = set()
        self._time: int = 0
        self._components: List[List[int]] = []
        self._node_to_component: Dict[int, int] = {}
        self._component_to_nodes: Dict[int, List[int]] = {}
        self._result: SCCResult | None = None

    def find_sccs(self) -> SCCResult:
        if self._graph.is_empty():
            return SCCResult()

        self._disc = {}
        self._low = {}
        self._stack = []
        self._stack_set = set()
        self._time = 0
        self._components = []
        self._node_to_component = {}
        self._component_to_nodes = {}

        for node in self._graph.nodes:
            if node not in self._disc:
                self._dfs(node)

        reversed_components = list(reversed(self._components))
        self._node_to_component = {}
        self._component_to_nodes = {}

        for new_cid, component in enumerate(reversed_components):
            self._component_to_nodes[new_cid] = list(component)
            for node in component:
                self._node_to_component[node] = new_cid

        self._result = SCCResult(
            node_to_component=dict(self._node_to_component),
            component_to_nodes=dict(self._component_to_nodes),
            components=[list(c) for c in reversed_components],
        )
        return self._result

    def _dfs(self, node: int) -> None:
        self._disc[node] = self._time
        self._low[node] = self._time
        self._time += 1
        self._stack.append(node)
        self._stack_set.add(node)

        for neighbor in self._graph.get_neighbors(node):
            if neighbor not in self._disc:
                self._dfs(neighbor)
                self._low[node] = min(self._low[node], self._low[neighbor])
            elif neighbor in self._stack_set:
                self._low[node] = min(self._low[node], self._disc[neighbor])

        if self._low[node] == self._disc[node]:
            component: List[int] = []
            while True:
                w = self._stack.pop()
                self._stack_set.remove(w)
                component.append(w)
                if w == node:
                    break
            self._components.append(component)

    def build_condensation(self, scc_result: SCCResult | None = None) -> CondensationGraph:
        if self._graph.is_empty():
            raise EmptyGraphError("Cannot build condensation graph from empty graph")

        if scc_result is None:
            scc_result = self._result if self._result is not None else self.find_sccs()

        num_components = len(scc_result)
        adjacency: Dict[int, Set[int]] = {}

        for cid in range(num_components):
            adjacency[cid] = set()

        for from_node, to_node in self._graph.edges:
            from_cid = scc_result.get_component_id(from_node)
            to_cid = scc_result.get_component_id(to_node)
            if from_cid != to_cid:
                adjacency[from_cid].add(to_cid)

        return CondensationGraph(
            num_components=num_components,
            adjacency=adjacency,
            node_to_component=dict(scc_result.node_to_component),
            component_to_nodes=dict(scc_result.component_to_nodes),
        )
