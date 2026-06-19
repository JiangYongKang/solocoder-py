from __future__ import annotations

import math

import pytest

from solocoder_py.kahn import KahnTopologicalSort
from tests.kahn.conftest import (
    build_10_discrete_nodes,
    build_discrete_nodes,
    build_fully_connected_dag,
    build_linear_chain,
    get_node_set,
    is_valid_topological_order,
)


class TestKahnEdgeCases:
    def test_single_node_graph(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("A")
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is True
        assert result.order == ["A"]
        assert result.has_cycle is False

        all_orders = list(kahn.enumerate_all_topological_orders())
        assert len(all_orders) == 1
        assert all_orders[0] == ["A"]

    def test_linear_chain_unique_order(self) -> None:
        graph = build_linear_chain()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is True
        assert is_valid_topological_order(graph, result.order)
        assert set(result.order) == get_node_set(graph)

        all_orders = list(kahn.enumerate_all_topological_orders())
        assert len(all_orders) == 1
        assert is_valid_topological_order(graph, all_orders[0])

        expected_order = ["A", "B", "C", "D", "E"]
        assert all_orders[0] == expected_order

    def test_fully_connected_dag_unique_order(self) -> None:
        graph = build_fully_connected_dag()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is True
        assert is_valid_topological_order(graph, result.order)
        assert set(result.order) == get_node_set(graph)

        all_orders = list(kahn.enumerate_all_topological_orders())
        assert len(all_orders) == 1
        assert is_valid_topological_order(graph, all_orders[0])

    def test_discrete_nodes_all_permutations_valid(self) -> None:
        graph = build_discrete_nodes()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is True
        assert len(result.order) == 4
        assert set(result.order) == {"A", "B", "C", "D"}

        all_orders = list(kahn.enumerate_all_topological_orders())
        assert len(all_orders) == 24

        for order in all_orders:
            assert is_valid_topological_order(graph, order)

        unique_orders = {tuple(o) for o in all_orders}
        assert len(unique_orders) == 24

    def test_empty_graph_sort_returns_empty(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        kahn = KahnTopologicalSort(graph)

        result = kahn.sort()
        assert result.is_valid is True
        assert result.order == []
        assert result.has_cycle is False
        assert result.cycle_nodes == []

    def test_empty_graph_enumerate_returns_single_empty(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        kahn = KahnTopologicalSort(graph)

        all_orders = list(kahn.enumerate_all_topological_orders())
        assert all_orders == [[]]

    def test_discrete_nodes_detect_cycle_returns_empty(self) -> None:
        graph = build_discrete_nodes()
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert cycle_nodes == []

    def test_linear_chain_detect_cycle_returns_empty(self) -> None:
        graph = build_linear_chain()
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert cycle_nodes == []

    def test_single_node_detect_cycle_returns_empty(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("X")
        kahn = KahnTopologicalSort(graph)

        cycle_nodes = kahn.detect_cycle()
        assert cycle_nodes == []

    def test_add_duplicate_edge_no_effect(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_edge("A", "B")
        graph.add_edge("A", "B")

        assert graph.edge_count == 1
        assert graph.get_in_degree("B") == 1

    def test_add_duplicate_node_no_effect(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("A")
        graph.add_node("A")

        assert graph.node_count == 1

    def test_remove_node_updates_in_degree(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("A", "C")

        assert graph.get_in_degree("C") == 2

        graph.remove_node("B")

        assert graph.has_node("B") is False
        assert graph.get_in_degree("C") == 1
        assert graph.edge_count == 1

    def test_remove_edge_updates_in_degree(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_edge("A", "B")
        graph.add_edge("A", "C")
        graph.add_edge("B", "C")

        assert graph.get_in_degree("C") == 2

        graph.remove_edge("B", "C")

        assert graph.has_edge("B", "C") is False
        assert graph.get_in_degree("C") == 1
        assert graph.edge_count == 2

    def test_10_discrete_nodes_enumerate_count_matches_factorial(self) -> None:
        graph = build_10_discrete_nodes()
        kahn = KahnTopologicalSort(graph)

        gen = kahn.enumerate_all_topological_orders()

        expected_count = math.factorial(10)
        count = 0
        seen_first = None
        for order in gen:
            if count == 0:
                seen_first = order
            assert len(order) == 10
            assert is_valid_topological_order(graph, order)
            count += 1

        assert count == expected_count
        assert seen_first is not None

    def test_10_discrete_nodes_enumerate_lazy_memory(self) -> None:
        import gc
        import sys

        graph = build_10_discrete_nodes()
        kahn = KahnTopologicalSort(graph)

        gen = kahn.enumerate_all_topological_orders()

        first_100 = []
        for i, order in enumerate(gen):
            first_100.append(tuple(order))
            if i >= 99:
                break

        assert len(first_100) == 100
        assert len(set(first_100)) == 100

        gen_size = sys.getsizeof(gen)
        list_100_size = sum(sys.getsizeof(o) for o in first_100)
        assert gen_size < list_100_size

        del first_100
        gc.collect()

        remaining_count = 0
        for _ in gen:
            remaining_count += 1

        assert remaining_count == math.factorial(10) - 100
