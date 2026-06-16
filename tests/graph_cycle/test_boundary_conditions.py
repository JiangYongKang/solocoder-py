from __future__ import annotations

import pytest

from solocoder_py.graph_cycle import (
    Cycle,
    CycleDetector,
    DirectedGraph,
)


class TestDAGReturnsEmpty:
    def test_dag_no_cycles(self, dag_graph: DirectedGraph) -> None:
        detector = CycleDetector(dag_graph)
        cycles = detector.detect_cycles()
        assert cycles == []

    def test_linear_chain_no_cycles(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert cycles == []

    def test_single_node_no_self_loop(self) -> None:
        graph = DirectedGraph()
        graph.add_node("A")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert cycles == []

    def test_disconnected_dag_no_cycles(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("C", "D")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert cycles == []


class TestSelfLoopDetection:
    def test_self_loop_detected(self, self_loop_graph: DirectedGraph) -> None:
        detector = CycleDetector(self_loop_graph)
        cycles = detector.detect_cycles()
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A"} in cycle_node_sets
        assert {"B", "C"} in cycle_node_sets
        assert len(cycles) == 2

    def test_self_loop_is_reported_separately(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        graph.add_edge("A", "A")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A"} in cycle_node_sets
        assert {"A", "B"} in cycle_node_sets
        assert len(cycles) == 2

    def test_multiple_self_loops(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("X", "X")
        graph.add_edge("Y", "Y")
        graph.add_edge("Z", "Z")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 3
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"X"} in cycle_node_sets
        assert {"Y"} in cycle_node_sets
        assert {"Z"} in cycle_node_sets


class TestNestedCycles:
    def test_nested_cycles_all_detected(self, nested_cycles: DirectedGraph) -> None:
        detector = CycleDetector(nested_cycles)
        cycles = detector.detect_cycles()
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A", "B", "C"} in cycle_node_sets
        assert {"B", "D"} in cycle_node_sets
        assert len(cycles) == 2


class TestCompoundCycles:
    def test_compound_cycle_with_subcycle(self, compound_cycle: DirectedGraph) -> None:
        detector = CycleDetector(compound_cycle)
        cycles = detector.detect_cycles()
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A", "B", "C", "D"} in cycle_node_sets
        assert {"B", "C"} in cycle_node_sets
        assert len(cycles) == 2

    def test_each_reported_cycle_path_is_valid(self, compound_cycle: DirectedGraph) -> None:
        detector = CycleDetector(compound_cycle)
        cycles = detector.detect_cycles()
        for cycle in cycles:
            nodes = cycle.nodes
            for i in range(len(nodes)):
                from_node = nodes[i]
                to_node = nodes[(i + 1) % len(nodes)]
                assert to_node in compound_cycle.get_neighbors(from_node)


class TestHasCycleMethod:
    def test_has_cycle_true_for_cyclic_graph(self, single_cycle_3: DirectedGraph) -> None:
        detector = CycleDetector(single_cycle_3)
        assert detector.has_cycle() is True

    def test_has_cycle_false_for_dag(self, dag_graph: DirectedGraph) -> None:
        detector = CycleDetector(dag_graph)
        assert detector.has_cycle() is False

    def test_has_cycle_false_for_empty_graph(self, empty_graph: DirectedGraph) -> None:
        detector = CycleDetector(empty_graph)
        assert detector.has_cycle() is False


class TestGetCycleNodes:
    def test_get_cycle_nodes_returns_all_nodes_in_any_cycle(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        graph.add_edge("C", "D")
        graph.add_edge("D", "C")
        graph.add_edge("E", "F")
        detector = CycleDetector(graph)
        cycle_nodes = detector.get_cycle_nodes()
        assert cycle_nodes == {"A", "B", "C", "D"}

    def test_get_cycle_nodes_empty_for_dag(self, dag_graph: DirectedGraph) -> None:
        detector = CycleDetector(dag_graph)
        assert detector.get_cycle_nodes() == set()
