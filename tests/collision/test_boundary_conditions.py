import time

import pytest

from solocoder_py.collision import (
    AABB,
    Collider,
    CollisionEngine,
    SpatialHash,
)


class TestSpatialHashBoundaryCells:
    def test_collider_spanning_multiple_cells(self):
        sh = SpatialHash(cell_size=50)
        c = Collider(
            id="big",
            aabb=AABB(min_x=20, min_y=20, max_x=130, max_y=130),
        )
        sh.add(c)

        query = AABB(min_x=0, min_y=0, max_x=50, max_y=50)
        candidates = sh.get_candidates(query)
        assert len(candidates) == 1
        assert candidates[0].id == "big"

        query2 = AABB(min_x=100, min_y=100, max_x=150, max_y=150)
        candidates2 = sh.get_candidates(query2)
        assert len(candidates2) == 1
        assert candidates2[0].id == "big"

    def test_collider_on_cell_boundary(self):
        sh = SpatialHash(cell_size=50)
        c = Collider(
            id="boundary",
            aabb=AABB(min_x=50, min_y=50, max_x=100, max_y=100),
        )
        sh.add(c)

        query = AABB(min_x=40, min_y=40, max_x=60, max_y=60)
        candidates = sh.get_candidates(query)
        assert len(candidates) == 1
        assert candidates[0].id == "boundary"

    def test_negative_coordinates(self):
        sh = SpatialHash(cell_size=50)
        c = Collider(
            id="neg",
            aabb=AABB(min_x=-60, min_y=-60, max_x=-10, max_y=-10),
        )
        sh.add(c)

        query = AABB(min_x=-70, min_y=-70, max_x=0, max_y=0)
        candidates = sh.get_candidates(query)
        assert len(candidates) == 1
        assert candidates[0].id == "neg"


class TestAABBBoundary:
    def test_zero_width_aabb(self):
        a = AABB(min_x=10, min_y=10, max_x=10, max_y=50)
        assert a.width == 0
        assert a.height == 40

    def test_zero_height_aabb(self):
        a = AABB(min_x=10, min_y=10, max_x=50, max_y=10)
        assert a.width == 40
        assert a.height == 0

    def test_zero_size_aabb(self):
        a = AABB(min_x=10, min_y=10, max_x=10, max_y=10)
        assert a.width == 0
        assert a.height == 0
        assert a.intersects(a) is True

    def test_point_aabb_intersects_line_aabb(self):
        point = AABB(min_x=50, min_y=50, max_x=50, max_y=50)
        line = AABB(min_x=0, min_y=50, max_x=100, max_y=50)
        assert point.intersects(line) is True
        assert line.intersects(point) is True


class TestEdgeCollisions:
    def test_exactly_touching_on_x(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=50, min_y=0, max_x=100, max_y=50))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 1

    def test_exactly_touching_on_y(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=50, max_x=50, max_y=100))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 1

    def test_exactly_touching_corner(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=50, min_y=50, max_x=100, max_y=100))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 1

    def test_just_apart_on_x(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=51, min_y=0, max_x=100, max_y=50))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 0

    def test_just_apart_on_y(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=0, min_y=51, max_x=50, max_y=100))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 0


class TestLargeScalePerformance:
    def test_many_colliders_dense_scene(self):
        engine = CollisionEngine(cell_size=20)
        count = 500
        for i in range(count):
            x = (i % 25) * 8
            y = (i // 25) * 8
            c = Collider(
                id=f"c{i}",
                aabb=AABB(min_x=x, min_y=y, max_x=x + 10, max_y=y + 10),
            )
            engine.add_collider(c)

        assert engine.collider_count == count

        start = time.time()
        pairs = engine.check_all_collisions()
        elapsed = time.time() - start

        assert elapsed < 5.0
        assert len(pairs) > 0

    def test_grid_size_effect_on_candidates(self):
        small_grid = SpatialHash(cell_size=10)
        large_grid = SpatialHash(cell_size=100)

        c = Collider(
            id="big",
            aabb=AABB(min_x=0, min_y=0, max_x=200, max_y=200),
        )

        small_grid.add(c)
        large_grid.add(c)

        query = AABB(min_x=50, min_y=50, max_x=60, max_y=60)
        small_candidates = small_grid.get_candidates(query)
        large_candidates = large_grid.get_candidates(query)

        assert len(small_candidates) == 1
        assert len(large_candidates) == 1


class TestUpdateCollider:
    def test_update_changes_position(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="mover", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)

        c2 = Collider(id="target", aabb=AABB(min_x=200, min_y=200, max_x=250, max_y=250))
        engine.add_collider(c2)

        assert len(engine.check_collision("mover")) == 0

        updated = Collider(id="mover", aabb=AABB(min_x=180, min_y=180, max_x=230, max_y=230))
        engine.update_collider(updated)

        collided = engine.check_collision("mover")
        assert len(collided) == 1
        assert collided[0].id == "target"

    def test_update_same_collider_twice(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)

        c2 = Collider(id="a", aabb=AABB(min_x=10, min_y=10, max_x=60, max_y=60))
        engine.update_collider(c2)

        assert engine.collider_count == 1
        retrieved = engine.get_collider("a")
        assert retrieved.aabb.min_x == 10


class TestResizeGrid:
    def test_resize_grid_preserves_colliders(self):
        engine = CollisionEngine(cell_size=50)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=30, max_y=30))
        c2 = Collider(id="b", aabb=AABB(min_x=20, min_y=20, max_x=50, max_y=50))
        engine.add_collider(c1)
        engine.add_collider(c2)

        pairs_before = engine.check_all_collisions()
        assert len(pairs_before) == 1

        engine.resize_grid(100)
        assert engine.cell_size == 100
        assert engine.collider_count == 2

        pairs_after = engine.check_all_collisions()
        assert len(pairs_after) == 1

    def test_resize_to_smaller_grid(self):
        engine = CollisionEngine(cell_size=200)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=30, max_y=30))
        c2 = Collider(id="b", aabb=AABB(min_x=200, min_y=200, max_x=230, max_y=230))
        engine.add_collider(c1)
        engine.add_collider(c2)

        engine.resize_grid(50)

        pairs = engine.check_all_collisions()
        assert len(pairs) == 0


class TestColliderWithData:
    def test_collider_stores_data(self):
        data = {"health": 100, "type": "player"}
        c = Collider(id="p1", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50), data=data)
        assert c.data is data
        assert c.data["health"] == 100

    def test_callback_receives_data(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(
            id="player",
            aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50),
            data={"name": "hero"},
        )
        c2 = Collider(
            id="coin",
            aabb=AABB(min_x=30, min_y=30, max_x=70, max_y=70),
            data={"value": 100},
        )
        engine.add_collider(c1)
        engine.add_collider(c2)

        received = []

        def callback(a, b):
            received.append((a.data, b.data))

        engine.add_global_callback(callback)
        engine.detect_and_trigger()

        assert len(received) == 1
        data_a, data_b = received[0]
        all_data = [data_a, data_b]
        assert any(d.get("name") == "hero" for d in all_data)
        assert any(d.get("value") == 100 for d in all_data)


class TestEmptyEngine:
    def test_empty_engine_no_collisions(self):
        engine = CollisionEngine(cell_size=100)
        pairs = engine.check_all_collisions()
        assert len(pairs) == 0

    def test_single_collider_no_collisions(self):
        engine = CollisionEngine(cell_size=100)
        c = Collider(id="only", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        engine.add_collider(c)
        pairs = engine.check_all_collisions()
        assert len(pairs) == 0
        assert len(engine.check_collision("only")) == 0


class TestRemoveCallbacksWithCollider:
    def test_removing_collider_removes_pair_callbacks(self):
        engine = CollisionEngine(cell_size=100)
        c1 = Collider(id="a", aabb=AABB(min_x=0, min_y=0, max_x=50, max_y=50))
        c2 = Collider(id="b", aabb=AABB(min_x=30, min_y=30, max_x=80, max_y=80))
        engine.add_collider(c1)
        engine.add_collider(c2)

        count = 0

        def callback(a, b):
            nonlocal count
            count += 1

        engine.add_pair_callback("a", "b", callback)
        engine.detect_and_trigger()
        assert count == 1

        engine.remove_collider("a")
        engine.add_collider(c1)
        engine.detect_and_trigger()
        assert count == 1
