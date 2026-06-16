from __future__ import annotations

from typing import List, Tuple

import pytest

from solocoder_py.dijkstra import Dijkstra, WeightedDigraph


@pytest.fixture
def empty_graph() -> WeightedDigraph:
    return WeightedDigraph()


@pytest.fixture
def dijkstra() -> Dijkstra:
    return Dijkstra()


def build_simple_graph() -> WeightedDigraph:
    graph = WeightedDigraph()
    graph.add_edge("A", "B", 4.0)
    graph.add_edge("A", "C", 2.0)
    graph.add_edge("B", "C", 1.0)
    graph.add_edge("B", "D", 5.0)
    graph.add_edge("C", "D", 8.0)
    graph.add_edge("C", "E", 10.0)
    graph.add_edge("D", "E", 2.0)
    return graph


def build_disconnected_graph() -> WeightedDigraph:
    graph = WeightedDigraph()
    graph.add_edge("A", "B", 1.0)
    graph.add_edge("B", "C", 2.0)
    graph.add_node("D")
    graph.add_edge("E", "F", 3.0)
    return graph


def build_equal_path_graph() -> WeightedDigraph:
    graph = WeightedDigraph()
    graph.add_edge("A", "B", 1.0)
    graph.add_edge("A", "C", 2.0)
    graph.add_edge("B", "D", 2.0)
    graph.add_edge("C", "D", 1.0)
    return graph


def build_zero_weight_graph() -> WeightedDigraph:
    graph = WeightedDigraph()
    graph.add_edge("A", "B", 0.0)
    graph.add_edge("B", "C", 0.0)
    graph.add_edge("A", "C", 5.0)
    return graph


def build_complex_graph() -> WeightedDigraph:
    graph = WeightedDigraph()
    edges: List[Tuple[str, str, float]] = [
        ("S", "A", 7),
        ("S", "B", 2),
        ("S", "C", 3),
        ("A", "D", 4),
        ("A", "B", 3),
        ("B", "D", 4),
        ("B", "H", 1),
        ("C", "L", 2),
        ("D", "F", 5),
        ("H", "F", 3),
        ("H", "G", 2),
        ("G", "E", 2),
        ("L", "I", 4),
        ("L", "J", 4),
        ("I", "K", 4),
        ("J", "K", 4),
        ("F", "E", 1),
        ("E", "K", 5),
    ]
    for u, v, w in edges:
        graph.add_edge(u, v, w)
    return graph
