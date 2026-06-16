from __future__ import annotations

from typing import List, Tuple

import pytest

from solocoder_py.scc import DirectedGraph, TarjanSCC


@pytest.fixture
def empty_graph() -> DirectedGraph:
    return DirectedGraph()


@pytest.fixture
def multi_scc_graph() -> DirectedGraph:
    g = DirectedGraph()
    edges: List[Tuple[int, int]] = [
        (0, 1), (1, 2), (2, 0),
        (2, 3),
        (3, 4), (4, 5), (5, 3),
        (5, 6),
        (6, 7), (7, 8), (8, 6),
    ]
    g.add_edges(edges)
    return g


@pytest.fixture
def strongly_connected_graph() -> DirectedGraph:
    g = DirectedGraph()
    edges: List[Tuple[int, int]] = [
        (0, 1), (1, 2), (2, 0),
        (0, 3), (3, 0),
        (1, 3), (3, 1),
    ]
    g.add_edges(edges)
    return g


@pytest.fixture
def discrete_graph() -> DirectedGraph:
    g = DirectedGraph()
    for i in range(5):
        g.add_node(i)
    return g


@pytest.fixture
def graph_with_self_loops() -> DirectedGraph:
    g = DirectedGraph()
    edges: List[Tuple[int, int]] = [
        (0, 0),
        (0, 1), (1, 0),
        (1, 2), (2, 2),
        (2, 3), (3, 2),
    ]
    g.add_edges(edges)
    return g


@pytest.fixture
def graph_with_parallel_edges() -> DirectedGraph:
    g = DirectedGraph()
    edges: List[Tuple[int, int]] = [
        (0, 1), (1, 0),
        (0, 2), (0, 2), (0, 2),
        (1, 2), (1, 2),
        (2, 3), (3, 2),
        (2, 4),
        (4, 5), (5, 4),
        (3, 4), (3, 4),
    ]
    g.add_edges(edges)
    return g


@pytest.fixture
def tarjan_multi_scc(multi_scc_graph: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(multi_scc_graph)


@pytest.fixture
def tarjan_strongly_connected(strongly_connected_graph: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(strongly_connected_graph)


@pytest.fixture
def tarjan_discrete(discrete_graph: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(discrete_graph)


@pytest.fixture
def tarjan_self_loops(graph_with_self_loops: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(graph_with_self_loops)


@pytest.fixture
def tarjan_parallel(graph_with_parallel_edges: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(graph_with_parallel_edges)


@pytest.fixture
def tarjan_empty(empty_graph: DirectedGraph) -> TarjanSCC:
    return TarjanSCC(empty_graph)
