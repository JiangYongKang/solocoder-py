from __future__ import annotations

from typing import Dict, Generic, List, Optional, Set, Tuple

from .exceptions import EdgeNotFoundError, KruskalError, NodeNotFoundError
from .models import Edge, ForestEdge, MSTResult, T, UnionFind


class UndirectedWeightedGraph(Generic[T]):
    def __init__(self) -> None:
        self._nodes: Set[T] = set()
        self._edges: List[Edge[T]] = []
        self._adjacency: Dict[T, Dict[T, List[Edge[T]]]] = {}

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def has_node(self, node: T) -> bool:
        return node in self._nodes

    def has_edge(self, u: T, v: T) -> bool:
        return u in self._adjacency and v in self._adjacency[u] and len(self._adjacency[u][v]) > 0

    def add_node(self, node: T) -> None:
        if node is None:
            raise KruskalError("Node cannot be None")
        if node not in self._nodes:
            self._nodes.add(node)
            self._adjacency[node] = {}

    def add_edge(self, u: T, v: T, weight: float) -> Edge[T]:
        self.add_node(u)
        self.add_node(v)
        edge = Edge(u=u, v=v, weight=weight)
        self._edges.append(edge)
        if v not in self._adjacency[u]:
            self._adjacency[u][v] = []
        if u not in self._adjacency[v]:
            self._adjacency[v][u] = []
        self._adjacency[u][v].append(edge)
        self._adjacency[v][u].append(edge)
        return edge

    def get_edges_between(self, u: T, v: T) -> List[Edge[T]]:
        if not self.has_node(u):
            raise NodeNotFoundError(f"Node not found: {u}")
        if not self.has_node(v):
            raise NodeNotFoundError(f"Node not found: {v}")
        if v not in self._adjacency[u]:
            return []
        return list(self._adjacency[u][v])

    def get_neighbors(self, node: T) -> List[Tuple[T, float]]:
        if not self.has_node(node):
            raise NodeNotFoundError(f"Node not found: {node}")
        result: List[Tuple[T, float]] = []
        for neighbor, edges in self._adjacency[node].items():
            if edges:
                min_weight = min(e.weight for e in edges)
                result.append((neighbor, min_weight))
        return result

    def get_nodes(self) -> List[T]:
        return sorted(self._nodes, key=lambda x: hash(x))

    def get_edges(self) -> List[Edge[T]]:
        return list(self._edges)

    def remove_node(self, node: T) -> None:
        if not self.has_node(node):
            raise NodeNotFoundError(f"Node not found: {node}")
        self._nodes.remove(node)
        edges_to_remove: List[Edge[T]] = []
        for edge in self._edges:
            if edge.contains(node):
                edges_to_remove.append(edge)
        for edge in edges_to_remove:
            self._edges.remove(edge)
            other = edge.other(node)
            if other in self._adjacency:
                self._adjacency[other].pop(node, None)
        del self._adjacency[node]

    def remove_edge(self, u: T, v: T, weight: Optional[float] = None) -> None:
        if not self.has_edge(u, v):
            raise EdgeNotFoundError(f"Edge not found: {u} - {v}")
        edges_between = self._adjacency[u][v]
        target_idx = -1
        if weight is None:
            target_idx = 0
        else:
            for i, edge in enumerate(edges_between):
                if edge.weight == weight:
                    target_idx = i
                    break
        if target_idx == -1:
            raise EdgeNotFoundError(
                f"Edge not found: {u} - {v} with weight {weight}"
            )
        edge = edges_between.pop(target_idx)
        self._adjacency[v][u].remove(edge)
        self._edges.remove(edge)
        if not edges_between:
            del self._adjacency[u][v]
            if not self._adjacency[v][u]:
                del self._adjacency[v][u]


class Kruskal(Generic[T]):
    def __init__(self, graph: Optional[UndirectedWeightedGraph[T]] = None) -> None:
        self._graph: UndirectedWeightedGraph[T] = graph or UndirectedWeightedGraph()

    @property
    def graph(self) -> UndirectedWeightedGraph[T]:
        return self._graph

    def add_node(self, node: T) -> None:
        self._graph.add_node(node)

    def add_edge(self, u: T, v: T, weight: float) -> Edge[T]:
        return self._graph.add_edge(u, v, weight)

    def compute_mst(self) -> MSTResult[T]:
        nodes = self._graph.get_nodes()
        if not nodes:
            return MSTResult()

        uf = UnionFind(nodes)
        edges = sorted(self._graph.get_edges(), key=lambda e: e.weight)

        forest_edges: List[ForestEdge[T]] = []
        v = len(nodes)

        for edge in edges:
            if uf.union(edge.u, edge.v):
                forest_edges.append(ForestEdge(edge=edge, component_id=0))
                if len(forest_edges) == v - 1:
                    break

        final_components = uf.get_components()
        sorted_components = sorted(
            final_components, key=lambda comp: hash(min(comp, key=lambda x: hash(x)))
        )

        component_root_to_id: Dict[T, int] = {}
        for idx, comp in enumerate(sorted_components):
            rep = min(comp, key=lambda x: hash(x))
            component_root_to_id[uf.find(rep)] = idx

        normalized_forest: List[ForestEdge[T]] = []
        for fe in forest_edges:
            root = uf.find(fe.edge.u)
            cid = component_root_to_id[root]
            normalized_forest.append(ForestEdge(edge=fe.edge, component_id=cid))

        return MSTResult(
            forest_edges=normalized_forest,
            components=sorted_components,
        )
