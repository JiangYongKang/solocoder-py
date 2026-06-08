from __future__ import annotations

import pytest

from solocoder_py.crdt import PNCounter, PNCounterState


class TestPNCounterBasicOperations:
    def test_initial_value_is_zero(self):
        counter = PNCounter(replica_id="node1")
        assert counter.value() == 0

    def test_increment_single(self):
        counter = PNCounter(replica_id="node1")
        counter.increment()
        assert counter.value() == 1

    def test_increment_multiple(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(5)
        assert counter.value() == 5
        counter.increment(3)
        assert counter.value() == 8

    def test_decrement_single(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(3)
        counter.decrement()
        assert counter.value() == 2

    def test_decrement_multiple(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(10)
        counter.decrement(4)
        assert counter.value() == 6

    def test_increment_zero_is_noop(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(0)
        assert counter.value() == 0
        state = counter.get_state()
        assert counter.replica_id not in state.positive

    def test_decrement_zero_is_noop(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(5)
        counter.decrement(0)
        assert counter.value() == 5
        state = counter.get_state()
        assert counter.replica_id not in state.negative


class TestPNCounterNonNegative:
    def test_value_never_negative(self):
        counter = PNCounter(replica_id="node1")
        counter.decrement(10)
        assert counter.value() == 0

    def test_decrement_past_zero_clamps(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(3)
        counter.decrement(10)
        assert counter.value() == 0


class TestPNCounterInvalidInput:
    def test_increment_negative_raises(self):
        counter = PNCounter(replica_id="node1")
        with pytest.raises(ValueError, match="delta must be non-negative"):
            counter.increment(-1)

    def test_decrement_negative_raises(self):
        counter = PNCounter(replica_id="node1")
        with pytest.raises(ValueError, match="delta must be non-negative"):
            counter.decrement(-1)


class TestPNCounterReplicaId:
    def test_default_replica_id_generated(self):
        counter1 = PNCounter()
        counter2 = PNCounter()
        assert counter1.replica_id is not None
        assert counter2.replica_id is not None
        assert counter1.replica_id != counter2.replica_id

    def test_explicit_replica_id(self):
        counter = PNCounter(replica_id="my-node")
        assert counter.replica_id == "my-node"


class TestPNCounterState:
    def test_get_state_returns_copy(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(3)
        counter.decrement(1)
        state = counter.get_state()
        assert isinstance(state, PNCounterState)
        assert state.positive["node1"] == 3
        assert state.negative["node1"] == 1
        state.positive["node1"] = 999
        state.negative["node1"] = 999
        assert counter.value() == 2

    def test_state_value(self):
        state = PNCounterState(
            positive={"a": 5, "b": 3},
            negative={"a": 2, "c": 1},
        )
        assert state.value() == 5

    def test_from_state_restores_counter(self):
        original = PNCounter(replica_id="node1")
        original.increment(10)
        original.decrement(3)
        state = original.get_state()
        restored = PNCounter.from_state(state, replica_id="restored")
        assert restored.value() == 7
        assert restored.replica_id == "restored"
        restored_state = restored.get_state()
        assert restored_state.positive == state.positive
        assert restored_state.negative == state.negative

    def test_from_state_is_independent_copy(self):
        original = PNCounter(replica_id="node1")
        original.increment(5)
        state = original.get_state()
        restored = PNCounter.from_state(state, replica_id="node1")
        original.increment(3)
        assert original.value() == 8
        assert restored.value() == 5


class TestPNCounterMerge:
    def test_merge_two_counters(self):
        c1 = PNCounter(replica_id="node1")
        c2 = PNCounter(replica_id="node2")
        c1.increment(5)
        c2.increment(3)
        c1.merge(c2)
        assert c1.value() == 8

    def test_merge_commutative(self):
        c1 = PNCounter(replica_id="node1")
        c2 = PNCounter(replica_id="node2")
        c1.increment(5)
        c2.increment(3)
        c1.decrement(1)
        c2.decrement(2)

        c1_snapshot = c1.get_state()
        c2_snapshot = c2.get_state()

        c1.merge(c2)

        c2_from_snapshot = PNCounter.from_state(c2_snapshot, replica_id="node2")
        c1_from_snapshot = PNCounter.from_state(c1_snapshot, replica_id="node1")
        c2_from_snapshot.merge(c1_from_snapshot)

        assert c1.value() == c2_from_snapshot.value()
        assert c1.value() == 5

    def test_merge_associative(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="b")
        c3 = PNCounter(replica_id="c")
        c1.increment(2)
        c2.increment(3)
        c3.increment(4)

        c1_state = c1.get_state()
        c2_state = c2.get_state()
        c3_state = c3.get_state()

        c1_copy = PNCounter.from_state(c1_state, replica_id="a")
        c2_copy = PNCounter.from_state(c2_state, replica_id="b")
        c3_copy = PNCounter.from_state(c3_state, replica_id="c")

        temp1 = PNCounter(replica_id="temp1")
        t1_c1 = PNCounter.from_state(c1_state)
        t1_c2 = PNCounter.from_state(c2_state)
        t1_c3 = PNCounter.from_state(c3_state)
        temp1.merge(t1_c1)
        temp1.merge(t1_c2)
        temp1.merge(t1_c3)

        temp2 = PNCounter(replica_id="temp2")
        t2_c2 = PNCounter.from_state(c2_state)
        t2_c3 = PNCounter.from_state(c3_state)
        t2_c1 = PNCounter.from_state(c1_state)
        temp2.merge(t2_c2)
        temp2.merge(t2_c3)
        temp2.merge(t2_c1)

        assert temp1.value() == temp2.value() == 9

    def test_merge_idempotent(self):
        c1 = PNCounter(replica_id="node1")
        c1.increment(5)
        c1.decrement(2)
        state_before = c1.get_state()
        c1.merge(c1)
        state_after = c1.get_state()
        assert state_before.positive == state_after.positive
        assert state_before.negative == state_after.negative
        assert c1.value() == 3

    def test_merge_same_replica_takes_max(self):
        c1 = PNCounter(replica_id="node1")
        c2 = PNCounter(replica_id="node1")
        c1.increment(10)
        c2.increment(5)
        c1.decrement(2)
        c2.decrement(4)
        c1.merge(c2)
        assert c1.value() == 6

    def test_merge_with_decrements(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="b")
        c1.increment(10)
        c2.increment(10)
        c1.decrement(3)
        c2.decrement(2)
        c1.merge(c2)
        assert c1.value() == 15

    def test_merge_wrong_type_raises(self):
        c1 = PNCounter(replica_id="a")
        with pytest.raises(TypeError, match="can only merge with another PNCounter"):
            c1.merge("not a counter")


class TestPNCounterMonotonicity:
    def test_increment_is_monotonic(self):
        counter = PNCounter(replica_id="node1")
        for i in range(1, 11):
            counter.increment()
            state = counter.get_state()
            assert state.positive["node1"] == i

    def test_decrement_is_monotonic(self):
        counter = PNCounter(replica_id="node1")
        counter.increment(100)
        for i in range(1, 11):
            counter.decrement()
            state = counter.get_state()
            assert state.negative["node1"] == i

    def test_merge_preserves_monotonicity(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="b")
        c1.increment(5)
        c2.increment(3)
        c1.merge(c2)
        state1 = c1.get_state()
        c2.increment(2)
        c1.merge(c2)
        state2 = c1.get_state()
        for rid in state2.positive:
            assert state2.positive[rid] >= state1.positive.get(rid, 0)
        for rid in state2.negative:
            assert state2.negative[rid] >= state1.negative.get(rid, 0)


class TestPNCounterDiff:
    def test_diff_identical_counters(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="a")
        c1.increment(5)
        c2.increment(5)
        diff = c1.diff(c2)
        assert not diff.added_positive
        assert not diff.added_negative
        assert not diff.increased_positive
        assert not diff.increased_negative

    def test_diff_added_replica(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="a")
        c1.increment(8)
        diff = c1.diff(c2)
        assert "a" in diff.added_positive
        assert diff.added_positive["a"] == 8

    def test_diff_increased(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="a")
        c1.increment(5)
        c1_state = c1.get_state()
        c2 = PNCounter.from_state(c1_state, replica_id="a")
        c1.increment(3)
        diff = c1.diff(c2)
        assert "a" in diff.increased_positive
        assert diff.increased_positive["a"] == (5, 8)

    def test_diff_wrong_type_raises(self):
        c1 = PNCounter(replica_id="a")
        with pytest.raises(TypeError, match="can only compute diff with another PNCounter"):
            c1.diff("not a counter")


class TestPNCounterIsGE:
    def test_is_ge_self(self):
        c1 = PNCounter(replica_id="a")
        c1.increment(5)
        c1.decrement(2)
        assert c1.is_ge(c1)

    def test_is_ge_after_merge(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="b")
        c1.increment(5)
        c2.increment(3)
        c1.merge(c2)
        assert c1.is_ge(c2)
        assert not c2.is_ge(c1)

    def test_is_ge_incomparable(self):
        c1 = PNCounter(replica_id="a")
        c2 = PNCounter(replica_id="b")
        c1.increment(5)
        c2.increment(3)
        assert not c1.is_ge(c2)
        assert not c2.is_ge(c1)

    def test_is_ge_wrong_type_raises(self):
        c1 = PNCounter(replica_id="a")
        with pytest.raises(TypeError, match="can only compare with another PNCounter"):
            c1.is_ge("not a counter")


class TestPNCounterMultipleReplicasConvergence:
    def test_three_replicas_converge(self):
        c1 = PNCounter(replica_id="r1")
        c2 = PNCounter(replica_id="r2")
        c3 = PNCounter(replica_id="r3")

        c1.increment(10)
        c2.increment(20)
        c3.increment(30)
        c1.decrement(2)
        c2.decrement(5)
        c3.decrement(1)

        c1.merge(c2)
        c1.merge(c3)
        c2.merge(c3)
        c2.merge(c1)
        c3.merge(c1)

        assert c1.value() == c2.value() == c3.value()
        assert c1.value() == 52

    def test_eventual_consistency_after_random_merges(self):
        replicas = [PNCounter(replica_id=f"r{i}") for i in range(5)]
        for i, r in enumerate(replicas):
            r.increment((i + 1) * 10)
            r.decrement(i)

        for _ in range(20):
            import random
            a, b = random.sample(range(5), 2)
            replicas[a].merge(replicas[b])
            replicas[b].merge(replicas[a])

        final_value = replicas[0].value()
        for r in replicas:
            assert r.value() == final_value
