from __future__ import annotations

from typing import List, Tuple

import pytest

from solocoder_py.mst import Kruskal, UndirectedWeightedGraph


@pytest.fixture
def empty_graph() -> UndirectedWeightedGraph[str]:
    return UndirectedWeightedGraph()


@pytest.fixture
def kruskal() -> Kruskal[str]:
    return Kruskal()


def build_simple_connected_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 4.0),
        ("A", "C", 2.0),
        ("B", "C", 1.0),
        ("B", "D", 5.0),
        ("C", "D", 8.0),
        ("C", "E", 10.0),
        ("D", "E", 2.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_classic_mst_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 7),
        ("A", "D", 5),
        ("B", "C", 8),
        ("B", "D", 9),
        ("B", "E", 7),
        ("C", "E", 5),
        ("D", "E", 15),
        ("D", "F", 6),
        ("E", "F", 8),
        ("E", "G", 9),
        ("F", "G", 11),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_two_node_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    graph.add_edge("A", "B", 3.5)
    return graph


def build_equal_weight_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 1.0),
        ("A", "C", 1.0),
        ("B", "C", 1.0),
        ("B", "D", 1.0),
        ("C", "D", 1.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_disconnected_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 1.0),
        ("B", "C", 2.0),
        ("D", "E", 3.0),
        ("E", "F", 4.0),
        ("D", "F", 5.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    graph.add_node("G")
    graph.add_node("H")
    return graph


def build_negative_weight_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", -2.0),
        ("A", "C", 1.0),
        ("B", "C", 3.0),
        ("B", "D", -1.0),
        ("C", "D", 2.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_multi_edge_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 5.0),
        ("A", "B", 3.0),
        ("A", "B", 7.0),
        ("B", "C", 2.0),
        ("B", "C", 6.0),
        ("A", "C", 4.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph


def build_isolated_node_graph() -> UndirectedWeightedGraph[str]:
    graph = UndirectedWeightedGraph[str]()
    edges: List[Tuple[str, str, float]] = [
        ("A", "B", 1.0),
        ("B", "C", 2.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    graph.add_node("D")
    graph.add_node("E")
    return graph


def verify_forest_connectivity(
    result, nodes, component_count_expected
):
    from solocoder_py.mst import UnionFind

    uf = UnionFind(nodes)
    for fe in result.forest_edges:
        uf.union(fe.u, fe.v)

    assert uf.count == component_count_expected

    components_by_id = {}
    for fe in result.forest_edges:
        if fe.component_id not in components_by_id:
            components_by_id[fe.component_id] = set()
        components_by_id[fe.component_id].add(fe.u)
        components_by_id[fe.component_id].add(fe.v)

    for cid, comp_nodes in components_by_id.items():
        rep = min(comp_nodes, key=lambda x: hash(x))
        root = uf.find(rep)
        for node in comp_nodes:
            assert uf.find(node) == root

    assert result.component_count == component_count_expected
