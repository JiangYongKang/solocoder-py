from __future__ import annotations

import pytest

from solocoder_py.kahn import (
    CycleDetectedError,
    KahnError,
    KahnTopologicalSort,
    NodeNotFoundError,
)
from tests.kahn.conftest import build_cycle_with_tail, build_simple_cycle


class TestKahnErrorBranches:
    def test_simple_cycle_detected(self) -> None:
        graph = build_simple_cycle()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is False
        assert result.has_cycle is True
        assert len(result.cycle_nodes) == 3
        assert set(result.cycle_nodes) == {"A", "B", "C"}

    def test_simple_cycle_detect_cycle_returns_nodes(self) -> None:
        graph = build_simple_cycle()
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert len(cycle_nodes) == 3
        assert set(cycle_nodes) == {"A", "B", "C"}

    def test_cycle_with_tail_detected(self) -> None:
        graph = build_cycle_with_tail()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is False
        assert result.has_cycle is True
        assert "A" not in result.cycle_nodes
        cycle_set = set(result.cycle_nodes)
        assert "B" in cycle_set
        assert "C" in cycle_set

    def test_enumerate_on_cyclic_graph_raises(self) -> None:
        graph = build_simple_cycle()
        kahn = KahnTopologicalSort(graph)

        with pytest.raises(CycleDetectedError) as exc_info:
            kahn.enumerate_all_topological_orders()

        assert exc_info.value.cycle_nodes is not None
        assert len(exc_info.value.cycle_nodes) > 0

    def test_get_in_degree_nonexistent_node_raises(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("A")

        with pytest.raises(NodeNotFoundError):
            graph.get_in_degree("Z")

    def test_get_neighbors_nonexistent_node_raises(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()

        with pytest.raises(NodeNotFoundError):
            list(graph.get_neighbors("Z"))

    def test_remove_nonexistent_node_raises(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()

        with pytest.raises(NodeNotFoundError):
            graph.remove_node("Z")

    def test_remove_nonexistent_edge_raises(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("A")
        graph.add_node("B")

        with pytest.raises(KahnError):
            graph.remove_edge("A", "B")

    def test_add_empty_node_raises(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()

        with pytest.raises(KahnError):
            graph.add_node("")

    def test_dag_detect_cycle_returns_empty(self) -> None:
        from tests.kahn.conftest import build_simple_dag

        graph = build_simple_dag()
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert cycle_nodes == []

    def test_empty_graph_detect_cycle_returns_empty(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert cycle_nodes == []

    def test_cycle_detected_error_inheritance(self) -> None:
        err = CycleDetectedError("test cycle", cycle_nodes=["A", "B"])
        assert isinstance(err, KahnError)
        assert err.cycle_nodes == ["A", "B"]

    def test_node_not_found_error_inheritance(self) -> None:
        err = NodeNotFoundError("node missing")
        assert isinstance(err, KahnError)
