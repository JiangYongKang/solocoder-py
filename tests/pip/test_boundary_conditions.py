import pytest

from solocoder_py.pip import Point, PointLocation, Polygon, RayCastingEngine

from .conftest import build_engine, build_square_polygon


class TestPointOnVertex:
    def test_point_on_corner_vertex(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(0, 0)
        result = engine.contains(square, point)
        assert result == PointLocation.ON_BOUNDARY
        assert engine.is_on_boundary(square, point) is True

    def test_point_on_all_four_corners(self):
        engine = build_engine()
        square = build_square_polygon()
        corners = [
            Point(0, 0),
            Point(10, 0),
            Point(10, 10),
            Point(0, 10),
        ]
        for corner in corners:
            assert engine.contains(square, corner) == PointLocation.ON_BOUNDARY
            assert engine.is_inside(square, corner) is True


class TestPointOnEdge:
    def test_point_on_bottom_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 0)
        assert engine.contains(square, point) == PointLocation.ON_BOUNDARY

    def test_point_on_right_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(10, 5)
        assert engine.contains(square, point) == PointLocation.ON_BOUNDARY

    def test_point_on_top_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 10)
        assert engine.contains(square, point) == PointLocation.ON_BOUNDARY

    def test_point_on_left_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(0, 5)
        assert engine.contains(square, point) == PointLocation.ON_BOUNDARY

    def test_point_on_diagonal_edge(self):
        engine = build_engine()
        triangle = Polygon.from_tuples([
            (0, 0),
            (10, 0),
            (0, 10),
        ])
        point = Point(3, 7)
        assert engine.contains(triangle, point) == PointLocation.ON_BOUNDARY


class TestHorizontalEdge:
    def test_point_on_horizontal_edge(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ])
        point = Point(3, 0)
        assert engine.contains(polygon, point) == PointLocation.ON_BOUNDARY

    def test_point_just_above_horizontal_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 0.0001)
        assert engine.contains(square, point) == PointLocation.INSIDE

    def test_point_just_below_horizontal_edge(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, -0.0001)
        assert engine.contains(square, point) == PointLocation.OUTSIDE


class TestRayPassingThroughVertex:
    def test_ray_through_vertex_edges_on_opposite_sides_counts_once(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 5),
        ])
        point = Point(2, 5)
        prev_vertex = Point(10, 10)
        next_vertex = Point(0, 0)
        assert (prev_vertex.y > 5) != (next_vertex.y > 5)
        result = engine.contains(polygon, point)
        assert result == PointLocation.INSIDE

    def test_ray_through_vertex_edges_on_same_side_counts_zero(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (5, 5),
            (10, 0),
            (10, 10),
            (0, 10),
        ])
        point = Point(2, 5)
        prev_vertex = Point(0, 0)
        next_vertex = Point(10, 0)
        assert (prev_vertex.y > 5) == (next_vertex.y > 5)
        result = engine.contains(polygon, point)
        assert result == PointLocation.INSIDE


class TestNearBoundary:
    def test_point_just_inside_boundary(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(0.0001, 5)
        assert engine.contains(square, point) == PointLocation.INSIDE

    def test_point_just_outside_boundary(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(-0.0001, 5)
        assert engine.contains(square, point) == PointLocation.OUTSIDE

    def test_point_very_close_to_edge_but_outside(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(10.000001, 5)
        assert engine.contains(square, point) == PointLocation.OUTSIDE


class TestDegeneratePolygon:
    def test_colinear_vertices_polygon(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (5, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ])
        point_inside = Point(5, 5)
        assert engine.contains(polygon, point_inside) == PointLocation.INSIDE

        point_outside = Point(15, 5)
        assert engine.contains(polygon, point_outside) == PointLocation.OUTSIDE

    def test_duplicate_vertices(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (0, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ])
        point_inside = Point(5, 5)
        assert engine.contains(polygon, point_inside) == PointLocation.INSIDE

    def test_multiple_colinear_points_on_edge(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (3, 0),
            (7, 0),
            (10, 0),
            (10, 10),
            (0, 10),
        ])
        point = Point(5, 5)
        assert engine.contains(polygon, point) == PointLocation.INSIDE


class TestSelfIntersectingPolygon:
    def test_butterfly_upper_wing_inside(self):
        engine = build_engine()
        butterfly = Polygon.from_tuples([
            (0, 0),
            (10, 10),
            (0, 10),
            (10, 0),
        ])
        point = Point(5, 8)
        result = engine.contains(butterfly, point)
        assert result == PointLocation.INSIDE

    def test_butterfly_lower_wing_inside(self):
        engine = build_engine()
        butterfly = Polygon.from_tuples([
            (0, 0),
            (10, 10),
            (0, 10),
            (10, 0),
        ])
        point = Point(5, 2)
        result = engine.contains(butterfly, point)
        assert result == PointLocation.INSIDE

    def test_butterfly_center_on_edge(self):
        engine = build_engine()
        butterfly = Polygon.from_tuples([
            (0, 0),
            (10, 10),
            (0, 10),
            (10, 0),
        ])
        point = Point(5, 5)
        result = engine.contains(butterfly, point)
        assert result == PointLocation.ON_BOUNDARY


class TestCustomEpsilon:
    def test_custom_epsilon_on_boundary(self):
        engine = RayCastingEngine(epsilon=1e-6)
        square = build_square_polygon()
        point = Point(5, 0.0000001)
        assert engine.contains(square, point) == PointLocation.ON_BOUNDARY

    def test_custom_epsilon_property(self):
        engine = RayCastingEngine(epsilon=1e-5)
        assert engine.epsilon == 1e-5
