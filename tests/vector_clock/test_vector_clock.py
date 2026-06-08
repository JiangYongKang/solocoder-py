from __future__ import annotations

import pytest

from solocoder_py.vector_clock import ClockRelation, VectorClock


class TestVectorClockCreation:
    def test_create_empty_clock(self):
        vc = VectorClock()
        assert vc.nodes() == set()
        assert vc.to_dict() == {}

    def test_create_with_initial_values(self):
        vc = VectorClock({"a": 1, "b": 2})
        assert vc.get("a") == 1
        assert vc.get("b") == 2
        assert vc.get("c") == 0

    def test_create_with_negative_count_raises(self):
        with pytest.raises(ValueError, match="clock count must be non-negative"):
            VectorClock({"a": -1})

    def test_create_with_empty_node_id_raises(self):
        with pytest.raises(ValueError, match="node_id must not be empty"):
            VectorClock({"": 3})

    def test_create_normalizes_zero_count_nodes(self):
        vc = VectorClock({"a": 1, "b": 0, "c": 0})
        assert vc.nodes() == {"a"}
        assert vc.to_dict() == {"a": 1}
        assert vc.get("b") == 0
        assert vc.get("c") == 0


class TestLocalEventIncrement:
    def test_tick_increments_existing_node(self):
        vc = VectorClock({"a": 5})
        vc.tick("a")
        assert vc.get("a") == 6

    def test_tick_creates_new_node(self):
        vc = VectorClock()
        vc.tick("b")
        assert vc.get("b") == 1

    def test_tick_multiple_times(self):
        vc = VectorClock()
        for _ in range(10):
            vc.tick("x")
        assert vc.get("x") == 10

    def test_tick_empty_node_id_raises(self):
        vc = VectorClock()
        with pytest.raises(ValueError, match="node_id must not be empty"):
            vc.tick("")


class TestClockQuery:
    def test_get_existing_node(self):
        vc = VectorClock({"a": 3})
        assert vc.get("a") == 3

    def test_get_missing_node_returns_zero(self):
        vc = VectorClock()
        assert vc.get("nonexistent") == 0

    def test_nodes_returns_all_nodes(self):
        vc = VectorClock({"a": 1, "b": 2, "c": 3})
        assert vc.nodes() == {"a", "b", "c"}

    def test_to_dict_returns_copy(self):
        vc = VectorClock({"a": 1})
        d = vc.to_dict()
        d["a"] = 999
        assert vc.get("a") == 1


class TestClockEquality:
    def test_equal_empty_clocks(self):
        assert VectorClock() == VectorClock()

    def test_equal_same_values(self):
        assert VectorClock({"a": 1, "b": 2}) == VectorClock({"a": 1, "b": 2})

    def test_equal_different_node_sets_implied_zeros(self):
        assert VectorClock({"a": 1}) == VectorClock({"a": 1, "b": 0})

    def test_not_equal_different_counts(self):
        assert VectorClock({"a": 1}) != VectorClock({"a": 2})

    def test_not_equal_different_nodes(self):
        assert VectorClock({"a": 1}) != VectorClock({"b": 1})

    def test_equals_not_equal_to_non_vectorclock(self):
        assert (VectorClock() == "not a clock") is False


class TestHappensBefore:
    def test_happens_before_simple(self):
        a = VectorClock({"a": 1, "b": 0})
        b = VectorClock({"a": 2, "b": 1})
        assert a.happens_before(b)

    def test_not_happens_before_strictly_greater(self):
        a = VectorClock({"a": 2})
        b = VectorClock({"a": 1})
        assert not a.happens_before(b)

    def test_not_happens_before_equal(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1})
        assert not a.happens_before(b)

    def test_happens_before_different_node_sets(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1, "b": 1})
        assert a.happens_before(b)

    def test_happens_before_empty(self):
        a = VectorClock()
        b = VectorClock({"a": 1})
        assert a.happens_before(b)

    def test_happens_before_requires_vectorclock(self):
        vc = VectorClock()
        with pytest.raises(TypeError):
            vc.happens_before("not a clock")


class TestHappensAfter:
    def test_happens_after_simple(self):
        a = VectorClock({"a": 2, "b": 1})
        b = VectorClock({"a": 1, "b": 0})
        assert a.happens_after(b)

    def test_not_happens_after(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 2})
        assert not a.happens_after(b)

    def test_not_happens_after_equal(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1})
        assert not a.happens_after(b)

    def test_happens_after_empty(self):
        a = VectorClock({"a": 1})
        b = VectorClock()
        assert a.happens_after(b)


class TestConcurrency:
    def test_concurrent_classic_case(self):
        a = VectorClock({"a": 2, "b": 1})
        b = VectorClock({"a": 1, "b": 2})
        assert a.is_concurrent_with(b)
        assert b.is_concurrent_with(a)

    def test_concurrent_with_some_nodes_same(self):
        a = VectorClock({"a": 3, "b": 1, "c": 2})
        b = VectorClock({"a": 3, "b": 2, "c": 1})
        assert a.is_concurrent_with(b)

    def test_not_concurrent_if_before(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 2})
        assert not a.is_concurrent_with(b)

    def test_not_concurrent_if_equal(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1})
        assert not a.is_concurrent_with(b)

    def test_concurrent_disjoint_nodes(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"b": 1})
        assert a.is_concurrent_with(b)

    def test_is_concurrent_with_requires_vectorclock(self):
        vc = VectorClock()
        with pytest.raises(TypeError):
            vc.is_concurrent_with("not a clock")


class TestCompare:
    def test_compare_equal(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1})
        assert a.compare(b) == ClockRelation.EQUAL

    def test_compare_before(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 2})
        assert a.compare(b) == ClockRelation.BEFORE

    def test_compare_after(self):
        a = VectorClock({"a": 2})
        b = VectorClock({"a": 1})
        assert a.compare(b) == ClockRelation.AFTER

    def test_compare_concurrent(self):
        a = VectorClock({"a": 2, "b": 1})
        b = VectorClock({"a": 1, "b": 2})
        assert a.compare(b) == ClockRelation.CONCURRENT


class TestClockMerge:
    def test_merge_disjoint_nodes(self):
        a = VectorClock({"a": 3})
        b = VectorClock({"b": 5})
        merged = a.merge(b)
        assert merged.get("a") == 3
        assert merged.get("b") == 5

    def test_merge_overlapping_nodes_takes_max(self):
        a = VectorClock({"a": 1, "b": 5})
        b = VectorClock({"a": 3, "b": 2})
        merged = a.merge(b)
        assert merged.get("a") == 3
        assert merged.get("b") == 5

    def test_merge_returns_new_instance(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"b": 1})
        merged = a.merge(b)
        assert a.get("b") == 0
        assert b.get("a") == 0
        assert merged.get("a") == 1
        assert merged.get("b") == 1

    def test_merge_with_empty(self):
        a = VectorClock({"a": 5})
        b = VectorClock()
        merged = a.merge(b)
        assert merged.get("a") == 5
        assert merged.nodes() == {"a"}

    def test_merge_empty_with_empty(self):
        a = VectorClock()
        b = VectorClock()
        merged = a.merge(b)
        assert merged.nodes() == set()

    def test_merge_requires_vectorclock(self):
        vc = VectorClock()
        with pytest.raises(TypeError):
            vc.merge("not a clock")

    def test_merge_idempotent(self):
        a = VectorClock({"a": 1, "b": 2})
        merged = a.merge(a)
        assert merged == a


class TestCopy:
    def test_copy_is_independent(self):
        a = VectorClock({"a": 1})
        b = a.copy()
        b.tick("a")
        assert a.get("a") == 1
        assert b.get("a") == 2


class TestEmptyClockEdgeCases:
    def test_two_empty_clocks_equal(self):
        assert VectorClock() == VectorClock()

    def test_empty_not_happens_before_empty(self):
        assert not VectorClock().happens_before(VectorClock())

    def test_empty_not_concurrent_with_empty(self):
        assert not VectorClock().is_concurrent_with(VectorClock())

    def test_empty_compared_to_empty_is_equal(self):
        assert VectorClock().compare(VectorClock()) == ClockRelation.EQUAL

    def test_empty_happens_before_any_nonempty(self):
        empty = VectorClock()
        nonempty = VectorClock({"a": 1})
        assert empty.happens_before(nonempty)

    def test_any_nonempty_happens_after_empty(self):
        empty = VectorClock()
        nonempty = VectorClock({"a": 1})
        assert nonempty.happens_after(empty)


class TestDifferentNodeSets:
    def test_partial_overlap_before(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 2, "b": 1})
        assert a.happens_before(b)
        assert b.happens_after(a)

    def test_partial_overlap_concurrent(self):
        a = VectorClock({"a": 2, "b": 1})
        b = VectorClock({"b": 2, "c": 1})
        assert a.is_concurrent_with(b)

    def test_one_has_extra_node_concurrent(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"b": 1})
        assert a.is_concurrent_with(b)
        assert not a.happens_before(b)
        assert not b.happens_before(a)

    def test_superset_before(self):
        a = VectorClock({"a": 1, "b": 1})
        b = VectorClock({"a": 1, "b": 2, "c": 1})
        assert a.happens_before(b)


class TestSameCountEdgeCases:
    def test_all_same_counts_not_before(self):
        a = VectorClock({"a": 5, "b": 5})
        b = VectorClock({"a": 5, "b": 5})
        assert not a.happens_before(b)
        assert not b.happens_before(a)
        assert a == b

    def test_part_same_part_higher(self):
        a = VectorClock({"a": 3, "b": 2})
        b = VectorClock({"a": 3, "b": 3})
        assert a.happens_before(b)

    def test_part_same_part_lower(self):
        a = VectorClock({"a": 3, "b": 3})
        b = VectorClock({"a": 3, "b": 2})
        assert a.happens_after(b)

    def test_same_counts_one_extra_node(self):
        a = VectorClock({"a": 2})
        b = VectorClock({"a": 2, "b": 0})
        assert a == b


class TestHashability:
    def test_hash_equal_clocks_same_hash(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1})
        assert hash(a) == hash(b)

    def test_hash_implied_zero_equal_clocks_same_hash(self):
        a = VectorClock({"a": 1})
        b = VectorClock({"a": 1, "b": 0, "c": 0})
        assert a == b
        assert hash(a) == hash(b)

    def test_implied_zero_equal_clocks_in_set_deduplicated(self):
        s = {VectorClock({"a": 1}), VectorClock({"a": 1, "b": 0})}
        assert len(s) == 1
        assert VectorClock({"a": 1, "c": 0}) in s

    def test_implied_zero_equal_clocks_as_dict_key(self):
        d = {VectorClock({"a": 1}): "value"}
        assert d[VectorClock({"a": 1, "b": 0})] == "value"

    def test_can_use_in_set(self):
        s = {VectorClock({"a": 1}), VectorClock({"a": 2})}
        assert len(s) == 2
        assert VectorClock({"a": 1}) in s

    def test_can_use_as_dict_key(self):
        d = {VectorClock({"a": 1}): "value"}
        assert d[VectorClock({"a": 1})] == "value"


class TestRealWorldScenario:
    def test_three_node_causal_chain(self):
        a = VectorClock()
        a.tick("A")
        a.tick("A")

        b = a.copy()
        b.tick("B")

        c = b.copy()
        c.tick("C")

        assert a.happens_before(b)
        assert b.happens_before(c)
        assert a.happens_before(c)

    def test_concurrent_updates_merged(self):
        base = VectorClock({"A": 1})

        branch_a = base.copy()
        branch_a.tick("A")
        branch_a.tick("A")

        branch_b = base.copy()
        branch_b.tick("B")

        assert branch_a.is_concurrent_with(branch_b)

        merged = branch_a.merge(branch_b)
        assert merged.get("A") == 3
        assert merged.get("B") == 1
        assert branch_a.happens_before(merged)
        assert branch_b.happens_before(merged)
