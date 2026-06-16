from __future__ import annotations

import pytest

from solocoder_py.dijkstra import Dijkstra, WeightedDigraph

from .conftest import (
    build_complex_graph,
    build_equal_path_graph,
    build_simple_graph,
)


class TestSimpleConnectedGraph:
    def test_shortest_path_simple_graph_distances(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        assert result.source == "A"
        assert result.get_distance("A") == 0.0
        assert result.get_distance("B") == 4.0
        assert result.get_distance("C") == 2.0
        assert result.get_distance("D") == 9.0
        assert result.get_distance("E") == 11.0

    def test_shortest_path_simple_graph_path_reconstruction(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        assert result.get_path("A") == ["A"]
        assert result.get_path("B") == ["A", "B"]
        assert result.get_path("C") == ["A", "C"]
        assert result.get_path("D") == ["A", "B", "D"]
        assert result.get_path("E") == ["A", "B", "D", "E"]

    def test_shortest_path_convenience_method(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        distance, path = dijkstra.shortest_path("A", "E")

        assert distance == 11.0
        assert path == ["A", "B", "D", "E"]

    def test_shortest_path_all_nodes_visited_without_target(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        assert not result.terminated_early
        assert set(result.visited) == {"A", "B", "C", "D", "E"}
        assert len(result.visited) == 5


class TestEarlyTermination:
    def test_early_termination_target_is_visited(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A", target="D")

        assert result.terminated_early
        assert result.target == "D"
        assert "D" in result.visited
        assert result.visited[-1] == "D"

    def test_early_termination_distance_correct(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A", target="D")

        assert result.get_distance("D") == 9.0
        assert result.get_path("D") == ["A", "B", "D"]

    def test_early_termination_unvisited_nodes_are_inf(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A", target="D")

        assert result.get_distance("D") == 9.0
        for node in set(result.distances.keys()) - set(result.visited):
            assert result.get_distance(node) == float("inf")
            assert not result.is_reachable(node)

    def test_early_termination_does_not_compute_all(self) -> None:
        full_result = Dijkstra(graph=build_simple_graph()).shortest_paths("A")
        early_result = Dijkstra(graph=build_simple_graph()).shortest_paths(
            "A", target="D"
        )

        assert len(early_result.visited) <= len(full_result.visited)
        assert "E" not in early_result.visited


class TestComplexGraph:
    def test_complex_graph_shortest_path(self) -> None:
        dijkstra = Dijkstra(graph=build_complex_graph())
        result = dijkstra.shortest_paths("S")

        assert result.get_distance("S") == 0.0
        assert result.get_distance("A") == 7.0
        assert result.get_distance("B") == 2.0
        assert result.get_distance("C") == 3.0
        assert result.get_distance("H") == 3.0
        assert result.get_distance("G") == 5.0
        assert result.get_distance("F") == 6.0
        assert result.get_distance("E") == 7.0
        assert result.get_distance("D") == 6.0
        assert result.get_distance("L") == 5.0
        assert result.get_distance("I") == 9.0
        assert result.get_distance("J") == 9.0
        assert result.get_distance("K") == 12.0

    def test_complex_graph_path_reconstruction(self) -> None:
        dijkstra = Dijkstra(graph=build_complex_graph())
        result = dijkstra.shortest_paths("S")

        assert result.get_path("S") == ["S"]
        assert result.get_path("B") == ["S", "B"]
        assert result.get_path("H") == ["S", "B", "H"]
        assert result.get_path("G") == ["S", "B", "H", "G"]
        assert result.get_path("E") == ["S", "B", "H", "G", "E"]


class TestEqualPathLengths:
    def test_equal_path_takes_one_of_the_valid_paths(self) -> None:
        dijkstra = Dijkstra(graph=build_equal_path_graph())
        distance, path = dijkstra.shortest_path("A", "D")

        assert distance == 3.0
        assert path in (
            ["A", "B", "D"],
            ["A", "C", "D"],
        )

    def test_equal_path_result_distance(self) -> None:
        dijkstra = Dijkstra(graph=build_equal_path_graph())
        result = dijkstra.shortest_paths("A")

        assert result.get_distance("D") == 3.0
        assert result.is_reachable("D")
