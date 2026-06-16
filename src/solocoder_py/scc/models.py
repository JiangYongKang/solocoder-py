from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .exceptions import NodeNotFoundError


@dataclass
class SCCResult:
    node_to_component: Dict[int, int] = field(default_factory=dict)
    component_to_nodes: Dict[int, List[int]] = field(default_factory=dict)
    components: List[List[int]] = field(default_factory=list)

    def get_component_id(self, node: int) -> int:
        if node not in self.node_to_component:
            raise NodeNotFoundError(f"Node {node} does not exist in the graph")
        return self.node_to_component[node]

    def get_component_nodes(self, component_id: int) -> List[int]:
        if component_id not in self.component_to_nodes:
            raise NodeNotFoundError(f"Component {component_id} does not exist")
        return list(self.component_to_nodes[component_id])

    def __len__(self) -> int:
        return len(self.components)


@dataclass
class CondensationGraph:
    num_components: int
    adjacency: Dict[int, Set[int]] = field(default_factory=dict)
    node_to_component: Dict[int, int] = field(default_factory=dict)
    component_to_nodes: Dict[int, List[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for cid in range(self.num_components):
            if cid not in self.adjacency:
                self.adjacency[cid] = set()

    def get_outgoing_edges(self, component_id: int) -> Set[int]:
        if component_id not in self.adjacency:
            raise NodeNotFoundError(f"Component {component_id} does not exist")
        return set(self.adjacency[component_id])

    def get_incoming_edges(self, component_id: int) -> Set[int]:
        if component_id < 0 or component_id >= self.num_components:
            raise NodeNotFoundError(f"Component {component_id} does not exist")
        incoming: Set[int] = set()
        for src, targets in self.adjacency.items():
            if component_id in targets:
                incoming.add(src)
        return incoming

    def is_dag(self) -> bool:
        visited: Set[int] = set()
        rec_stack: Set[int] = set()

        def has_cycle(node: int) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.adjacency.get(node, set()):
                if has_cycle(neighbor):
                    return True
            rec_stack.remove(node)
            return False

        for cid in range(self.num_components):
            if cid not in visited:
                if has_cycle(cid):
                    return False
        return True

    def topological_order(self) -> List[int]:
        visited: Set[int] = set()
        order: List[int] = []

        def dfs(node: int) -> None:
            if node in visited:
                return
            visited.add(node)
            for neighbor in sorted(self.adjacency.get(node, set())):
                dfs(neighbor)
            order.append(node)

        for cid in range(self.num_components):
            if cid not in visited:
                dfs(cid)

        return list(reversed(order))

    def has_edge(self, from_component: int, to_component: int) -> bool:
        if from_component not in self.adjacency:
            raise NodeNotFoundError(f"Component {from_component} does not exist")
        return to_component in self.adjacency[from_component]

    def get_edges(self) -> List[Tuple[int, int]]:
        edges: List[Tuple[int, int]] = []
        for src in sorted(self.adjacency.keys()):
            for dst in sorted(self.adjacency[src]):
                edges.append((src, dst))
        return edges
