from __future__ import annotations

from typing import Set

import pytest

from solocoder_py.mst import Kruskal, UndirectedWeightedGraph, UnionFind

from .conftest import (
    build_classic_mst_graph,
    build_disconnected_graph,
    build_simple_connected_graph,
    verify_forest_connectivity,
)


def test_connected_graph_mst_edge_count():
    graph = build_simple_connected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    assert result.edge_count == v - 1
    assert result.is_spanning_tree
    assert result.component_count == 1


def test_connected_graph_mst_total_weight_minimized():
    graph = build_simple_connected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    expected_weight = 1.0 + 2.0 + 2.0 + 5.0
    assert result.total_weight == pytest.approx(expected_weight)


def test_classic_mst_correctness():
    graph = build_classic_mst_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.edge_count == 6
    assert result.is_spanning_tree

    expected_weight = 5 + 5 + 6 + 7 + 7 + 9
    assert result.total_weight == pytest.approx(expected_weight)


def test_mst_connectivity_correct():
    graph = build_simple_connected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    nodes = graph.get_nodes()
    uf = UnionFind(nodes)
    for fe in result.forest_edges:
        uf.union(fe.u, fe.v)

    assert uf.count == 1

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            assert uf.connected(nodes[i], nodes[j])


def test_mst_no_cycles():
    graph = build_simple_connected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    nodes = graph.get_nodes()
    uf = UnionFind(nodes)
    for fe in result.forest_edges:
        assert not uf.connected(fe.u, fe.v)
        uf.union(fe.u, fe.v)


def test_disconnected_graph_forest_edge_count():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    v = graph.node_count
    c = result.component_count
    assert result.edge_count == v - c
    assert not result.is_spanning_tree


def test_disconnected_graph_forest_components():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    assert result.component_count == 4

    expected_components = [
        {"A", "B", "C"},
        {"D", "E", "F"},
        {"G"},
        {"H"},
    ]
    result_components_set: Set[frozenset] = {
        frozenset(comp) for comp in result.components
    }
    expected_components_set: Set[frozenset] = {
        frozenset(comp) for comp in expected_components
    }
    assert result_components_set == expected_components_set


def test_disconnected_graph_forest_total_weight():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    comp0 = result.get_component(0)
    comp1 = result.get_component(1)

    abc_weight = sum(fe.weight for fe in result.forest_edges if fe.u in {"A", "B", "C"})
    def_weight = sum(fe.weight for fe in result.forest_edges if fe.u in {"D", "E", "F"})

    assert abc_weight == pytest.approx(1.0 + 2.0)
    assert def_weight == pytest.approx(3.0 + 4.0)
    assert result.total_weight == pytest.approx(1.0 + 2.0 + 3.0 + 4.0)


def test_forest_edges_correct_component_id():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    component_to_id = {}
    for idx, comp in enumerate(result.components):
        rep = min(comp, key=lambda x: hash(x))
        component_to_id[frozenset(comp)] = idx
        for fe in result.forest_edges:
            if fe.u in comp:
                assert fe.component_id == idx
            if fe.v in comp:
                assert fe.component_id == idx


def test_forest_connectivity_tracking():
    graph = build_disconnected_graph()
    kruskal = Kruskal(graph)
    result = kruskal.compute_mst()

    nodes = graph.get_nodes()
    verify_forest_connectivity(result, nodes, result.component_count)

    for cid in range(result.component_count):
        comp_edges = result.get_edges_by_component(cid)
        comp = result.get_component(cid)
        if len(comp) > 1:
            assert len(comp_edges) == len(comp) - 1
        else:
            assert len(comp_edges) == 0


def test_kruskal_incremental_build():
    kruskal = Kruskal[str]()
    kruskal.add_node("A")
    kruskal.add_node("B")
    kruskal.add_node("C")
    kruskal.add_edge("A", "B", 1.0)
    kruskal.add_edge("B", "C", 2.0)
    kruskal.add_edge("A", "C", 5.0)

    result = kruskal.compute_mst()

    assert result.edge_count == 2
    assert result.is_spanning_tree
    assert result.total_weight == pytest.approx(3.0)


def test_undirected_graph_edges_symmetric():
    graph = UndirectedWeightedGraph[str]()
    graph.add_edge("A", "B", 3.0)
    graph.add_edge("B", "C", 4.0)

    assert graph.has_edge("A", "B")
    assert graph.has_edge("B", "A")
    assert graph.has_edge("B", "C")
    assert graph.has_edge("C", "B")

    neighbors_a = graph.get_neighbors("A")
    neighbors_b = graph.get_neighbors("B")

    assert ("B", 3.0) in neighbors_a
    assert ("A", 3.0) in neighbors_b
    assert ("C", 4.0) in neighbors_b
