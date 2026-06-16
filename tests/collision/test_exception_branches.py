import pytest

from solocoder_py.collision import (
    AABB,
    Collider,
    CollisionEngine,
    CollisionError,
    ColliderNotFoundError,
    InvalidAABBError,
    InvalidColliderError,
    InvalidGridSizeError,
    SpatialHash,
)


class TestAABBValidation:
    def test_inverted_x_raises(self):
        with pytest.raises(InvalidAABBError):
            AABB(min_x=100, min_y=0, max_x=50, max_y=50)

    def test_inverted_y_raises(self):
        with pytest.raises(InvalidAABBError):
            AABB(min_x=0, min_y=100, max_x=50, max_y=50)

    def test_both_inverted_raises(self):
        with pytest.raises(InvalidAABBError):
            AABB(min_x=100, min_y=100, max_x=50, max_y=50)

    def test_equal_x_is_valid(self):
        a = AABB(min_x=50, min_y=0, max_x=50, max_y=50)
        assert a.width == 0

    def test_equal_y_is_valid(self):
        a = AABB(min_x=0, min_y=50, max_x=50, max_y=50)
        assert a.height == 0


class TestColliderValidation:
    def test_empty_id_raises(self):
        with pytest.raises(InvalidColliderError):
            Collider(id="", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))

    def test_collider_inherits_aabb_error(self):
        with pytest.raises(InvalidAABBError):
            Collider(id="a", aabb=AABB(min_x=100, min_y=0, max_x=50, max_y=50))


class TestSpatialHashGridSizeValidation:
    def test_zero_cell_size_raises(self):
        with pytest.raises(InvalidGridSizeError):
            SpatialHash(cell_size=0)

    def test_negative_cell_size_raises(self):
        with pytest.raises(InvalidGridSizeError):
            SpatialHash(cell_size=-10)

    def test_positive_cell_size_ok(self):
        sh = SpatialHash(cell_size=1.0)
        assert sh.cell_size == 1.0


class TestEngineGridSizeValidation:
    def test_engine_zero_cell_size_raises(self):
        with pytest.raises(InvalidGridSizeError):
            CollisionEngine(cell_size=0)

    def test_engine_negative_cell_size_raises(self):
        with pytest.raises(InvalidGridSizeError):
            CollisionEngine(cell_size=-50)

    def test_resize_grid_zero_raises(self):
        engine = CollisionEngine(cell_size=100)
        with pytest.raises(InvalidGridSizeError):
            engine.resize_grid(0)

    def test_resize_grid_negative_raises(self):
        engine = CollisionEngine(cell_size=100)
        with pytest.raises(InvalidGridSizeError):
            engine.resize_grid(-10)


class TestColliderNotFound:
    def test_get_nonexistent_collider_raises(self):
        engine = CollisionEngine(cell_size=100)
        with pytest.raises(ColliderNotFoundError):
            engine.get_collider("no-such-id")

    def test_spatial_hash_get_nonexistent_raises(self):
        sh = SpatialHash(cell_size=100)
        with pytest.raises(ColliderNotFoundError):
            sh.get_collider("no-such-id")

    def test_check_collision_nonexistent_raises(self):
        engine = CollisionEngine(cell_size=100)
        with pytest.raises(ColliderNotFoundError):
            engine.check_collision("no-such-id")

    def test_remove_nonexistent_is_noop(self):
        engine = CollisionEngine(cell_size=100)
        engine.remove_collider("no-such-id")
        assert engine.collider_count == 0

    def test_spatial_hash_remove_nonexistent_is_noop(self):
        sh = SpatialHash(cell_size=100)
        sh.remove("no-such-id")
        assert sh.collider_count == 0


class TestSelfCollision:
    def test_self_not_in_check_collision(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="self", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)
        collided = engine.check_collision("self")
        assert len(collided) == 0

    def test_self_not_in_all_collisions(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="self", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)
        pairs = engine.check_all_collisions()
        assert len(pairs) == 0

    def test_self_does_not_trigger_callback(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="self", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)

        triggered = []

        def callback(a, b):
            triggered.append((a.id, b.id))

        engine.add_global_callback(callback)
        engine.detect_and_trigger()

        assert len(triggered) == 0


class TestZeroSizeColliders:
    def test_zero_size_collider_detected(self):
        engine = CollisionEngine(cell_size=100)
        point = Collider(
            id="point",
            aabb=AABB(min_x=25, min_y=25, max_x=25, max_y=25),
        )
        box = Collider(
            id="box",
            aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50),
        )
        engine.add_collider(point)
        engine.add_collider(box)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 1

    def test_zero_size_colliders_touching(self):
        engine = CollisionEngine(cell_size=100)
        p1 = Collider(id="p1", aabb=AABB(min_x=50, min_y=50, max_x=50, max_y=50))
        p2 = Collider(id="p2", aabb=AABB(min_x=50, min_y=50, max_x=50, max_y=50))
        engine.add_collider(p1)
        engine.add_collider(p2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 1

    def test_zero_size_colliders_separated(self):
        engine = CollisionEngine(cell_size=100)
        p1 = Collider(id="p1", aabb=AABB(min_x=10, min_y=10, max_x=10, max_y=10))
        p2 = Collider(id="p2", aabb=AABB(min_x=50, min_y=50, max_x=50, max_y=50))
        engine.add_collider(p1)
        engine.add_collider(p2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 0


class TestExceptionHierarchy:
    def test_invalid_aabb_inherits_from_collision_error(self):
        assert issubclass(InvalidAABBError, CollisionError)

    def test_invalid_collider_inherits_from_collision_error(self):
        assert issubclass(InvalidColliderError, CollisionError)

    def test_invalid_grid_size_inherits_from_collision_error(self):
        assert issubclass(InvalidGridSizeError, CollisionError)

    def test_collider_not_found_inherits_from_collision_error(self):
        assert issubclass(ColliderNotFoundError, CollisionError)


class TestSpatialHashEmptyCells:
    def test_empty_query_returns_empty(self):
        sh = SpatialHash(cell_size=100)
        c = Collider(id="a", aabb=AABB(min_x=1000, min_y=1000, max_x=1050, max_y=1050))
        sh.add(c)

        candidates = sh.get_candidates(AABB(min_x=0, min_y=0, max_x=10, max_y=10))
        assert len(candidates) == 0

    def test_query_far_away_returns_empty(self):
        sh = SpatialHash(cell_size=50)
        c = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=30, max_y=30))
        sh.add(c)

        candidates = sh.get_candidates(AABB(min_x=1000, min_y=1000, max_x=1050, max_y=1050))
        assert len(candidates) == 0


class TestCallbackEdgeCases:
    def test_add_same_callback_twice(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=30, min_y=30, max_x=80, max_y=80))
        engine.add_collider(c1)
        engine.add_collider(c2)

        count = 0

        def callback(a, b):
            nonlocal count
            count += 1

        engine.add_global_callback(callback)
        engine.add_global_callback(callback)
        engine.detect_and_trigger()

        assert count == 2

    def test_remove_nonexistent_callback_is_noop(self):
        engine = CollisionEngine(cell_size=100)

        def cb(a, b):
            pass

        engine.remove_global_callback(cb)
        engine.remove_pair_callback("a", "b", cb)

    def test_clear_removes_all_callbacks(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=30, min_y=30, max_x=80, max_y=80))
        engine.add_collider(c1)
        engine.add_collider(c2)

        count = 0

        def callback(a, b):
            nonlocal count
            count += 1

        engine.add_global_callback(callback)
        engine.add_pair_callback("a", "b", callback)
        engine.clear()

        engine.add_collider(c1)
        engine.add_collider(c2)
        engine.detect_and_trigger()

        assert count == 0
