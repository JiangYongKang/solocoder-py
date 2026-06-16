from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generic, Hashable, List, Optional, Set, TypeVar

T = TypeVar("T", bound=Hashable)


@dataclass
class Edge(Generic[T]):
    u: T
    v: T
    weight: float

    def __post_init__(self) -> None:
        if self.u == self.v:
            from .exceptions import KruskalError
            raise KruskalError("Self-loop edges are not allowed")

    @property
    def endpoints(self) -> tuple[T, T]:
        return (self.u, self.v)

    def contains(self, node: T) -> bool:
        return self.u == node or self.v == node

    def other(self, node: T) -> T:
        if node == self.u:
            return self.v
        if node == self.v:
            return self.u
        from .exceptions import NodeNotFoundError
        raise NodeNotFoundError(f"Node {node} is not an endpoint of this edge")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        a1, a2 = sorted([self.u, self.v], key=lambda x: hash(x))
        b1, b2 = sorted([other.u, other.v], key=lambda x: hash(x))
        return a1 == b1 and a2 == b2 and self.weight == other.weight

    def __hash__(self) -> int:
        a1, a2 = sorted([self.u, self.v], key=lambda x: hash(x))
        return hash((a1, a2, self.weight))


@dataclass
class ForestEdge(Generic[T]):
    edge: Edge[T]
    component_id: int

    @property
    def u(self) -> T:
        return self.edge.u

    @property
    def v(self) -> T:
        return self.edge.v

    @property
    def weight(self) -> float:
        return self.edge.weight


@dataclass
class MSTResult(Generic[T]):
    forest_edges: List[ForestEdge[T]] = field(default_factory=list)
    components: List[Set[T]] = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        return sum(e.weight for e in self.forest_edges)

    @property
    def edge_count(self) -> int:
        return len(self.forest_edges)

    @property
    def component_count(self) -> int:
        return len(self.components)

    @property
    def is_spanning_tree(self) -> bool:
        return self.component_count == 1

    def get_edges_by_component(self, component_id: int) -> List[Edge[T]]:
        if component_id < 0 or component_id >= self.component_count:
            raise IndexError(f"Component id {component_id} out of range")
        return [fe.edge for fe in self.forest_edges if fe.component_id == component_id]

    def get_component(self, component_id: int) -> Set[T]:
        if component_id < 0 or component_id >= self.component_count:
            raise IndexError(f"Component id {component_id} out of range")
        return self.components[component_id]


class UnionFind(Generic[T]):
    def __init__(self, elements: Optional[List[T]] = None) -> None:
        self._parent: Dict[T, T] = {}
        self._rank: Dict[T, int] = {}
        self._count: int = 0
        if elements:
            for elem in elements:
                self.add(elem)

    def __len__(self) -> int:
        return len(self._parent)

    @property
    def count(self) -> int:
        return self._count

    def add(self, element: T) -> bool:
        if element in self._parent:
            return False
        self._parent[element] = element
        self._rank[element] = 0
        self._count += 1
        return True

    def has(self, element: T) -> bool:
        return element in self._parent

    def find(self, element: T) -> T:
        if element not in self._parent:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(f"Element not in UnionFind: {element}")
        if self._parent[element] != element:
            self._parent[element] = self.find(self._parent[element])
        return self._parent[element]

    def connected(self, a: T, b: T) -> bool:
        return self.find(a) == self.find(b)

    def union(self, a: T, b: T) -> bool:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return False
        rank_a = self._rank[root_a]
        rank_b = self._rank[root_b]
        if rank_a < rank_b:
            self._parent[root_a] = root_b
        elif rank_a > rank_b:
            self._parent[root_b] = root_a
        else:
            self._parent[root_b] = root_a
            self._rank[root_a] += 1
        self._count -= 1
        return True

    def roots(self) -> List[T]:
        roots_set: Set[T] = set()
        for elem in self._parent:
            roots_set.add(self.find(elem))
        return list(roots_set)

    def get_components(self) -> List[Set[T]]:
        groups: Dict[T, Set[T]] = {}
        for elem in self._parent:
            root = self.find(elem)
            if root not in groups:
                groups[root] = set()
            groups[root].add(elem)
        return list(groups.values())
