from __future__ import annotations

import copy

import pytest

from solocoder_py.crdt import ORSet, ORSetState


class TestORSetBasicOperations:
    def test_initial_empty(self):
        s = ORSet(replica_id="node1")
        assert s.value() == set()
        assert len(s) == 0

    def test_add_single_element(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        assert s.contains("a")
        assert "a" in s
        assert s.value() == {"a"}
        assert len(s) == 1

    def test_add_multiple_elements(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.add("b")
        s.add("c")
        assert s.value() == {"a", "b", "c"}
        assert len(s) == 3

    def test_add_all(self):
        s = ORSet(replica_id="node1")
        s.add_all(["x", "y", "z"])
        assert s.value() == {"x", "y", "z"}

    def test_add_duplicate_element(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.add("a")
        assert s.value() == {"a"}
        assert len(s) == 1

    def test_remove_element(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.add("b")
        s.remove("a")
        assert not s.contains("a")
        assert s.contains("b")
        assert s.value() == {"b"}

    def test_remove_nonexistent_element(self):
        s = ORSet(replica_id="node1")
        s.remove("ghost")
        assert s.value() == set()

    def test_clear(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.add("b")
        s.clear()
        assert s.value() == set()
        assert len(s) == 0

    def test_re_add_after_remove(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.remove("a")
        s.add("a")
        assert s.contains("a")
        assert s.value() == {"a"}


class TestORSetReplicaId:
    def test_default_replica_id_generated(self):
        s1 = ORSet()
        s2 = ORSet()
        assert s1.replica_id is not None
        assert s2.replica_id is not None
        assert s1.replica_id != s2.replica_id

    def test_explicit_replica_id(self):
        s = ORSet(replica_id="my-node")
        assert s.replica_id == "my-node"


class TestORSetState:
    def test_get_state_returns_copy(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        state = s.get_state()
        assert isinstance(state, ORSetState)
        assert "a" in state.elements
        assert len(state.elements["a"].tags) == 1
        state.elements["a"].tags = set()
        assert s.contains("a")

    def test_state_value(self):
        from solocoder_py.crdt import ORSetElement
        state = ORSetState(
            elements={
                "a": ORSetElement(tags={"tag1", "tag2"}),
                "b": ORSetElement(tags=set()),
            }
        )
        assert state.value() == {"a"}


class TestORSetMerge:
    def test_merge_two_sets(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("a")
        s2.add("b")
        s1.merge(s2)
        assert s1.value() == {"a", "b"}

    def test_merge_commutative(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("a")
        s2.add("b")

        s1a = ORSet(replica_id="s1a")
        s1a.merge(s1)
        s2a = ORSet(replica_id="s2a")
        s2a.merge(s2)

        s1.merge(s2)

        s1b = ORSet(replica_id="s1b")
        s1b.merge(s1a)
        s2b = ORSet(replica_id="s2b")
        s2b.merge(s2a)
        s2b.merge(s1b)

        assert s1.value() == s2b.value()

    def test_merge_associative(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="b")
        s3 = ORSet(replica_id="c")
        s1.add("x")
        s2.add("y")
        s3.add("z")

        s1_state = ORSet(replica_id="s1_copy")
        s1_state.merge(s1)
        s2_state = ORSet(replica_id="s2_copy")
        s2_state.merge(s2)
        s3_state = ORSet(replica_id="s3_copy")
        s3_state.merge(s3)

        temp1 = ORSet(replica_id="temp1")
        t1_s1 = ORSet(replica_id="t1_s1")
        t1_s1.merge(s1_state)
        t1_s2 = ORSet(replica_id="t1_s2")
        t1_s2.merge(s2_state)
        temp1.merge(t1_s1)
        temp1.merge(t1_s2)
        t1_s3 = ORSet(replica_id="t1_s3")
        t1_s3.merge(s3_state)
        temp1.merge(t1_s3)

        temp2 = ORSet(replica_id="temp2")
        t2_s2 = ORSet(replica_id="t2_s2")
        t2_s2.merge(s2_state)
        t2_s3 = ORSet(replica_id="t2_s3")
        t2_s3.merge(s3_state)
        temp2.merge(t2_s2)
        temp2.merge(t2_s3)
        t2_s1 = ORSet(replica_id="t2_s1")
        t2_s1.merge(s1_state)
        temp2.merge(t2_s1)

        assert temp1.value() == temp2.value()

    def test_merge_idempotent(self):
        s = ORSet(replica_id="node1")
        s.add("a")
        s.add("b")
        state_before = s.get_state()
        s.merge(s)
        state_after = s.get_state()
        for elem in state_after.elements:
            assert state_after.elements[elem].tags == state_before.elements[elem].tags
        assert s.value() == {"a", "b"}

    def test_merge_preserves_removed_element(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("a")
        s1.add("b")
        s1.remove("a")
        s1.merge(s2)
        assert s1.value() == {"b"}

    def test_merge_with_removed_in_other(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("a")
        s2.merge(s1)
        s2.remove("a")
        s1.add("a")
        s1.merge(s2)
        assert "a" in s1.value()

    def test_merge_wrong_type_raises(self):
        s = ORSet(replica_id="a")
        with pytest.raises(TypeError, match="can only merge with another ORSet"):
            s.merge("not a set")


class TestORSetAddWinsSemantics:
    def test_concurrent_add_remove_add_wins(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("x")
        s2.merge(s1)
        s2.remove("x")
        s1.add("x")
        s1.merge(s2)
        s2.merge(s1)
        assert "x" in s1.value()
        assert "x" in s2.value()

    def test_concurrent_add_same_element(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("shared")
        s2.add("shared")
        s1.merge(s2)
        s2.merge(s1)
        assert s1.value() == {"shared"}
        assert s2.value() == {"shared"}

    def test_concurrent_add_and_remove(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s1.add("item")
        s2.merge(s1)
        s2.remove("item")
        s1.add("item")
        s1.merge(s2)
        assert "item" in s1.value()

    def test_remove_does_not_affect_concurrent_adds(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="b")
        s3 = ORSet(replica_id="c")
        s1.add("elem")
        s2.merge(s1)
        s2.remove("elem")
        s3.add("elem")
        s3.merge(s2)
        s1.merge(s3)
        assert "elem" in s1.value()


class TestORSetNoDuplicates:
    def test_multiple_adds_same_element_no_duplicates(self):
        s = ORSet(replica_id="node1")
        for _ in range(10):
            s.add("a")
        assert len(s.value()) == 1
        assert s.value() == {"a"}

    def test_merge_adds_same_element_no_duplicates(self):
        s1 = ORSet(replica_id="node1")
        s2 = ORSet(replica_id="node2")
        s3 = ORSet(replica_id="node3")
        s1.add("x")
        s2.add("x")
        s3.add("x")
        s1.merge(s2)
        s1.merge(s3)
        assert len(s1.value()) == 1
        assert s1.value() == {"x"}


class TestORSetDiff:
    def test_diff_identical_sets(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="a")
        s1.add("x")
        s2.merge(s1)
        diff = s1.diff(s2)
        assert not diff.added
        assert not diff.removed
        assert not diff.updated

    def test_diff_added_element(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="a")
        s1.add("new")
        diff = s1.diff(s2)
        assert "new" in diff.added

    def test_diff_removed_element(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="a")
        s2.add("gone")
        diff = s1.diff(s2)
        assert "gone" in diff.removed

    def test_diff_updated_element(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="a")
        s1.add("item")
        s2.merge(s1)
        s1.add("item")
        diff = s1.diff(s2)
        assert "item" in diff.updated

    def test_diff_wrong_type_raises(self):
        s = ORSet(replica_id="a")
        with pytest.raises(TypeError, match="can only compute diff with another ORSet"):
            s.diff("not a set")


class TestORSetIsGE:
    def test_is_ge_self(self):
        s = ORSet(replica_id="a")
        s.add("x")
        s.add("y")
        assert s.is_ge(s)

    def test_is_ge_after_merge(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="b")
        s1.add("x")
        s2.add("y")
        s1.merge(s2)
        assert s1.is_ge(s2)
        assert not s2.is_ge(s1)

    def test_is_ge_incomparable(self):
        s1 = ORSet(replica_id="a")
        s2 = ORSet(replica_id="b")
        s1.add("x")
        s2.add("y")
        assert not s1.is_ge(s2)
        assert not s2.is_ge(s1)

    def test_is_ge_wrong_type_raises(self):
        s = ORSet(replica_id="a")
        with pytest.raises(TypeError, match="can only compare with another ORSet"):
            s.is_ge("not a set")


class TestORSetMultipleReplicasConvergence:
    def test_three_replicas_converge(self):
        s1 = ORSet(replica_id="r1")
        s2 = ORSet(replica_id="r2")
        s3 = ORSet(replica_id="r3")

        s1.add("a")
        s2.add("b")
        s3.add("c")

        s1.merge(s2)
        s1.merge(s3)
        s2.merge(s3)
        s2.merge(s1)
        s3.merge(s1)

        assert s1.value() == s2.value() == s3.value()
        assert s1.value() == {"a", "b", "c"}

    def test_replicas_converge_with_removes(self):
        s1 = ORSet(replica_id="r1")
        s2 = ORSet(replica_id="r2")
        s3 = ORSet(replica_id="r3")

        s1.add("keep")
        s1.add("remove")
        s1.add("also_keep")

        s2.merge(s1)
        s3.merge(s1)

        s2.remove("remove")

        s1.merge(s2)
        s3.merge(s2)
        s1.merge(s3)
        s2.merge(s1)
        s3.merge(s1)

        expected = {"keep", "also_keep"}
        assert s1.value() == expected
        assert s2.value() == expected
        assert s3.value() == expected

    def test_eventual_consistency_random_merges(self):
        replicas = [ORSet(replica_id=f"r{i}") for i in range(4)]
        for i, r in enumerate(replicas):
            r.add(f"elem-{i}")

        for _ in range(50):
            import random
            a, b = random.sample(range(4), 2)
            replicas[a].merge(replicas[b])
            replicas[b].merge(replicas[a])

        for i in range(4):
            for j in range(4):
                replicas[i].merge(replicas[j])

        final_value = replicas[0].value()
        for r in replicas:
            assert r.value() == final_value
        assert len(final_value) == 4


class TestORSetVariousElementTypes:
    def test_integer_elements(self):
        s = ORSet(replica_id="node1")
        s.add(1)
        s.add(2)
        s.add(3)
        assert s.value() == {1, 2, 3}

    def test_tuple_elements(self):
        s = ORSet(replica_id="node1")
        s.add(("a", 1))
        s.add(("b", 2))
        assert ("a", 1) in s
        assert s.value() == {("a", 1), ("b", 2)}

    def test_mixed_types(self):
        s = ORSet(replica_id="node1")
        s.add("string")
        s.add(42)
        s.add((1, 2, 3))
        assert len(s) == 3
