import pytest

from solocoder_py.pip import Point, PointLocation, Polygon, PolygonWithHoles, RayCastingEngine

from .conftest import (
    build_butterfly_polygon,
    build_concave_polygon,
    build_engine,
    build_holed_polygon,
    build_square_polygon,
    build_triangle_polygon,
)


class TestSquarePointInPolygon:
    def test_point_inside_square(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 5)
        result = engine.contains(square, point)
        assert result == PointLocation.INSIDE
        assert engine.is_inside(square, point) is True

    def test_point_outside_square(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(15, 5)
        result = engine.contains(square, point)
        assert result == PointLocation.OUTSIDE
        assert engine.is_outside(square, point) is True
        assert engine.is_inside(square, point) is False

    def test_point_above_square(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 15)
        assert engine.contains(square, point) == PointLocation.OUTSIDE

    def test_point_below_square(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, -5)
        assert engine.contains(square, point) == PointLocation.OUTSIDE

    def test_point_left_of_square(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(-5, 5)
        assert engine.contains(square, point) == PointLocation.OUTSIDE

    def test_point_at_center_square_center(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(5, 5)
        assert engine.contains(square, point) == PointLocation.INSIDE

    def test_point_near_corner_inside(self):
        engine = build_engine()
        square = build_square_polygon()
        point = Point(1, 1)
        assert engine.contains(square, point) == PointLocation.INSIDE


class TestTrianglePointInPolygon:
    def test_point_inside_triangle(self):
        engine = build_engine()
        triangle = build_triangle_polygon()
        point = Point(5, 3)
        assert engine.contains(triangle, point) == PointLocation.INSIDE

    def test_point_outside_triangle(self):
        engine = build_engine()
        triangle = build_triangle_polygon()
        point = Point(5, 12)
        assert engine.contains(triangle, point) == PointLocation.OUTSIDE

    def test_point_at_triangle_base_vertex_inside(self):
        engine = build_engine()
        triangle = build_triangle_polygon()
        point = Point(5, 1)
        assert engine.contains(triangle, point) == PointLocation.INSIDE


class TestConcavePolygon:
    def test_point_in_notch_region_is_outside(self):
        engine = build_engine()
        concave = build_concave_polygon()
        point = Point(5, 8)
        assert engine.contains(concave, point) == PointLocation.OUTSIDE

    def test_point_below_notch_is_inside(self):
        engine = build_engine()
        concave = build_concave_polygon()
        point = Point(5, 3)
        assert engine.contains(concave, point) == PointLocation.INSIDE

    def test_point_left_upper_region_is_inside(self):
        engine = build_engine()
        concave = build_concave_polygon()
        point = Point(1, 8)
        assert engine.contains(concave, point) == PointLocation.INSIDE

    def test_point_right_upper_region_is_inside(self):
        engine = build_engine()
        concave = build_concave_polygon()
        point = Point(9, 8)
        assert engine.contains(concave, point) == PointLocation.INSIDE


class TestButterflyPolygon:
    def test_butterfly_upper_wing_inside(self):
        engine = build_engine()
        butterfly = build_butterfly_polygon()
        point = Point(5, 8)
        assert engine.contains(butterfly, point) == PointLocation.INSIDE

    def test_butterfly_lower_wing_inside(self):
        engine = build_engine()
        butterfly = build_butterfly_polygon()
        point = Point(5, 2)
        assert engine.contains(butterfly, point) == PointLocation.INSIDE

    def test_butterfly_left_middle_outside(self):
        engine = build_engine()
        butterfly = build_butterfly_polygon()
        point = Point(2, 5)
        assert engine.contains(butterfly, point) == PointLocation.OUTSIDE

    def test_butterfly_right_middle_outside(self):
        engine = build_engine()
        butterfly = build_butterfly_polygon()
        point = Point(8, 5)
        assert engine.contains(butterfly, point) == PointLocation.OUTSIDE


class TestPolygonWithHole:
    def test_point_inside_outer_outside_inner_is_inside(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 9)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.INSIDE
        assert engine.is_inside_holed(holed, point) is True

    def test_point_in_hole_is_outside(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 5)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.OUTSIDE
        assert engine.is_outside_holed(holed, point) is True

    def test_point_outside_outer_is_outside(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(15, 5)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.OUTSIDE

    def test_point_on_outer_boundary(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 0)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.ON_BOUNDARY
        assert engine.is_on_holed_boundary(holed, point) is True

    def test_point_on_inner_boundary(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 3)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.ON_BOUNDARY

    def test_point_left_of_hole_is_inside(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(1, 5)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.INSIDE

    def test_winding_order_detection(self):
        holed = build_holed_polygon()
        assert holed.outer_ring.is_counterclockwise()
        assert holed.hole_count == 1

    def test_polygon_with_holes_from_tuples(self):
        holed = PolygonWithHoles.from_tuples(
            outer_ring=[(0, 0), (10, 0), (10, 10), (0, 10)],
            inner_rings=[
                [(2, 2), (8, 2), (8, 8), (2, 8)],
            ],
        )
        assert holed.hole_count == 1
        engine = build_engine()
        assert engine.is_inside_holed(holed, Point(1, 1)) is True
        assert engine.is_inside_holed(holed, Point(5, 5)) is False


class TestContainsMany:
    def test_contains_many_points(self):
        engine = build_engine()
        square = build_square_polygon()
        points = [
            Point(5, 5),
            Point(15, 5),
            Point(0, 0),
            Point(5, 0),
        ]
        results = engine.contains_many(square, points)
        assert len(results) == 4
        assert results[0] == PointLocation.INSIDE
        assert results[1] == PointLocation.OUTSIDE
        assert results[2] == PointLocation.ON_BOUNDARY
        assert results[3] == PointLocation.ON_BOUNDARY


class TestGeographicCoordinates:
    def test_lat_lng_point_inside_rectangle(self):
        engine = build_engine()
        bbox = Polygon.from_tuples([
            (-122.0, 37.0),
            (-121.0, 37.0),
            (-121.0, 38.0),
            (-122.0, 38.0),
        ])
        sf_lat_lng = Point(-121.5, 37.5)
        assert engine.contains(bbox, sf_lat_lng) == PointLocation.INSIDE

    def test_lat_lng_point_outside_rectangle(self):
        engine = build_engine()
        bbox = Polygon.from_tuples([
            (-122.0, 37.0),
            (-121.0, 37.0),
            (-121.0, 38.0),
            (-122.0, 38.0),
        ])
        ny_lat_lng = Point(-74.0, 40.7)
        assert engine.contains(bbox, ny_lat_lng) == PointLocation.OUTSIDE


class TestIrregularPolygon:
    def test_irregular_polygon_inside(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (10, 2),
            (8, 8),
            (4, 10),
            (1, 6),
        ])
        point = Point(5, 5)
        assert engine.contains(polygon, point) == PointLocation.INSIDE

    def test_irregular_polygon_outside(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0),
            (10, 2),
            (8, 8),
            (4, 10),
            (1, 6),
        ])
        point = Point(12, 5)
        assert engine.contains(polygon, point) == PointLocation.OUTSIDE
