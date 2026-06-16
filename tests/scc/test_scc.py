from __future__ import annotations

from typing import List, Set, Tuple

import pytest

from solocoder_py.scc import (
    CondensationGraph,
    DirectedGraph,
    EmptyGraphError,
    NodeNotFoundError,
    SCCResult,
    TarjanSCC,
)


class TestMultiSCCGraph:
    def test_scc_correct_grouping(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        assert len(result) == 3

        components = [set(c) for c in result.components]
        expected_components = [
            {0, 1, 2},
            {3, 4, 5},
            {6, 7, 8},
        ]
        for expected in expected_components:
            assert expected in components

    def test_node_to_component_mapping(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()

        c0 = result.get_component_id(0)
        assert result.get_component_id(1) == c0
        assert result.get_component_id(2) == c0

        c1 = result.get_component_id(3)
        assert result.get_component_id(4) == c1
        assert result.get_component_id(5) == c1

        c2 = result.get_component_id(6)
        assert result.get_component_id(7) == c2
        assert result.get_component_id(8) == c2

        assert c0 < c1 < c2

    def test_component_to_nodes_mapping(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        for cid in range(len(result)):
            nodes = result.get_component_nodes(cid)
            assert len(nodes) > 0
            for node in nodes:
                assert result.get_component_id(node) == cid

    def test_condensation_is_dag(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)
        assert condensation.is_dag() is True

    def test_condensation_edges(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)

        c0 = result.get_component_id(0)
        c1 = result.get_component_id(3)
        c2 = result.get_component_id(6)

        assert condensation.has_edge(c0, c1) is True
        assert condensation.has_edge(c1, c2) is True
        assert condensation.has_edge(c0, c2) is False

        edges = condensation.get_edges()
        assert (c0, c1) in edges
        assert (c1, c2) in edges
        assert len(edges) == 2

    def test_topological_order(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)

        topo_order = condensation.topological_order()
        assert len(topo_order) == 3

        edge_set = set(condensation.get_edges())
        for i, u in enumerate(topo_order):
            for v in topo_order[i + 1:]:
                assert (v, u) not in edge_set

    def test_scc_ids_satisfy_topological_order(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)

        for from_cid, to_cid in condensation.get_edges():
            assert from_cid < to_cid


class TestStronglyConnectedGraph:
    def test_single_scc(self, tarjan_strongly_connected: TarjanSCC) -> None:
        result = tarjan_strongly_connected.find_sccs()
        assert len(result) == 1
        assert set(result.components[0]) == {0, 1, 2, 3}

    def test_condensation_single_node(self, tarjan_strongly_connected: TarjanSCC) -> None:
        result = tarjan_strongly_connected.find_sccs()
        condensation = tarjan_strongly_connected.build_condensation(result)
        assert condensation.num_components == 1
        assert condensation.is_dag() is True
        assert len(condensation.get_edges()) == 0


class TestDiscreteGraph:
    def test_each_node_own_scc(self, tarjan_discrete: TarjanSCC) -> None:
        result = tarjan_discrete.find_sccs()
        assert len(result) == 5
        for component in result.components:
            assert len(component) == 1

    def test_component_ids_unique(self, tarjan_discrete: TarjanSCC) -> None:
        result = tarjan_discrete.find_sccs()
        component_ids = set()
        for node in range(5):
            cid = result.get_component_id(node)
            assert cid not in component_ids
            component_ids.add(cid)

    def test_condensation_no_edges(self, tarjan_discrete: TarjanSCC) -> None:
        result = tarjan_discrete.find_sccs()
        condensation = tarjan_discrete.build_condensation(result)
        assert condensation.num_components == 5
        assert len(condensation.get_edges()) == 0
        assert condensation.is_dag() is True


class TestGraphWithSelfLoops:
    def test_self_loops_handled_correctly(self, tarjan_self_loops: TarjanSCC) -> None:
        result = tarjan_self_loops.find_sccs()
        components = [set(c) for c in result.components]

        assert {0, 1} in components
        assert {2, 3} in components

        assert len(result) == 2

    def test_self_loop_node_in_correct_scc(self, tarjan_self_loops: TarjanSCC) -> None:
        result = tarjan_self_loops.find_sccs()
        c0 = result.get_component_id(0)
        assert result.get_component_id(1) == c0

        c1 = result.get_component_id(2)
        assert result.get_component_id(3) == c1

        assert c0 < c1

    def test_condensation_with_self_loops(self, tarjan_self_loops: TarjanSCC) -> None:
        result = tarjan_self_loops.find_sccs()
        condensation = tarjan_self_loops.build_condensation(result)

        assert condensation.is_dag() is True
        assert len(condensation.get_edges()) == 1

        c0 = result.get_component_id(0)
        c1 = result.get_component_id(2)
        assert condensation.has_edge(c0, c1) is True


class TestGraphWithParallelEdges:
    def test_condensation_no_duplicate_edges(self, tarjan_parallel: TarjanSCC) -> None:
        result = tarjan_parallel.find_sccs()
        condensation = tarjan_parallel.build_condensation(result)

        edges = condensation.get_edges()
        edge_set = set(edges)
        assert len(edges) == len(edge_set)

        c01 = result.get_component_id(0)
        c23 = result.get_component_id(2)
        c45 = result.get_component_id(4)

        assert condensation.has_edge(c01, c23) is True
        assert condensation.has_edge(c23, c45) is True

        assert c01 < c23 < c45
        for from_cid, to_cid in edges:
            assert from_cid < to_cid

    def test_condensation_is_dag(self, tarjan_parallel: TarjanSCC) -> None:
        result = tarjan_parallel.find_sccs()
        condensation = tarjan_parallel.build_condensation(result)
        assert condensation.is_dag() is True


class TestEmptyGraph:
    def test_empty_graph_returns_empty_result(self, tarjan_empty: TarjanSCC) -> None:
        result = tarjan_empty.find_sccs()
        assert len(result) == 0
        assert len(result.components) == 0
        assert len(result.node_to_component) == 0
        assert len(result.component_to_nodes) == 0

    def test_build_condensation_on_empty_graph_raises(self, tarjan_empty: TarjanSCC) -> None:
        with pytest.raises(EmptyGraphError):
            tarjan_empty.build_condensation()


class TestNotFoundErrors:
    def test_query_nonexistent_node_raises(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        with pytest.raises(NodeNotFoundError):
            result.get_component_id(999)

    def test_query_nonexistent_component_raises(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        with pytest.raises(NodeNotFoundError):
            result.get_component_nodes(999)

    def test_graph_nonexistent_node_raises(self, multi_scc_graph: DirectedGraph) -> None:
        with pytest.raises(NodeNotFoundError):
            multi_scc_graph.get_neighbors(999)

    def test_condensation_nonexistent_component_raises(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)
        with pytest.raises(NodeNotFoundError):
            condensation.get_outgoing_edges(999)


class TestDirectedGraph:
    def test_add_node(self, empty_graph: DirectedGraph) -> None:
        empty_graph.add_node(1)
        assert empty_graph.has_node(1)
        assert 1 in empty_graph
        assert empty_graph.num_nodes == 1

    def test_add_edge(self, empty_graph: DirectedGraph) -> None:
        empty_graph.add_edge(0, 1)
        assert empty_graph.has_edge(0, 1)
        assert empty_graph.has_node(0)
        assert empty_graph.has_node(1)
        assert empty_graph.num_edges == 1

    def test_get_neighbors(self, empty_graph: DirectedGraph) -> None:
        empty_graph.add_edges([(0, 1), (0, 2), (0, 3)])
        neighbors = empty_graph.get_neighbors(0)
        assert neighbors == {1, 2, 3}

    def test_graph_iteration(self, multi_scc_graph: DirectedGraph) -> None:
        nodes = list(multi_scc_graph)
        assert nodes == [0, 1, 2, 3, 4, 5, 6, 7, 8]

    def test_get_transpose(self, multi_scc_graph: DirectedGraph) -> None:
        transposed = multi_scc_graph.get_transpose()
        for u, v in multi_scc_graph.edges:
            assert transposed.has_edge(v, u)

    def test_is_empty(self, empty_graph: DirectedGraph, multi_scc_graph: DirectedGraph) -> None:
        assert empty_graph.is_empty() is True
        assert multi_scc_graph.is_empty() is False


class TestCondensationGraph:
    def test_get_incoming_edges(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)

        c0 = result.get_component_id(0)
        c1 = result.get_component_id(3)
        c2 = result.get_component_id(6)

        assert condensation.get_incoming_edges(c0) == set()
        assert condensation.get_incoming_edges(c1) == {c0}
        assert condensation.get_incoming_edges(c2) == {c1}

    def test_get_outgoing_edges(self, tarjan_multi_scc: TarjanSCC) -> None:
        result = tarjan_multi_scc.find_sccs()
        condensation = tarjan_multi_scc.build_condensation(result)

        c0 = result.get_component_id(0)
        c1 = result.get_component_id(3)
        c2 = result.get_component_id(6)

        assert condensation.get_outgoing_edges(c0) == {c1}
        assert condensation.get_outgoing_edges(c1) == {c2}
        assert condensation.get_outgoing_edges(c2) == set()

    def test_topological_order_on_discrete(self, tarjan_discrete: TarjanSCC) -> None:
        result = tarjan_discrete.find_sccs()
        condensation = tarjan_discrete.build_condensation(result)
        topo = condensation.topological_order()
        assert len(topo) == 5
        assert set(topo) == set(range(5))
