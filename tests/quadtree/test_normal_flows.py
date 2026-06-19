import pytest

from solocoder_py.quadtree import Point, Quadtree, Rectangle

from .conftest import build_quadtree_with_points


class TestPointInsertion:
    def test_insert_single_point(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        p = Point(x=50, y=50, data="test")
        qt.insert(p)
        assert qt.point_count == 1
        assert qt.total_count == 1

    def test_insert_multiple_points_same_quadrant(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        for i in range(4):
            qt.insert(Point(x=20 + i * 5, y=20 + i * 5, data=f"p{i}"))
        assert qt.point_count == 4

    def test_points_distributed_to_correct_quadrants(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        nw = Point(x=25, y=175, data="nw")
        ne = Point(x=175, y=175, data="ne")
        sw = Point(x=25, y=25, data="sw")
        se = Point(x=175, y=25, data="se")

        qt.insert(nw)
        qt.insert(ne)
        qt.insert(sw)
        qt.insert(se)

        results = qt.query(Rectangle(x=0, y=0, width=200, height=200))
        assert len(results) == 4

        data_set = {r.data for r in results}
        assert data_set == {"nw", "ne", "sw", "se"}


class TestRectangleInsertion:
    def test_insert_single_rectangle(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        rect = Rectangle(x=10, y=10, width=30, height=30, data="rect1")
        qt.insert(rect)
        assert qt.rectangle_count == 1
        assert qt.total_count == 1

    def test_rectangle_spanning_quadrant_kept_in_parent(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        big_rect = Rectangle(x=50, y=50, width=100, height=100, data="big")
        qt.insert(big_rect)

        p1 = Point(x=25, y=25, data="sw")
        p2 = Point(x=175, y=175, data="ne")
        qt.insert(p1)
        qt.insert(p2)

        results = qt.query(Rectangle(x=0, y=0, width=200, height=200))
        result_data = {r.data for r in results}
        assert "big" in result_data
        assert "sw" in result_data
        assert "ne" in result_data

    def test_small_rectangle_fits_in_quadrant(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        p1 = Point(x=25, y=25, data="p1")
        qt.insert(p1)

        small_rect = Rectangle(x=10, y=10, width=20, height=20, data="small")
        qt.insert(small_rect)

        results = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        result_data = {r.data for r in results}
        assert "p1" in result_data
        assert "small" in result_data


class TestRangeQuery:
    def test_query_returns_intersecting_points(self):
        qt, p1, p2, p3, p4, _ = build_quadtree_with_points(max_capacity=4)

        result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(result) == 4

    def test_query_partial_overlap(self):
        qt, p1, p2, p3, p4, _ = build_quadtree_with_points(max_capacity=4)

        result = qt.query(Rectangle(x=0, y=0, width=50, height=200))
        result_data = {p.data for p in result}
        assert "sw1" in result_data
        assert "nw1" in result_data
        assert "se1" not in result_data
        assert "ne1" not in result_data

    def test_query_with_rectangles(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)

        rect1 = Rectangle(x=20, y=20, width=30, height=30, data="r1")
        rect2 = Rectangle(x=120, y=120, width=50, height=50, data="r2")
        qt.insert(rect1)
        qt.insert(rect2)

        result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        result_data = {r.data for r in result}
        assert "r1" in result_data
        assert "r2" not in result_data

    def test_query_includes_parent_rectangles(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        big_rect = Rectangle(x=50, y=50, width=100, height=100, data="big")
        qt.insert(big_rect)

        p1 = Point(x=25, y=25, data="sw")
        qt.insert(p1)

        result = qt.query(Rectangle(x=75, y=75, width=50, height=50))
        result_data = {r.data for r in result}
        assert "big" in result_data
        assert "sw" not in result_data


class TestTreeSplitAndMigration:
    def test_split_when_exceeding_capacity(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=5)

        qt.insert(Point(x=25, y=25, data="sw1"))
        qt.insert(Point(x=175, y=175, data="ne1"))
        assert qt.point_count == 2

        qt.insert(Point(x=75, y=75, data="se1"))

        assert qt.point_count == 3
        all_points = qt.get_all()
        assert len(all_points) == 3

    def test_objects_migrate_to_subnodes_after_split(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=5)

        p1 = Point(x=25, y=25, data="sw")
        p2 = Point(x=175, y=25, data="se")
        p3 = Point(x=25, y=175, data="nw")

        qt.insert(p1)
        qt.insert(p2)
        qt.insert(p3)

        sw_results = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(sw_results) == 1
        assert sw_results[0].data == "sw"

        nw_results = qt.query(Rectangle(x=0, y=100, width=100, height=100))
        assert len(nw_results) == 1
        assert nw_results[0].data == "nw"

        se_results = qt.query(Rectangle(x=100, y=0, width=100, height=100))
        assert len(se_results) == 1
        assert se_results[0].data == "se"

    def test_large_rectangle_stays_in_parent_after_split(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=5)

        big_rect = Rectangle(x=40, y=40, width=120, height=120, data="big")
        p1 = Point(x=25, y=25, data="sw")
        p2 = Point(x=175, y=175, data="ne")
        p3 = Point(x=25, y=175, data="nw")

        qt.insert(big_rect)
        qt.insert(p1)
        qt.insert(p2)
        qt.insert(p3)

        query_rect = Rectangle(x=50, y=50, width=100, height=100)
        results = qt.query(query_rect)
        result_data = {r.data for r in results}
        assert "big" in result_data

        all_results = qt.get_all()
        assert len(all_results) == 4


class TestGetAll:
    def test_get_all_returns_all_objects(self):
        qt, p1, p2, p3, p4, _ = build_quadtree_with_points(max_capacity=4)
        all_objs = qt.get_all()
        assert len(all_objs) == 4

    def test_get_all_mixed_points_and_rectangles(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)

        qt.insert(Point(x=50, y=50, data="p1"))
        qt.insert(Point(x=150, y=150, data="p2"))
        qt.insert(Rectangle(x=10, y=10, width=30, height=30, data="r1"))

        all_objs = qt.get_all()
        assert len(all_objs) == 3


class TestClear:
    def test_clear_removes_all_objects(self):
        qt, _, _, _, _, _ = build_quadtree_with_points(max_capacity=4)
        assert qt.total_count == 4
        qt.clear()
        assert qt.total_count == 0
        assert len(qt.get_all()) == 0

    def test_clear_preserves_configuration(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=8, max_depth=15)
        qt.insert(Point(x=50, y=50))
        qt.clear()
        assert qt.max_capacity == 8
        assert qt.max_depth == 15
        assert qt.boundary.width == 200
        assert qt.boundary.height == 200
