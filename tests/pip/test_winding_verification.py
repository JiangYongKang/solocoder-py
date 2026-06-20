from __future__ import annotations

import pytest

from solocoder_py.pip import Point, PointLocation, Polygon, PolygonWithHoles, RayCastingEngine

from .conftest import build_butterfly_polygon, build_engine, build_holed_polygon


class TestSignedRayCastingVerification:
    def test_counterclockwise_square_has_positive_winding(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0), (10, 0), (10, 10), (0, 10),
        ])
        assert polygon.is_counterclockwise()
        point = Point(5, 5)
        winding = engine._signed_ray_casting(polygon, point)
        assert winding == 1

    def test_clockwise_square_has_negative_winding(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0), (0, 10), (10, 10), (10, 0),
        ])
        assert polygon.is_clockwise()
        point = Point(5, 5)
        winding = engine._signed_ray_casting(polygon, point)
        assert winding == -1

    def test_point_outside_has_zero_winding(self):
        engine = build_engine()
        polygon = Polygon.from_tuples([
            (0, 0), (10, 0), (10, 10), (0, 10),
        ])
        point = Point(15, 5)
        winding = engine._signed_ray_casting(polygon, point)
        assert winding == 0

    def test_parity_matches_absolute_winding_parity(self):
        engine = build_engine()
        polygon = build_butterfly_polygon()
        test_points = [
            Point(5, 8),
            Point(5, 2),
            Point(2, 5),
            Point(8, 5),
        ]
        for point in test_points:
            parity_result = engine._ray_casting(polygon, point)
            winding = engine._signed_ray_casting(polygon, point)
            assert parity_result == (abs(winding) % 2 == 1)


class TestHoledPolygonWindingVerification:
    def test_outer_ring_counterclockwise(self):
        holed = build_holed_polygon()
        assert holed.outer_ring.is_counterclockwise()
        assert holed.outer_ring.winding_order > 0

    def test_inner_rings_clockwise(self):
        holed = build_holed_polygon()
        for inner_ring in holed.inner_rings:
            assert inner_ring.is_clockwise()
            assert inner_ring.winding_order < 0

    def test_point_in_hole_zero_total_winding(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 5)
        outer_winding = engine._signed_ray_casting(holed.outer_ring, point)
        inner_winding = engine._signed_ray_casting(holed.inner_rings[0], point)
        total = outer_winding + inner_winding
        assert total == 0
        assert engine.contains_holed(holed, point) == PointLocation.OUTSIDE

    def test_point_between_rings_positive_total_winding(self):
        engine = build_engine()
        holed = build_holed_polygon()
        point = Point(5, 9)
        outer_winding = engine._signed_ray_casting(holed.outer_ring, point)
        inner_winding = engine._signed_ray_casting(holed.inner_rings[0], point)
        total = outer_winding + inner_winding
        assert total == 1
        assert engine.contains_holed(holed, point) == PointLocation.INSIDE

    def test_normalize_fixes_winding_order(self):
        holed = PolygonWithHoles.from_tuples(
            outer_ring=[(0, 0), (0, 10), (10, 10), (10, 0)],
            inner_rings=[
                [(2, 2), (8, 2), (8, 8), (2, 8)],
            ],
        )
        assert holed.outer_ring.is_counterclockwise()
        for inner_ring in holed.inner_rings:
            assert inner_ring.is_clockwise()

    def test_contains_holed_auto_normalizes(self):
        outer = Polygon.from_tuples([(0, 0), (0, 10), (10, 10), (10, 0)])
        inner = Polygon.from_tuples([(2, 2), (8, 2), (8, 8), (2, 8)])
        assert outer.is_clockwise()
        assert inner.is_counterclockwise()
        holed = PolygonWithHoles(
            outer_ring=outer, inner_rings=[inner], validate_winding=False
        )
        engine = build_engine()
        point = Point(5, 5)
        result = engine.contains_holed(holed, point)
        assert result == PointLocation.OUTSIDE
        assert holed.outer_ring.is_counterclockwise()
        for inner_ring in holed.inner_rings:
            assert inner_ring.is_clockwise()
