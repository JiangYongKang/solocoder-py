from __future__ import annotations

from itertools import permutations

import pytest

from solocoder_py.kahn import KahnTopologicalSort
from tests.kahn.conftest import (
    build_multi_source_dag,
    build_simple_dag,
    is_valid_topological_order,
)


class TestKahnNormalFlows:
    def test_simple_dag_topo_sort_correct(self) -> None:
        graph = build_simple_dag()
        kahn = KahnTopologicalSort(graph)
        result = kahn.sort()

        assert result.is_valid is True
        assert result.has_cycle is False
        assert len(result.order) == graph.node_count
        assert set(result.order) == set(graph.get_nodes())
        assert is_valid_topological_order(graph, result.order)

    def test_simple_dag_enumerate_all_orders(self) -> None:
        graph = build_simple_dag()
        kahn = KahnTopologicalSort(graph)
        all_orders = kahn.enumerate_all_topological_orders()

        assert len(all_orders) == 2

        orders_as_tuples = [tuple(o) for o in all_orders]
        assert ("A", "B", "C", "D") in orders_as_tuples
        assert ("A", "C", "B", "D") in orders_as_tuples

        for order in all_orders:
            assert is_valid_topological_order(graph, order)

    def test_multi_source_dag_enumerate_no_duplicates(self) -> None:
        graph = build_multi_source_dag()
        kahn = KahnTopologicalSort(graph)
        all_orders = kahn.enumerate_all_topological_orders()

        unique_orders = {tuple(o) for o in all_orders}
        assert len(all_orders) == len(unique_orders)

    def test_multi_source_dag_enumerate_all_valid(self) -> None:
        graph = build_multi_source_dag()
        kahn = KahnTopologicalSort(graph)
        all_orders = kahn.enumerate_all_topological_orders()

        for order in all_orders:
            assert is_valid_topological_order(graph, order)

    def test_multi_source_dag_full_permutation_count(self) -> None:
        graph = build_multi_source_dag()
        nodes = graph.get_nodes()
        kahn = KahnTopologicalSort(graph)
        all_orders = kahn.enumerate_all_topological_orders()

        valid_count = 0
        for perm in permutations(nodes):
            if is_valid_topological_order(graph, list(perm)):
                valid_count += 1

        assert len(all_orders) == valid_count

    def test_digraph_add_nodes_and_edges(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B")

        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert graph.has_node("A") is True
        assert graph.has_node("B") is True
        assert graph.has_edge("A", "B") is True
        assert graph.has_edge("B", "A") is False

    def test_digraph_in_degree_calculation(self) -> None:
        from solocoder_py.kahn import Digraph

        graph = Digraph()
        graph.add_edge("A", "B")
        graph.add_edge("A", "C")
        graph.add_edge("B", "D")
        graph.add_edge("C", "D")

        assert graph.get_in_degree("A") == 0
        assert graph.get_in_degree("B") == 1
        assert graph.get_in_degree("C") == 1
        assert graph.get_in_degree("D") == 2

    def test_kahn_via_add_methods(self) -> None:
        kahn = KahnTopologicalSort()
        kahn.add_node("A")
        kahn.add_node("B")
        kahn.add_edge("A", "B")

        result = kahn.sort()
        assert result.is_valid is True
        assert result.order == ["A", "B"]

    def test_sort_result_properties(self) -> None:
        graph = build_simple_dag()
        kahn = KahnTopologicalSort(graph)
        result = kahn.sort()

        assert result.is_valid is True
        assert result.has_cycle is False
        assert result.cycle_nodes == []
        assert len(result.order) == 4
