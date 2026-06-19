import random

import pytest

from solocoder_py.quadtree import (
    DuplicatePointError,
    InvalidCapacityError,
    InvalidDepthError,
    InvalidRectangleError,
    OutOfBoundsError,
    Point,
    Quadtree,
    QuadtreeError,
    Rectangle,
)


class TestOutOfBounds:
    def test_insert_point_outside_left(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Point(x=-1, y=50))

    def test_insert_point_outside_right(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Point(x=101, y=50))

    def test_insert_point_outside_bottom(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Point(x=50, y=-1))

    def test_insert_point_outside_top(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Point(x=50, y=101))

    def test_insert_rectangle_completely_outside(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=200, y=200, width=50, height=50))

    def test_insert_rectangle_partially_outside_right(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=50, y=50, width=100, height=100))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_partially_outside_left(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=-50, y=50, width=100, height=50))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_partially_outside_top(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=50, y=50, width=50, height=100))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_partially_outside_bottom(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=50, y=-50, width=50, height=100))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_partially_outside_multiple_sides(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=-10, y=-10, width=120, height=120))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_exceeding_right_boundary(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=0, y=0, width=150, height=50))
        assert qt.rectangle_count == 0

    def test_insert_rectangle_exceeding_top_boundary(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(OutOfBoundsError):
            qt.insert(Rectangle(x=0, y=0, width=50, height=150))
        assert qt.rectangle_count == 0

    def test_insert_point_on_boundary_is_valid(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=100, y=100))
        assert qt.point_count == 1

    def test_insert_rectangle_on_boundary_is_valid(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Rectangle(x=0, y=0, width=100, height=100))
        assert qt.rectangle_count == 1


class TestDuplicatePoints:
    def test_insert_duplicate_point_raises(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=50, y=50, data="first"))
        with pytest.raises(DuplicatePointError):
            qt.insert(Point(x=50, y=50, data="second"))
        assert qt.point_count == 1

    def test_duplicate_point_different_data_raises(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        qt.insert(Point(x=30, y=30, data={"a": 1}))
        with pytest.raises(DuplicatePointError):
            qt.insert(Point(x=30, y=30, data={"b": 2}))

    def test_duplicate_point_after_split_raises(self):
        boundary = Rectangle(x=0, y=0, width=200, height=200)
        qt = Quadtree(boundary, max_capacity=2, max_depth=5)

        qt.insert(Point(x=25, y=25, data="sw1"))
        qt.insert(Point(x=175, y=175, data="ne1"))
        qt.insert(Point(x=25, y=175, data="nw1"))

        with pytest.raises(DuplicatePointError):
            qt.insert(Point(x=25, y=25, data="sw1_dup"))

        assert qt.point_count == 3


class TestInvalidParameters:
    def test_zero_capacity_raises(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        with pytest.raises(InvalidCapacityError):
            Quadtree(boundary, max_capacity=0)

    def test_negative_capacity_raises(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        with pytest.raises(InvalidCapacityError):
            Quadtree(boundary, max_capacity=-1)

    def test_negative_max_depth_raises(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        with pytest.raises(InvalidDepthError):
            Quadtree(boundary, max_capacity=4, max_depth=-1)

    def test_invalid_rectangle_negative_width(self):
        with pytest.raises(InvalidRectangleError):
            Rectangle(x=0, y=0, width=-10, height=10)

    def test_invalid_rectangle_negative_height(self):
        with pytest.raises(InvalidRectangleError):
            Rectangle(x=0, y=0, width=10, height=-10)

    def test_insert_unsupported_type(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=4)
        with pytest.raises(TypeError):
            qt.insert("not a spatial object")


class TestExceptionHierarchy:
    def test_out_of_bounds_inherits_from_quadtree_error(self):
        assert issubclass(OutOfBoundsError, QuadtreeError)

    def test_duplicate_point_inherits_from_quadtree_error(self):
        assert issubclass(DuplicatePointError, QuadtreeError)

    def test_invalid_capacity_inherits_from_quadtree_error(self):
        assert issubclass(InvalidCapacityError, QuadtreeError)

    def test_invalid_depth_inherits_from_quadtree_error(self):
        assert issubclass(InvalidDepthError, QuadtreeError)

    def test_invalid_rectangle_inherits_from_quadtree_error(self):
        assert issubclass(InvalidRectangleError, QuadtreeError)


class TestMaxDepthInRecursiveInsert:
    def test_deep_recursion_stops_at_max_depth(self):
        boundary = Rectangle(x=0, y=0, width=1024, height=1024)
        max_depth = 4
        qt = Quadtree(boundary, max_capacity=1, max_depth=max_depth)

        for i in range(20):
            qt.insert(Point(x=1 + i * 0.1, y=1 + i * 0.1, data=f"p{i}"))

        assert qt.point_count == 20

        all_points = qt.get_all()
        assert len(all_points) == 20

    def test_max_depth_zero_all_points_in_root(self):
        boundary = Rectangle(x=0, y=0, width=100, height=100)
        qt = Quadtree(boundary, max_capacity=1, max_depth=0)

        points = [
            Point(x=10, y=10, data="p1"),
            Point(x=20, y=20, data="p2"),
            Point(x=80, y=80, data="p3"),
            Point(x=90, y=90, data="p4"),
        ]
        for p in points:
            qt.insert(p)

        result = qt.query(Rectangle(x=0, y=0, width=100, height=100))
        assert len(result) == 4


class TestRandomizedCorrectness:
    def test_random_points_query_matches_bruteforce(self):
        random.seed(42)
        boundary = Rectangle(x=0, y=0, width=1000, height=1000)
        qt = Quadtree(boundary, max_capacity=8, max_depth=10)

        all_points = []
        for i in range(200):
            x = random.uniform(0, 1000)
            y = random.uniform(0, 1000)
            p = Point(x=x, y=y, data=f"p{i}")
            all_points.append(p)
            qt.insert(p)

        query_rects = [
            Rectangle(x=0, y=0, width=1000, height=1000),
            Rectangle(x=100, y=100, width=300, height=300),
            Rectangle(x=500, y=500, width=500, height=500),
            Rectangle(x=200, y=600, width=400, height=200),
            Rectangle(x=0, y=0, width=50, height=50),
            Rectangle(x=900, y=900, width=200, height=200),
        ]

        for query_rect in query_rects:
            qt_results = qt.query(query_rect)
            brute_results = [p for p in all_points if query_rect.contains_point(p)]

            qt_data = {p.data for p in qt_results if isinstance(p, Point)}
            brute_data = {p.data for p in brute_results}

            assert qt_data == brute_data

    def test_random_rectangles_query_matches_bruteforce(self):
        random.seed(123)
        boundary = Rectangle(x=0, y=0, width=1000, height=1000)
        qt = Quadtree(boundary, max_capacity=8, max_depth=10)

        all_rects = []
        for i in range(100):
            w = random.uniform(10, 200)
            h = random.uniform(10, 200)
            x = random.uniform(0, 1000 - w)
            y = random.uniform(0, 1000 - h)
            rect = Rectangle(x=x, y=y, width=w, height=h, data=f"r{i}")
            all_rects.append(rect)
            qt.insert(rect)

        query_rects = [
            Rectangle(x=0, y=0, width=1000, height=1000),
            Rectangle(x=100, y=100, width=300, height=300),
            Rectangle(x=400, y=400, width=400, height=400),
            Rectangle(x=200, y=600, width=300, height=300),
        ]

        for query_rect in query_rects:
            qt_results = qt.query(query_rect)
            brute_results = [r for r in all_rects if query_rect.intersects(r)]

            qt_data = {r.data for r in qt_results if isinstance(r, Rectangle)}
            brute_data = {r.data for r in brute_results}

            assert qt_data == brute_data

    def test_mixed_random_objects_query_matches_bruteforce(self):
        random.seed(456)
        boundary = Rectangle(x=0, y=0, width=1000, height=1000)
        qt = Quadtree(boundary, max_capacity=8, max_depth=10)

        all_points = []
        all_rects = []

        for i in range(150):
            x = random.uniform(0, 1000)
            y = random.uniform(0, 1000)
            p = Point(x=x, y=y, data=f"p{i}")
            all_points.append(p)
            qt.insert(p)

        for i in range(50):
            w = random.uniform(20, 150)
            h = random.uniform(20, 150)
            x = random.uniform(0, 1000 - w)
            y = random.uniform(0, 1000 - h)
            rect = Rectangle(x=x, y=y, width=w, height=h, data=f"r{i}")
            all_rects.append(rect)
            qt.insert(rect)

        query_rect = Rectangle(x=200, y=200, width=600, height=600)
        qt_results = qt.query(query_rect)

        brute_points = [p for p in all_points if query_rect.contains_point(p)]
        brute_rects = [r for r in all_rects if query_rect.intersects(r)]

        qt_point_data = {o.data for o in qt_results if isinstance(o, Point)}
        qt_rect_data = {o.data for o in qt_results if isinstance(o, Rectangle)}
        brute_point_data = {p.data for p in brute_points}
        brute_rect_data = {r.data for r in brute_rects}

        assert qt_point_data == brute_point_data
        assert qt_rect_data == brute_rect_data

    def test_get_all_matches_bruteforce_count(self):
        random.seed(789)
        boundary = Rectangle(x=0, y=0, width=500, height=500)
        qt = Quadtree(boundary, max_capacity=4, max_depth=8)

        n_points = 100
        n_rects = 50

        for i in range(n_points):
            x = random.uniform(0, 500)
            y = random.uniform(0, 500)
            qt.insert(Point(x=x, y=y, data=f"p{i}"))

        for i in range(n_rects):
            x = random.uniform(0, 400)
            y = random.uniform(0, 400)
            w = random.uniform(10, 100)
            h = random.uniform(10, 100)
            qt.insert(Rectangle(x=x, y=y, width=w, height=h, data=f"r{i}"))

        assert qt.point_count == n_points
        assert qt.rectangle_count == n_rects
        assert qt.total_count == n_points + n_rects
        assert len(qt.get_all()) == n_points + n_rects
