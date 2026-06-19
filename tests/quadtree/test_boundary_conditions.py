import pytest

from solocoder_py.quadtree import Point, Quadtree, Rectangle


class TestEmptyQuadtree:
    def test_empty_quadtree_query_returns_empty(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(result) == 0

    def test_empty_quadtree_get_all_returns_empty(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        assert len(qt.get_all()) == 0

    def test_empty_quadtree_count_is_zero(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        assert qt.point_count == 0
        assert qt.rectangle_count == 0
        assert qt.total_count == 0


class TestPointsOnQuadrantBoundary:
    def test_point_on_center_boundary(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        center_point = Point(x=100, y=100, data="center")
        qt.insert(center_point)

        p1 = Point(x=25, y=25, data="sw")
        qt.insert(p1)

        result = qt.query(Rectangle(x=90, y=90, width=20, height=20))
        result_data = {r.data for r in result}
        assert "center" in result_data

    def test_point_on_vertical_divider(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        divider_point = Point(x=100, y=25, data="on_vline")
        qt.insert(divider_point)

        p1 = Point(x=25, y=25, data="left")
        qt.insert(p1)

        all_points = qt.get_all()
        assert len(all_points) == 2

        left_result = qt.query(Rectangle(x=0, y=0, width=99, height=200))
        left_data = {p.data for p in left_result}
        assert "left" in left_data

        right_result = qt.query(Rectangle(x=101, y=0, width=99, height=200))
        right_data = {p.data for p in right_result}
        assert "on_vline" not in right_data

    def test_point_on_horizontal_divider(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        divider_point = Point(x=25, y=100, data="on_hline")
        qt.insert(divider_point)

        p1 = Point(x=25, y=25, data="bottom")
        qt.insert(p1)

        all_points = qt.get_all()
        assert len(all_points) == 2

        bottom_result = qt.query(Rectangle(x=0, y=0, width=200, height=99))
        bottom_data = {p.data for p in bottom_result}
        assert "bottom" in bottom_data

        top_result = qt.query(Rectangle(x=0, y=101, width=200, height=99))
        top_data = {p.data for p in top_result}
        assert "on_hline" not in top_data


class TestCapacityThreshold:
    def test_exactly_at_capacity_no_split(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=3, max_depth=5)

        qt.insert(Point(x=25, y=25, data="p1"))
        qt.insert(Point(x=50, y=50, data="p2"))
        qt.insert(Point(x=75, y=75, data="p3"))

        assert qt.point_count == 3
        all_points = qt.get_all()
        assert len(all_points) == 3

    def test_exceeding_capacity_triggers_split(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=5)

        qt.insert(Point(x=25, y=25, data="sw"))
        qt.insert(Point(x=175, y=175, data="ne"))
        assert qt.point_count == 2

        qt.insert(Point(x=25, y=175, data="nw"))
        assert qt.point_count == 3

        sw_result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(sw_result) == 1
        assert sw_result[0].data == "sw"

    def test_capacity_one(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        qt.insert(Point(x=25, y=25, data="sw"))
        assert qt.point_count == 1

        qt.insert(Point(x=175, y=175, data="ne"))
        assert qt.point_count == 2

        sw_result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(sw_result) == 1
        assert sw_result[0].data == "sw"

        ne_result = qt.query(Rectangle(x=100, y=100, width=100, height=100))
        assert len(ne_result) == 1
        assert ne_result[0].data == "ne"


class TestMaxDepthConstraint:
    def test_max_depth_zero_no_split(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=0)

        for i in range(10):
            qt.insert(Point(x=10 + i * 10, y=10 + i * 10, data=f"p{i}"))

        assert qt.point_count == 10
        all_points = qt.get_all()
        assert len(all_points) == 10

    def test_stops_splitting_at_max_depth(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=2)

        points = []
        for i in range(20):
            p = Point(x=10 + i * 2, y=10 + i * 3, data=f"p{i}")
            points.append(p)
            qt.insert(p)

        assert qt.point_count == 20
        all_points = qt.get_all()
        assert len(all_points) == 20

    def test_max_depth_query_still_works(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=1)

        qt.insert(Point(x=25, y=25, data="sw1"))
        qt.insert(Point(x=35, y=35, data="sw2"))
        qt.insert(Point(x=45, y=45, data="sw3"))

        sw_result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(sw_result) == 3


class TestQueryNoIntersection:
    def test_query_completely_outside(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=50, y=50, data="p1"))

        result = qt.query(Rectangle(x=300, y=300, width=100, height=100))
        assert len(result) == 0

    def test_query_touches_but_no_overlap_x(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=50, y=50, data="p1"))

        result = qt.query(Rectangle(x=201, y=0, width=100, height=200))
        assert len(result) == 0

    def test_query_touches_but_no_overlap_y(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=50, y=50, data="p1"))

        result = qt.query(Rectangle(x=0, y=201, width=200, height=100))
        assert len(result) == 0


class TestZeroSizeObjects:
    def test_zero_size_point_is_valid(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        p = Point(x=50, y=50, data="p")
        qt.insert(p)
        assert qt.point_count == 1

    def test_zero_width_rectangle(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        rect = Rectangle(x=50, y=50, width=0, height=50, data="line")
        qt.insert(rect)
        assert qt.rectangle_count == 1

        result = qt.query(Rectangle(x=40, y=40, width=20, height=60))
        assert len(result) == 1

    def test_zero_height_rectangle(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        rect = Rectangle(x=50, y=50, width=50, height=0, data="hline")
        qt.insert(rect)
        assert qt.rectangle_count == 1

    def test_zero_size_rectangle(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=4)
        rect = Rectangle(x=50, y=50, width=0, height=0, data="point_rect")
        qt.insert(rect)
        assert qt.rectangle_count == 1


class TestLargeRectangles:
    def test_full_boundary_rectangle_stays_at_root(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        full_rect = Rectangle(x=0, y=0, width=200, height=200, data="full")
        qt.insert(full_rect)

        p1 = Point(x=25, y=25, data="sw")
        p2 = Point(x=175, y=175, data="ne")
        qt.insert(p1)
        qt.insert(p2)

        result = qt.query(Rectangle(x=50, y=50, width=100, height=100))
        result_data = {r.data for r in result}
        assert "full" in result_data

    def test_rectangle_spanning_all_four_quadrants(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=1, max_depth=5)

        cross_rect = Rectangle(x=25, y=25, width=150, height=150, data="cross")
        qt.insert(cross_rect)

        p1 = Point(x=10, y=10, data="sw")
        qt.insert(p1)

        results = qt.query(Rectangle(x=0, y=0, width=200, height=200))
        result_data = {r.data for r in results}
        assert "cross" in result_data
        assert "sw" in result_data
