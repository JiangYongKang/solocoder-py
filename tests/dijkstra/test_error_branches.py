from __future__ import annotations

import pytest

from solocoder_py.dijkstra import (
    Dijkstra,
    DijkstraError,
    NegativeWeightError,
    NodeNotFoundError,
    UnreachableNodeError,
    WeightedDigraph,
)

from .conftest import build_disconnected_graph, build_simple_graph


class TestUnreachableNodes:
    def test_unreachable_node_is_not_reachable(self) -> None:
        dijkstra = Dijkstra(graph=build_disconnected_graph())
        result = dijkstra.shortest_paths("A")

        assert result.is_reachable("A")
        assert result.is_reachable("B")
        assert result.is_reachable("C")
        assert not result.is_reachable("D")
        assert not result.is_reachable("E")
        assert not result.is_reachable("F")

    def test_unreachable_node_distance_is_infinity(self) -> None:
        dijkstra = Dijkstra(graph=build_disconnected_graph())
        result = dijkstra.shortest_paths("A")

        assert result.get_distance("D") == float("inf")
        assert result.get_distance("E") == float("inf")

    def test_unreachable_node_get_path_raises(self) -> None:
        dijkstra = Dijkstra(graph=build_disconnected_graph())
        result = dijkstra.shortest_paths("A")

        with pytest.raises(UnreachableNodeError) as exc:
            result.get_path("D")
        assert "unreachable" in str(exc.value).lower()
        assert "D" in str(exc.value)
        assert "A" in str(exc.value)

    def test_shortest_path_method_raises_for_unreachable(self) -> None:
        dijkstra = Dijkstra(graph=build_disconnected_graph())

        with pytest.raises(UnreachableNodeError) as exc:
            dijkstra.shortest_path("A", "D")
        assert "unreachable" in str(exc.value).lower()


class TestNegativeWeightEdges:
    def test_add_negative_weight_edge_raises(self) -> None:
        graph = WeightedDigraph()

        with pytest.raises(NegativeWeightError) as exc:
            graph.add_edge("A", "B", -1.0)
        assert "non-negative" in str(exc.value).lower()
        assert "-1.0" in str(exc.value) or "-1" in str(exc.value)

    def test_add_negative_weight_edge_via_dijkstra_raises(
        self, dijkstra: Dijkstra
    ) -> None:
        with pytest.raises(NegativeWeightError):
            dijkstra.add_edge("X", "Y", -5.0)

    def test_zero_weight_is_allowed(self) -> None:
        graph = WeightedDigraph()
        graph.add_edge("A", "B", 0.0)
        assert graph.has_edge("A", "B")
        assert graph.get_edge_weight("A", "B") == 0.0


class TestNodeNotFoundErrors:
    def test_shortest_paths_source_not_found(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())

        with pytest.raises(NodeNotFoundError) as exc:
            dijkstra.shortest_paths("Z")
        assert "Z" in str(exc.value)
        assert "source" in str(exc.value).lower()

    def test_shortest_paths_target_not_found(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())

        with pytest.raises(NodeNotFoundError) as exc:
            dijkstra.shortest_paths("A", target="Z")
        assert "Z" in str(exc.value)
        assert "target" in str(exc.value).lower()

    def test_shortest_path_source_not_found(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())

        with pytest.raises(NodeNotFoundError):
            dijkstra.shortest_path("Z", "A")

    def test_shortest_path_target_not_found(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())

        with pytest.raises(NodeNotFoundError):
            dijkstra.shortest_path("A", "Z")

    def test_get_neighbors_not_found(self) -> None:
        graph = WeightedDigraph()
        graph.add_node("A")

        with pytest.raises(NodeNotFoundError):
            list(graph.get_neighbors("Z"))

    def test_remove_node_not_found(self) -> None:
        graph = WeightedDigraph()

        with pytest.raises(NodeNotFoundError):
            graph.remove_node("X")

    def test_result_get_distance_node_not_in_result(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        with pytest.raises(NodeNotFoundError):
            result.get_distance("Z")

    def test_result_get_path_node_not_in_result(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        with pytest.raises(NodeNotFoundError):
            result.get_path("Z")

    def test_result_is_reachable_node_not_in_result(self) -> None:
        dijkstra = Dijkstra(graph=build_simple_graph())
        result = dijkstra.shortest_paths("A")

        with pytest.raises(NodeNotFoundError):
            result.is_reachable("Z")


class TestOtherErrors:
    def test_empty_node_identifier_raises(self) -> None:
        graph = WeightedDigraph()

        with pytest.raises(DijkstraError):
            graph.add_node("")

    def test_remove_nonexistent_edge_raises(self) -> None:
        graph = WeightedDigraph()
        graph.add_node("A")
        graph.add_node("B")

        with pytest.raises(DijkstraError):
            graph.remove_edge("A", "B")

    def test_get_nonexistent_edge_weight_raises(self) -> None:
        graph = WeightedDigraph()
        graph.add_node("A")
        graph.add_node("B")

        with pytest.raises(DijkstraError):
            graph.get_edge_weight("A", "B")
