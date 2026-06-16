from __future__ import annotations

import pytest

from solocoder_py.mst import Edge, Kruskal, UnionFind

from .conftest import (
    build_disconnected_graph,
    build_equal_weight_graph,
    build_isolated_node_graph,
    build_multi_edge_graph,
    build_negative_weight_graph,
    build_two_node_graph,
)


def test_two_node_graph_mst():
    graph = build_two_node_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.edge_count == 1
    assert result.is_spanning_tree
    assert result.component_count == 1
    assert result.total_weight == pytest.approx(3.5)

    assert len(result.forest_edges) == 1
    fe = result.forest_edges[0]
    assert fe.component_id == 0
    assert {fe.u, fe.v} == {"A", "B"}


def test_all_edges_equal_weight_spanning_tree():
    graph = build_equal_weight_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    assert result.edge_count == v - 1
    assert result.is_spanning_tree
    assert result.component_count == 1

    expected_weight = (v - 1) * 1.0
    assert result.total_weight == pytest.approx(expected_weight)

    uf = UnionFind(graph.get_nodes())
    for fe in result.forest_edges:
        assert not uf.connected(fe.u, fe.v)
        uf.union(fe.u, fe.v)
    assert uf.count == 1


def test_disconnected_forest_edge_count_equals_v_minus_c():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    c = result.component_count
    assert result.edge_count == v - c


def test_isolated_node_forest():
    graph = build_isolated_node_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.component_count == 3
    v = graph.node_count
    c = result.component_count
    assert result.edge_count == v - c

    comp_sizes = [len(comp) for comp in result.components]
    assert sorted(comp_sizes) == sorted([1, 1, 3])

    connected_comp = None
    for comp in result.components:
        if len(comp) == 3:
            connected_comp = comp
            break
    assert connected_comp == {"A", "B", "C"}

    comp_edges_count = {}
    for fe in result.forest_edges:
        cid = fe.component_id
        comp_edges_count[cid] = comp_edges_count.get(cid, 0) + 1

    for cid in range(result.component_count):
        comp = result.get_component(cid)
        expected_edges = len(comp) - 1
        actual_edges = comp_edges_count.get(cid, 0)
        assert actual_edges == expected_edges


def test_negative_weight_edges_correct():
    graph = build_negative_weight_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    assert result.edge_count == v - 1
    assert result.is_spanning_tree
    assert result.component_count == 1

    expected_weight = -2.0 + -1.0 + 1.0
    assert result.total_weight == pytest.approx(expected_weight)


def test_multi_edge_graph_chooses_min():
    graph = build_multi_edge_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    assert result.edge_count == v - 1
    assert result.is_spanning_tree

    expected_weight = 2.0 + 3.0
    assert result.total_weight == pytest.approx(expected_weight)

    mst_edges = [fe.edge for fe in result.forest_edges]

    assert Edge(u="A", v="B", weight=3.0) in mst_edges
    assert Edge(u="B", v="C", weight=2.0) in mst_edges


def test_single_node_graph():
    kruskal = Kruskal[str]()
    kruskal.add_node("A")
    result = kruskal.compute_mst()

    assert result.edge_count == 0
    assert result.component_count == 1
    assert result.is_spanning_tree
    assert result.total_weight == pytest.approx(0.0)
    assert len(result.components) == 1
    assert result.components[0] == {"A"}


def test_union_find_path_compression():
    uf = UnionFind[str](["a", "b", "c", "d", "e"])
    uf.union("a", "b")
    uf.union("c", "d")
    uf.union("b", "c")

    root1 = uf.find("e")
    root2 = uf.find("d")
    assert uf.find("a") == uf.find("d")
    assert uf.find("b") == uf.find("c")
    assert uf.find("a") == uf.find("c")
    assert uf.find("e") != uf.find("a")


def test_union_find_by_rank():
    uf = UnionFind[int]()
    for i in range(10):
        uf.add(i)

    for i in range(1, 10):
        uf.union(0, i)

    assert uf.count == 1
    root = uf.find(0)
    for i in range(10):
        assert uf.find(i) == root


def test_edge_endpoints_symmetric():
    edge1 = Edge(u="A", v="B", weight=5.0)
    edge2 = Edge(u="B", v="A", weight=5.0)

    assert edge1 == edge2
    assert hash(edge1) == hash(edge2)
    assert edge1.endpoints == ("A", "B") or edge1.endpoints == ("B", "A")


def test_edge_other_works_both_ways():
    edge = Edge(u="X", v="Y", weight=2.5)
    assert edge.other("X") == "Y"
    assert edge.other("Y") == "X"
    assert edge.contains("X")
    assert edge.contains("Y")
    assert not edge.contains("Z")


def test_get_edges_by_component_and_get_component():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    for cid in range(result.component_count):
        comp = result.get_component(cid)
        edges = result.get_edges_by_component(cid)
        if len(comp) > 1:
            assert len(edges) == len(comp) - 1
            uf = UnionFind(list(comp))
            for edge in edges:
                uf.union(edge.u, edge.v)
            assert uf.count == 1
        else:
            assert len(edges) == 0

    with pytest.raises(IndexError):
        result.get_component(result.component_count)

    with pytest.raises(IndexError):
        result.get_edges_by_component(result.component_count)


def test_mst_result_properties():
    graph = build_two_node_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.total_weight == pytest.approx(3.5)
    assert result.edge_count == 1
    assert result.component_count == 1
    assert result.is_spanning_tree is True

    graph2 = build_disconnected_graph()
    kruskal2 = Kruskal(graph2)
    result2 = kruskal2.compute_mst()

    assert result2.is_spanning_tree is False
    assert result2.component_count == 4
