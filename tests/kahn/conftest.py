from __future__ import annotations

from typing import List, Tuple

import pytest

from solocoder_py.kahn import Digraph, KahnTopologicalSort


@pytest.fixture
def empty_graph() -> Digraph:
    return Digraph()


@pytest.fixture
def kahn() -> KahnTopologicalSort:
    return KahnTopologicalSort()


def build_simple_dag() -> Digraph:
    graph = Digraph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")
    return graph


def build_linear_chain() -> Digraph:
    graph = Digraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    return graph


def build_discrete_nodes() -> Digraph:
    graph = Digraph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    return graph


def build_10_discrete_nodes() -> Digraph:
    graph = Digraph()
    for i in range(10):
        graph.add_node(f"N{i}")
    return graph


def build_simple_cycle() -> Digraph:
    graph = Digraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    return graph


def build_cycle_with_tail() -> Digraph:
    graph = Digraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "B")
    graph.add_edge("C", "D")
    return graph


def build_multi_source_dag() -> Digraph:
    graph = Digraph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "C")
    graph.add_edge("C", "D")
    graph.add_edge("C", "E")
    return graph


def build_fully_connected_dag() -> Digraph:
    graph = Digraph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("A", "D")
    graph.add_edge("B", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")
    return graph


def get_node_set(graph: Digraph) -> set[str]:
    return set(graph.get_nodes())


def is_valid_topological_order(graph: Digraph, order: List[str]) -> bool:
    if set(order) != get_node_set(graph):
        return False
    if len(order) != graph.node_count:
        return False
    node_pos = {node: i for i, node in enumerate(order)}
    for edge in graph.get_edges():
        if node_pos[edge.from_node] >= node_pos[edge.to_node]:
            return False
    return True
