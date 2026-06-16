from __future__ import annotations

from typing import Any, Dict, List

import pytest

from solocoder_py.graph_cycle import CycleDetector, DirectedGraph


@pytest.fixture
def empty_graph() -> DirectedGraph:
    return DirectedGraph()


@pytest.fixture
def empty_detector() -> CycleDetector:
    return CycleDetector()


def build_single_cycle_graph(nodes: List[Any]) -> DirectedGraph:
    graph = DirectedGraph()
    for i in range(len(nodes)):
        graph.add_edge(nodes[i], nodes[(i + 1) % len(nodes)])
    return graph


def build_dag_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    return graph


def build_two_disjoint_cycles_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    graph.add_edge("E", "C")
    return graph


def build_nested_cycles_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    graph.add_edge("B", "D")
    graph.add_edge("D", "B")
    return graph


def build_self_loop_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "A")
    graph.add_edge("B", "C")
    graph.add_edge("C", "B")
    return graph


def build_compound_cycle_with_subcycle_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "D")
    graph.add_edge("D", "A")
    graph.add_edge("C", "B")
    return graph


def build_unreachable_cycle_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("C", "D")
    graph.add_edge("D", "E")
    graph.add_edge("E", "C")
    return graph


def build_multiple_entry_cycle_graph() -> DirectedGraph:
    graph = DirectedGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "B")
    graph.add_edge("D", "B")
    graph.add_edge("C", "E")
    return graph


@pytest.fixture
def single_cycle_3() -> DirectedGraph:
    return build_single_cycle_graph(["A", "B", "C"])


@pytest.fixture
def dag_graph() -> DirectedGraph:
    return build_dag_graph()


@pytest.fixture
def two_disjoint_cycles() -> DirectedGraph:
    return build_two_disjoint_cycles_graph()


@pytest.fixture
def nested_cycles() -> DirectedGraph:
    return build_nested_cycles_graph()


@pytest.fixture
def self_loop_graph() -> DirectedGraph:
    return build_self_loop_graph()


@pytest.fixture
def compound_cycle() -> DirectedGraph:
    return build_compound_cycle_with_subcycle_graph()


@pytest.fixture
def unreachable_cycle() -> DirectedGraph:
    return build_unreachable_cycle_graph()
