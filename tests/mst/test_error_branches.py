from __future__ import annotations

import pytest

from solocoder_py.mst import (
    Edge,
    EdgeNotFoundError,
    Kruskal,
    KruskalError,
    NodeNotFoundError,
    UndirectedWeightedGraph,
    UnionFind,
)

from .conftest import empty_graph, kruskal


def test_empty_graph_returns_empty_mst(empty_graph):
    kruskal_alg = Kruskal(empty_graph)
    result = kruskal_alg.compute_mst()

    assert result.edge_count == 0
    assert result.component_count == 0
    assert result.total_weight == pytest.approx(0.0)
    assert len(result.forest_edges) == 0
    assert len(result.components) == 0


def test_kruskal_empty_instance():
    k = Kruskal[str]()
    result = k.compute_mst()
    assert result.edge_count == 0
    assert result.component_count == 0
    assert result.total_weight == pytest.approx(0.0)


def test_node_not_found_get_neighbors(empty_graph):
    with pytest.raises(NodeNotFoundError):
        empty_graph.get_neighbors("X")


def test_node_not_found_remove_node(empty_graph):
    with pytest.raises(NodeNotFoundError):
        empty_graph.remove_node("X")


def test_edge_not_found_remove_edge(empty_graph):
    empty_graph.add_node("A")
    empty_graph.add_node("B")
    with pytest.raises(EdgeNotFoundError):
        empty_graph.remove_edge("A", "B")


def test_edge_not_found_remove_edge_wrong_weight():
    graph = UndirectedWeightedGraph[str]()
    graph.add_edge("A", "B", 5.0)
    with pytest.raises(EdgeNotFoundError):
        graph.remove_edge("A", "B", 99.0)


def test_add_node_none_raises_error(empty_graph):
    with pytest.raises(KruskalError):
        empty_graph.add_node(None)


def test_self_loop_edge_rejected():
    graph = UndirectedWeightedGraph[str]()
    with pytest.raises(KruskalError):
        graph.add_edge("A", "A", 1.0)


def test_edge_self_loop_dataclass_rejected():
    with pytest.raises(KruskalError):
        Edge(u="X", v="X", weight=2.0)


def test_edge_other_invalid_node():
    edge = Edge(u="A", v="B", weight=1.0)
    with pytest.raises(NodeNotFoundError):
        edge.other("C")


def test_union_find_element_not_found():
    uf = UnionFind[str]()
    uf.add("A")
    uf.add("B")
    with pytest.raises(NodeNotFoundError):
        uf.find("C")


def test_union_find_connected_invalid():
    uf = UnionFind[str](["A", "B"])
    with pytest.raises(NodeNotFoundError):
        uf.connected("A", "C")


def test_union_find_union_invalid():
    uf = UnionFind[str](["A", "B"])
    with pytest.raises(NodeNotFoundError):
        uf.union("A", "D")


def test_get_edges_between_node_not_found():
    graph = UndirectedWeightedGraph[str]()
    with pytest.raises(NodeNotFoundError):
        graph.get_edges_between("A", "B")
    graph.add_node("A")
    with pytest.raises(NodeNotFoundError):
        graph.get_edges_between("A", "B")


def test_multiple_same_weight_edges_graph():
    graph = UndirectedWeightedGraph[str]()
    graph.add_edge("A", "B", 2.0)
    graph.add_edge("A", "B", 2.0)
    graph.add_edge("B", "C", 2.0)

    edges_ab = graph.get_edges_between("A", "B")
    assert len(edges_ab) == 2

    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()
    assert result.edge_count == 2
    assert result.is_spanning_tree
    assert result.total_weight == pytest.approx(4.0)


def test_very_large_weights():
    graph = UndirectedWeightedGraph[str]()
    graph.add_edge("A", "B", 1e15)
    graph.add_edge("B", "C", 2e15)
    graph.add_edge("A", "C", 4e15)

    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()
    assert result.total_weight == pytest.approx(3e15)


def test_mixed_positive_negative_zero_weights():
    graph = UndirectedWeightedGraph[str]()
    edges = [
        ("A", "B", 5.0),
        ("A", "C", -3.0),
        ("B", "C", 0.0),
        ("B", "D", -1.0),
        ("C", "D", 2.0),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)

    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.edge_count == 3
    assert result.is_spanning_tree

    sorted_edges = sorted(result.forest_edges, key=lambda e: e.weight)
    weights = [fe.weight for fe in sorted_edges]
    assert -3.0 in weights
    assert -1.0 in weights
    assert 0.0 in weights
    assert result.total_weight == pytest.approx(-4.0)


def test_duplicate_node_add_no_effect():
    graph = UndirectedWeightedGraph[str]()
    graph.add_node("A")
    count_before = graph.node_count
    graph.add_node("A")
    assert graph.node_count == count_before


def test_duplicate_union_in_union_find():
    uf = UnionFind[int]([1, 2, 3])
    assert uf.union(1, 2) is True
    assert uf.union(1, 2) is False
    assert uf.count == 2


def test_add_duplicate_element_to_union_find():
    uf = UnionFind[int]()
    assert uf.add(1) is True
    assert uf.add(1) is False
    assert len(uf) == 1
