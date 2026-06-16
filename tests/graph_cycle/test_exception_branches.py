from __future__ import annotations

import pytest

from solocoder_py.graph_cycle import (
    CycleDetector,
    DirectedGraph,
    NodeNotFoundError,
)


class TestEmptyGraph:
    def test_empty_graph_detect_cycles_returns_empty(self, empty_detector: CycleDetector) -> None:
        cycles = empty_detector.detect_cycles()
        assert cycles == []

    def test_empty_graph_has_cycle_false(self, empty_detector: CycleDetector) -> None:
        assert empty_detector.has_cycle() is False

    def test_empty_graph_node_count_zero(self, empty_graph: DirectedGraph) -> None:
        assert empty_graph.node_count == 0
        assert empty_graph.edge_count == 0


class TestUnreachableCycles:
    def test_unreachable_cycle_still_detected(self, unreachable_cycle: DirectedGraph) -> None:
        detector = CycleDetector(unreachable_cycle)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"C", "D", "E"}

    def test_both_reachable_and_unreachable_cycles_detected(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        graph.add_edge("C", "D")
        graph.add_edge("D", "E")
        graph.add_edge("E", "C")
        graph.add_edge("F", "G")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 2
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A", "B"} in cycle_node_sets
        assert {"C", "D", "E"} in cycle_node_sets


class TestDetectCyclesFromNode:
    def test_detect_from_start_node_finds_cycle(self, single_cycle_3: DirectedGraph) -> None:
        detector = CycleDetector(single_cycle_3)
        cycles = detector.detect_cycles_from_node("A")
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"A", "B", "C"}

    def test_detect_from_node_not_in_cycle_but_reaches_it(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("X", "A")
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles_from_node("X")
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"A", "B"}

    def test_detect_from_nonexistent_node_raises(self, empty_detector: CycleDetector) -> None:
        with pytest.raises(NodeNotFoundError, match="Node not found"):
            empty_detector.detect_cycles_from_node("nonexistent")

    def test_detect_from_dag_node_returns_empty(self, dag_graph: DirectedGraph) -> None:
        detector = CycleDetector(dag_graph)
        cycles = detector.detect_cycles_from_node("A")
        assert cycles == []


class TestGraphOperations:
    def test_get_neighbors_for_nonexistent_node_raises(self, empty_graph: DirectedGraph) -> None:
        with pytest.raises(NodeNotFoundError, match="Node not found"):
            empty_graph.get_neighbors("missing")

    def test_has_node_true_for_existing(self, single_cycle_3: DirectedGraph) -> None:
        assert single_cycle_3.has_node("A") is True
        assert single_cycle_3.has_node("Z") is False

    def test_add_node_then_edge(self) -> None:
        detector = CycleDetector()
        detector.add_node("X")
        detector.add_node("Y")
        detector.add_edge("X", "Y")
        detector.add_edge("Y", "X")
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"X", "Y"}

    def test_set_graph_replaces_graph(self) -> None:
        detector = CycleDetector()
        graph1 = DirectedGraph()
        graph1.add_edge("A", "A")
        detector.set_graph(graph1)
        assert detector.detect_cycles()[0].nodes == ["A"]

        graph2 = DirectedGraph()
        graph2.add_edge("X", "Y")
        graph2.add_edge("Y", "X")
        detector.set_graph(graph2)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"X", "Y"}


class TestGraphEdgesDeduplication:
    def test_duplicate_edges_are_deduplicated(self) -> None:
        graph = DirectedGraph(_adjacency={"A": ["B", "B", "C", "B"]})
        neighbors = graph.get_neighbors("A")
        assert neighbors == ["B", "C"]
        assert graph.edge_count == 2

    def test_neighbors_listed_in_original_order_after_dedup(self) -> None:
        graph = DirectedGraph(_adjacency={"A": ["C", "B", "A", "B", "C"]})
        neighbors = graph.get_neighbors("A")
        assert neighbors == ["C", "B", "A"]
