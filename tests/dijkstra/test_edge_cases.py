from __future__ import annotations

import pytest

from solocoder_py.dijkstra import Dijkstra, WeightedDigraph

from .conftest import build_zero_weight_graph


class TestSourceEqualsTarget:
    def test_source_is_target_distance_zero(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("A", "B", 1.0)
        graph.add_edge("B", "C", 2.0)
        dijkstra = Dijkstra(graph=graph)

        distance, path = dijkstra.shortest_path("A", "A")
        assert distance == 0.0
        assert path == ["A"]

    def test_source_is_target_in_shortest_paths(self) -> None:
        graph = WeightedDigraph()
        graph.add_node("X")
        dijkstra = Dijkstra(graph=graph)

        result = dijkstra.shortest_paths("X", target="X")
        assert result.terminated_early
        assert result.get_distance("X") == 0.0
        assert result.get_path("X") == ["X"]


class TestSingleNodeGraph:
    def test_single_node_no_edges(self) -> None:
        graph = WeightedDigraph()
        graph.add_node("only")
        dijkstra = Dijkstra(graph=graph)

        result = dijkstra.shortest_paths("only")
        assert result.source == "only"
        assert result.get_distance("only") == 0.0
        assert result.get_path("only") == ["only"]
        assert result.visited == ["only"]
        assert not result.terminated_early

    def test_single_node_self_loop_zero_weight(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("only", "only", 0.0)
        dijkstra = Dijkstra(graph=graph)

        result = dijkstra.shortest_paths("only")
        assert result.get_distance("only") == 0.0
        assert result.get_path("only") == ["only"]


class TestZeroWeightEdges:
    def test_zero_weight_edge_path(self) -> None:
        dijkstra = Dijkstra(graph=build_zero_weight_graph())
        result = dijkstra.shortest_paths("A")

        assert result.get_distance("A") == 0.0
        assert result.get_distance("B") == 0.0
        assert result.get_distance("C") == 0.0

    def test_zero_weight_edge_path_reconstruction(self) -> None:
        dijkstra = Dijkstra(graph=build_zero_weight_graph())
        result = dijkstra.shortest_paths("A")

        path_c = result.get_path("C")
        assert result.get_distance("C") == 0.0
        assert path_c in (["A", "B", "C"], ["A", "C"])

    def test_zero_weight_edge_does_not_break_algorithm(self) -> None:
        dijkstra = Dijkstra(graph=build_zero_weight_graph())
        distance, path = dijkstra.shortest_path("A", "C")

        assert distance == 0.0
        assert "A" in path
        assert "C" in path


class TestLargeGraphProperties:
    def test_graph_node_count(self) -> None:
        graph = WeightedDigraph()
        assert graph.node_count == 0

        graph.add_node("A")
        assert graph.node_count == 1

        graph.add_edge("A", "B", 1.0)
        assert graph.node_count == 2

    def test_graph_edge_count(self) -> None:
        graph = WeightedDigraph()
        assert graph.edge_count == 0

        graph.add_edge("A", "B", 1.0)
        graph.add_edge("A", "C", 2.0)
        graph.add_edge("B", "C", 3.0)
        assert graph.edge_count == 3

    def test_graph_get_nodes_sorted(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("C", "A", 1.0)
        graph.add_edge("B", "D", 1.0)

        assert graph.get_nodes() == ["A", "B", "C", "D"]

    def test_graph_has_node_and_edge(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("X", "Y", 5.0)

        assert graph.has_node("X")
        assert graph.has_node("Y")
        assert not graph.has_node("Z")
        assert graph.has_edge("X", "Y")
        assert not graph.has_edge("Y", "X")
        assert not graph.has_edge("X", "Z")

    def test_graph_remove_node(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("A", "B", 1.0)
        graph.add_edge("B", "C", 2.0)
        graph.add_edge("A", "C", 3.0)

        assert graph.node_count == 3
        assert graph.edge_count == 3

        graph.remove_node("B")
        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert not graph.has_node("B")
        assert not graph.has_edge("A", "B")
        assert not graph.has_edge("B", "C")
        assert graph.has_edge("A", "C")

    def test_graph_remove_edge(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("A", "B", 1.0)
        graph.add_edge("A", "C", 2.0)

        graph.remove_edge("A", "B")
        assert graph.edge_count == 1
        assert not graph.has_edge("A", "B")
        assert graph.has_edge("A", "C")
        assert graph.has_node("B")
