from __future__ import annotations

import pytest

from solocoder_py.graph_cycle import (
    Cycle,
    CycleDetector,
    DirectedGraph,
)


class TestSingleCycleDetection:
    def test_three_node_cycle_detected(self, single_cycle_3: DirectedGraph) -> None:
        detector = CycleDetector(single_cycle_3)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert len(cycles[0]) == 3
        assert set(cycles[0].nodes) == {"A", "B", "C"}

    def test_two_node_cycle_detected(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("X", "Y")
        graph.add_edge("Y", "X")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert len(cycles[0]) == 2
        assert set(cycles[0].nodes) == {"X", "Y"}

    def test_single_node_self_loop_detected(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("S", "S")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert len(cycles[0]) == 1
        assert cycles[0].nodes == ["S"]

    def test_cycle_path_follows_graph_edges(self, single_cycle_3: DirectedGraph) -> None:
        detector = CycleDetector(single_cycle_3)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        cycle_nodes = cycles[0].nodes
        assert len(cycle_nodes) == 3
        for i in range(len(cycle_nodes)):
            from_node = cycle_nodes[i]
            to_node = cycle_nodes[(i + 1) % len(cycle_nodes)]
            assert to_node in single_cycle_3.get_neighbors(from_node)

    def test_four_node_cycle_detected(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "A")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0].nodes) == {"A", "B", "C", "D"}


class TestMultipleCyclesDetection:
    def test_two_disjoint_cycles_all_detected(self, two_disjoint_cycles: DirectedGraph) -> None:
        detector = CycleDetector(two_disjoint_cycles)
        cycles = detector.detect_cycles()
        assert len(cycles) == 2
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A", "B"} in cycle_node_sets
        assert {"C", "D", "E"} in cycle_node_sets

    def test_three_disjoint_cycles_all_detected(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "A")
        graph.add_edge("B", "C")
        graph.add_edge("C", "B")
        graph.add_edge("D", "E")
        graph.add_edge("E", "F")
        graph.add_edge("F", "D")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        assert len(cycles) == 3
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert {"A"} in cycle_node_sets
        assert {"B", "C"} in cycle_node_sets
        assert {"D", "E", "F"} in cycle_node_sets

    def test_cycles_not_duplicated(self) -> None:
        graph = DirectedGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")
        graph.add_edge("A", "C")
        detector = CycleDetector(graph)
        cycles = detector.detect_cycles()
        cycle_node_sets = [set(c.nodes) for c in cycles]
        assert cycle_node_sets.count({"A", "B", "C"}) == 1


class TestCycleDeduplication:
    def test_same_cycle_different_start_is_one_cycle(self) -> None:
        cycle1 = Cycle(nodes=["A", "B", "C"])
        cycle2 = Cycle(nodes=["B", "C", "A"])
        cycle3 = Cycle(nodes=["C", "A", "B"])
        assert cycle1 == cycle2 == cycle3

    def test_different_cycles_are_not_equal(self) -> None:
        cycle1 = Cycle(nodes=["A", "B", "C"])
        cycle2 = Cycle(nodes=["A", "B", "D"])
        assert cycle1 != cycle2

    def test_self_loop_equality(self) -> None:
        cycle1 = Cycle(nodes=["X"])
        cycle2 = Cycle(nodes=["X"])
        assert cycle1 == cycle2

    def test_cycle_hash_consistency(self) -> None:
        cycle1 = Cycle(nodes=["A", "B", "C"])
        cycle2 = Cycle(nodes=["B", "C", "A"])
        assert hash(cycle1) == hash(cycle2)
