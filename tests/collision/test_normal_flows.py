import pytest

from solocoder_py.collision import (
    AABB,
    Collider,
    CollisionEngine,
    CollisionPair,
    SpatialHash,
)

from .conftest import build_engine_with_colliders


class TestAABBIntersection:
    def test_intersecting_boxes_return_true(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=30, min_y=30, max_x=80, max_y=80)
        assert a.intersects(b) is True
        assert b.intersects(a) is True

    def test_non_intersecting_boxes_return_false(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=100, min_y=100, max_x=150, max_y=150)
        assert a.intersects(b) is False
        assert b.intersects(a) is False

    def test_touching_at_edge_is_intersection(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=50, min_y=0, max_x=100, max_y=50)
        assert a.intersects(b) is True
        assert b.intersects(a) is True

    def test_touching_at_corner_is_intersection(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=50, min_y=50, max_x=100, max_y=100)
        assert a.intersects(b) is True
        assert b.intersects(a) is True

    def test_one_inside_another(self):
        a = AABB(min_x=0, min_y=0, max_x=100, max_y=100)
        b = AABB(min_x=20, min_y=20, max_x=80, max_y=80)
        assert a.intersects(b) is True
        assert b.intersects(a) is True
        assert a.contains(b) is True
        assert b.contains(a) is False

    def test_separated_on_x_only(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=60, min_y=0, max_x=110, max_y=50)
        assert a.intersects(b) is False

    def test_separated_on_y_only(self):
        a = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        b = AABB(min_x=0, min_y=60, max_x=50, max_y=110)
        assert a.intersects(b) is False


class TestSpatialHashBasic:
    def test_add_and_get_collider(self):
        sh = SpatialHash(cell_size=100)
        c = Collider(id="a", aabb=AABB(min_x=10, min_y=10, max_x=50, max_y=50))
        sh.add(c)
        assert sh.collider_count == 1
        assert sh.has_collider("a") is True
        retrieved = sh.get_collider("a")
        assert retrieved is c

    def test_remove_collider(self):
        sh = SpatialHash(cell_size=100)
        c = Collider(id="a", aabb=AABB(min_x=10, min_y=10, max_x=50, max_y=50))
        sh.add(c)
        sh.remove("a")
        assert sh.collider_count == 0
        assert sh.has_collider("a") is False

    def test_clear(self):
        sh = SpatialHash(cell_size=100)
        for i in range(10):
            sh.add(Collider(
                id=f"c{i}",
                aabb=AABB(min_x=i * 10, min_y=i * 10, max_x=i * 10 + 5, max_y=i * 10 + 5),
            ))
        assert sh.collider_count == 10
        sh.clear()
        assert sh.collider_count == 0


class TestSpatialHashCandidates:
    def test_candidates_include_overlapping(self):
        sh = SpatialHash(cell_size=100)
        c1 = Collider(id="c1", aabb=AABB(min_x=10, min_y=10, max_x=50, max_y=50))
        c2 = Collider(id="c2", aabb=AABB(min_x=40, min_y=40, max_x=80, max_y=80))
        c3 = Collider(id="c3", aabb=AABB(min_x=200, min_y=200, max_x=250, max_y=250))
        sh.add(c1)
        sh.add(c2)
        sh.add(c3)

        candidates = sh.get_candidates(AABB(min_x=0, min_y=0, max_x=60, max_y=60))
        candidate_ids = {c.id for c in candidates}
        assert "c1" in candidate_ids
        assert "c2" in candidate_ids
        assert "c3" not in candidate_ids

    def test_single_cell_collider(self):
        sh = SpatialHash(cell_size=100)
        c = Collider(id="c", aabb=AABB(min_x=10, min_y=10, max_x=50, max_y=50))
        sh.add(c)
        candidates = sh.get_candidates(AABB(min_x=20, min_y=20, max_x=30, max_y=30))
        assert len(candidates) == 1
        assert candidates[0].id == "c"


class TestCollisionEngineBasic:
    def test_add_collider(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="c1", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        result = engine.add_collider(c)
        assert result is c
        assert engine.collider_count == 1

    def test_remove_collider(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="c1", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)
        engine.remove_collider("c1")
        assert engine.collider_count == 0

    def test_get_collider(self):
        engine, c1, _, _, _, _ = build_engine_with_colliders()
        retrieved = engine.get_collider("c1")
        assert retrieved.id == "c1"
        assert retrieved.aabb.min_x == 10

    def test_get_all_colliders(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        all_colliders = engine.get_all_colliders()
        assert len(all_colliders) == 5
        ids = {c.id for c in all_colliders}
        assert ids == {"c1", "c2", "c3", "c4", "c5"}

    def test_has_collider(self):
        engine, c1, _, _, _, _ = build_engine_with_colliders()
        assert engine.has_collider("c1") is True
        assert engine.has_collider("nonexistent") is False

    def test_clear(self):
        engine, _, _, _, _, _ = build_engine_with_colliders()
        assert engine.collider_count == 5
        engine.clear()
        assert engine.collider_count == 0


class TestCheckCollision:
    def test_single_collider_detects_collisions(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        collided = engine.check_collision("c1")
        ids = {c.id for c in collided}
        assert "c2" in ids
        assert "c3" not in ids
        assert "c4" not in ids
        assert "c5" not in ids

    def test_single_collider_no_self_collision(self):
        engine, c1, _, _, _, _ = build_engine_with_colliders()
        collided = engine.check_collision("c1")
        ids = {c.id for c in collided}
        assert "c1" not in ids

    def test_check_collision_with_aabb(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        test_aabb = AABB(min_x=0, min_y=0, max_x=60, max_y=60)
        collided = engine.check_collision_aabb(test_aabb)
        ids = {c.id for c in collided}
        assert "c1" in ids
        assert "c2" in ids
        assert "c4" in ids
        assert "c3" not in ids
        assert "c5" not in ids


class TestCheckAllCollisions:
    def test_all_collisions_detected(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        pairs = engine.check_all_collisions()
        pair_set = set()
        for pair in pairs:
            pair_set.add((pair.collider_a.id, pair.collider_b.id))

        assert ("c1", "c2") in pair_set
        assert ("c2", "c4") in pair_set
        assert len(pairs) == 2

    def test_no_duplicate_pairs(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        pairs = engine.check_all_collisions()
        pair_ids = [(p.collider_a.id, p.collider_b.id) for p in pairs]
        assert len(pair_ids) == len(set(pair_ids))

    def test_no_self_pairs(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        pairs = engine.check_all_collisions()
        for pair in pairs:
            assert pair.collider_a.id != pair.collider_b.id


class TestCollisionPair:
    def test_pair_ordering(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        p1 = CollisionPair(collider_a=c1, collider_b=c2)
        with pytest.warns(RuntimeWarning):
            p2 = CollisionPair(collider_a=c2, collider_b=c1)

        assert p1 == p2
        assert hash(p1) == hash(p2)
        assert p1.collider_a.id == "a"
        assert p1.collider_b.id == "b"

    def test_pair_in_set(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        s = set()
        s.add(CollisionPair(collider_a=c1, collider_b=c2))
        with pytest.warns(RuntimeWarning):
            s.add(CollisionPair(collider_a=c2, collider_b=c1))
        assert len(s) == 1

    def test_was_swapped_false_when_already_ordered(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        pair = CollisionPair(collider_a=c1, collider_b=c2)
        assert pair.was_swapped is False
        assert pair.collider_a is c1
        assert pair.collider_b is c2

    def test_was_swapped_true_when_reordered(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        with pytest.warns(RuntimeWarning):
            pair = CollisionPair(collider_a=c2, collider_b=c1)
        assert pair.was_swapped is True
        assert pair.collider_a is c1
        assert pair.collider_b is c2

    def test_swap_emits_runtime_warning(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        with pytest.warns(RuntimeWarning, match="reordered by ID") as record:
            CollisionPair(collider_a=c2, collider_b=c1)

        assert len(record) == 1
        assert "from_ordered" in str(record[0].message)
        assert "'b'" in str(record[0].message)
        assert "'a'" in str(record[0].message)

    def test_already_ordered_no_warning(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            pair = CollisionPair(collider_a=c1, collider_b=c2)

        assert pair.was_swapped is False

    def test_from_unordered_same_as_default(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        with pytest.warns(RuntimeWarning):
            p_default = CollisionPair(collider_a=c2, collider_b=c1)
        with pytest.warns(RuntimeWarning):
            p_factory = CollisionPair.from_unordered(c2, c1)

        assert p_default == p_factory
        assert p_default.was_swapped == p_factory.was_swapped
        assert p_default.collider_a.id == p_factory.collider_a.id

    def test_from_unordered_already_sorted_no_warning(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            pair = CollisionPair.from_unordered(c1, c2)

        assert pair.was_swapped is False

    def test_from_unordered_emits_same_warning(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        with pytest.warns(RuntimeWarning, match="reordered by ID"):
            CollisionPair.from_unordered(c2, c1)

    def test_from_ordered_preserves_order(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            pair = CollisionPair.from_ordered(c2, c1)

        assert pair.was_swapped is False
        assert pair.collider_a is c2
        assert pair.collider_b is c1
        assert pair.collider_a.id == "b"
        assert pair.collider_b.id == "a"

    def test_from_ordered_never_emits_warning(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            CollisionPair.from_ordered(c1, c2)
            CollisionPair.from_ordered(c2, c1)

    def test_from_ordered_not_equal_to_normalized(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        with pytest.warns(RuntimeWarning):
            p_normalized = CollisionPair(collider_a=c2, collider_b=c1)
        p_ordered = CollisionPair.from_ordered(c2, c1)

        assert p_normalized != p_ordered
        assert hash(p_normalized) != hash(p_ordered)

    def test_from_ordered_already_sorted_stays_same(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        pair = CollisionPair.from_ordered(c1, c2)
        assert pair.was_swapped is False
        assert pair.collider_a is c1
        assert pair.collider_b is c2

    def test_from_ordered_goes_through_post_init_path(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        pair = CollisionPair.from_ordered(c2, c1)
        assert pair._preserve_order is True
        assert pair.was_swapped is False
        assert pair.collider_a is c2
        assert pair.collider_b is c1

    def test_default_constructor_preserve_order_false(self):
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=0, max_x=10, max_y=10))

        pair = CollisionPair(collider_a=c1, collider_b=c2)
        assert pair._preserve_order is False


class TestGlobalCallbacks:
    def test_global_callback_triggered(self):
        engine, c1, c2, _, _, _ = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_global_callback(callback)
        engine.detect_and_trigger()

        assert len(triggered) == 2

        pair_ids = set()
        for a_id, b_id in triggered:
            pair_ids.add(tuple(sorted([a_id, b_id])))

        assert ("c1", "c2") in pair_ids
        assert ("c2", "c4") in pair_ids

    def test_remove_global_callback(self):
        engine, c1, c2, _, _, _ = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_global_callback(callback)
        engine.remove_global_callback(callback)
        engine.detect_and_trigger()

        assert len(triggered) == 0


class TestPairCallbacks:
    def test_pair_callback_triggered(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_pair_callback("c1", "c2", callback)
        engine.detect_and_trigger()

        assert len(triggered) == 1
        a_id, b_id = triggered[0]
        assert set([a_id, b_id]) == {"c1", "c2"}

    def test_pair_callback_not_triggered_for_other_pairs(self):
        engine, c1, c2, c3, c4, c5 = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_pair_callback("c1", "c3", callback)
        engine.detect_and_trigger()

        assert len(triggered) == 0

    def test_remove_pair_callback(self):
        engine, c1, c2, _, _, _ = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_pair_callback("c1", "c2", callback)
        engine.remove_pair_callback("c1", "c2", callback)
        engine.detect_and_trigger()

        assert len(triggered) == 0

    def test_multiple_pair_callbacks(self):
        engine, c1, c2, _, _, _ = build_engine_with_colliders()
        count1 = 0
        count2 = 0

        def cb1(a, b):
            nonlocal count1
            count1 += 1

        def cb2(a, b):
            nonlocal count2
            count2 += 1

        engine.add_pair_callback("c1", "c2", cb1)
        engine.add_pair_callback("c1", "c2", cb2)
        engine.detect_and_trigger()

        assert count1 == 1
        assert count2 == 1


class TestDetectAndTriggerFor:
    def test_detect_and_trigger_for_specific_collider(self):
        engine, c1, c2, _, _, _ = build_engine_with_colliders()
        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_global_callback(callback)
        collided = engine.detect_and_trigger_for("c1")

        assert len(collided) == 1
        assert collided[0].id == "c2"
        assert len(triggered) == 1
