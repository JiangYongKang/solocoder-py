import math

import pytest

from solocoder_py.pip import (
    EmptyPolygonError,
    InsufficientVerticesError,
    InvalidCoordinateError,
    InvalidPointError,
    InvalidPolygonError,
    PipError,
    Point,
    Polygon,
    RayCastingEngine,
)

from .conftest import build_engine, build_square_polygon


class TestPointValidation:
    def test_point_with_nan_x(self):
        with pytest.raises(InvalidCoordinateError):
            Point(float("nan"), 5.0)

    def test_point_with_nan_y(self):
        with pytest.raises(InvalidCoordinateError):
            Point(5.0, float("nan"))

    def test_point_with_inf_x(self):
        with pytest.raises(InvalidCoordinateError):
            Point(float("inf"), 5.0)

    def test_point_with_neg_inf_x(self):
        with pytest.raises(InvalidCoordinateError):
            Point(float("-inf"), 5.0)

    def test_point_with_inf_y(self):
        with pytest.raises(InvalidCoordinateError):
            Point(5.0, float("inf"))

    def test_point_with_both_nan(self):
        with pytest.raises(InvalidCoordinateError):
            Point(float("nan"), float("nan"))

    def test_point_with_string_x(self):
        with pytest.raises(InvalidCoordinateError):
            Point("5", 5)

    def test_point_with_none_x(self):
        with pytest.raises(InvalidCoordinateError):
            Point(None, 5)


class TestPolygonValidation:
    def test_empty_polygon_from_tuples(self):
        with pytest.raises(EmptyPolygonError):
            Polygon.from_tuples([])

    def test_none_vertices(self):
        with pytest.raises(EmptyPolygonError):
            Polygon.from_tuples(None)

    def test_one_vertex(self):
        with pytest.raises(InsufficientVerticesError):
            Polygon.from_tuples([(0, 0)])

    def test_two_vertices(self):
        with pytest.raises(InsufficientVerticesError):
            Polygon.from_tuples([(0, 0), (1, 1)])

    def test_invalid_vertex_format(self):
        with pytest.raises(InvalidPointError):
            Polygon.from_tuples([(0, 0), (1, 1, 1), (2, 2)])

    def test_invalid_vertex_type(self):
        with pytest.raises(InvalidPointError):
            Polygon.from_tuples([(0, 0), "invalid", (2, 2)])

    def test_polygon_with_nan_vertex(self):
        with pytest.raises(InvalidCoordinateError):
            Polygon.from_tuples([(0, 0), (float("nan"), 5), (10, 10)])

    def test_polygon_with_inf_vertex(self):
        with pytest.raises(InvalidCoordinateError):
            Polygon.from_tuples([(0, 0), (float("inf"), 5), (10, 10)])

    def test_polygon_with_non_list_input(self):
        with pytest.raises(InvalidPolygonError):
            Polygon.from_tuples("not a list")

    def test_polygon_with_non_point_list(self):
        with pytest.raises(InvalidPolygonError):
            Polygon(vertices=[(0, 0), (1, 1), (2, 2)])


class TestEngineInputValidation:
    def test_engine_contains_with_invalid_polygon_type(self):
        engine = build_engine()
        point = Point(5, 5)
        with pytest.raises(InvalidPolygonError):
            engine.contains("not a polygon", point)

    def test_engine_contains_with_invalid_point_type(self):
        engine = build_engine()
        polygon = build_square_polygon()
        with pytest.raises(InvalidPointError):
            engine.contains(polygon, "not a point")

    def test_engine_is_inside_with_invalid_polygon(self):
        engine = build_engine()
        point = Point(5, 5)
        with pytest.raises(InvalidPolygonError):
            engine.is_inside("invalid", point)

    def test_engine_is_outside_with_invalid_point(self):
        engine = build_engine()
        polygon = build_square_polygon()
        with pytest.raises(InvalidPointError):
            engine.is_outside(polygon, "invalid")

    def test_engine_is_on_boundary_with_invalid_polygon(self):
        engine = build_engine()
        point = Point(5, 5)
        with pytest.raises(InvalidPolygonError):
            engine.is_on_boundary("invalid", point)


class TestExceptionHierarchy:
    def test_pip_error_base_class(self):
        assert issubclass(InvalidPointError, PipError)
        assert issubclass(InvalidPolygonError, PipError)

    def test_empty_polygon_is_invalid_polygon(self):
        assert issubclass(EmptyPolygonError, InvalidPolygonError)

    def test_insufficient_vertices_is_invalid_polygon(self):
        assert issubclass(InsufficientVerticesError, InvalidPolygonError)

    def test_invalid_coordinate_is_invalid_point(self):
        assert issubclass(InvalidCoordinateError, InvalidPointError)


class TestPolygonConstructorVariants:
    def test_from_tuples_creates_valid_polygon(self):
        polygon = Polygon.from_tuples([(0, 0), (10, 0), (10, 10)])
        assert polygon.vertex_count == 3
        assert isinstance(polygon.vertices[0], Point)

    def test_direct_constructor_with_points(self):
        points = [Point(0, 0), Point(10, 0), Point(10, 10)]
        polygon = Polygon(vertices=points)
        assert polygon.vertex_count == 3


class TestPointProperties:
    def test_point_to_tuple(self):
        p = Point(3.0, 4.0)
        assert p.to_tuple() == (3.0, 4.0)

    def test_point_iteration(self):
        p = Point(3.0, 4.0)
        x, y = p
        assert x == 3.0
        assert y == 4.0

    def test_point_equality(self):
        p1 = Point(3.0, 4.0)
        p2 = Point(3.0, 4.0)
        assert p1 == p2

    def test_point_hashable(self):
        p = Point(3.0, 4.0)
        s = {p}
        assert p in s


class TestContainsMany:
    def test_contains_many_with_empty_list(self):
        engine = build_engine()
        square = build_square_polygon()
        results = engine.contains_many(square, [])
        assert results == []

    def test_contains_many_preserves_order(self):
        engine = build_engine()
        square = build_square_polygon()
        points = [
            Point(5, 5),
            Point(15, 5),
            Point(0, 0),
        ]
        results = engine.contains_many(square, points)
        assert len(results) == 3
        from solocoder_py.pip import PointLocation
        assert results[0] == PointLocation.INSIDE
        assert results[1] == PointLocation.OUTSIDE
        assert results[2] == PointLocation.ON_BOUNDARY
