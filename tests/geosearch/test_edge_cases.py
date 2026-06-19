import math

import pytest

from solocoder_py.geosearch import (
    GeoPoint,
    GeoSearchEngine,
)


class TestEmptyCandidateList:
    def test_search_empty_candidates(self, beijing_center):
        engine = GeoSearchEngine()
        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 0
        assert response.filtered_count == 0
        assert len(response.results) == 0

    def test_search_after_clear(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        engine.clear_candidates()
        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 0
        assert len(response.results) == 0


class TestBoundingBoxBoundary:
    def test_exactly_on_bbox_boundary_included(self):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        lat_offset = radius_km / 111.32
        lng_offset = radius_km / 111.32

        boundary_points = [
            GeoPoint(latitude=lat_offset, longitude=0.0),
            GeoPoint(latitude=-lat_offset, longitude=0.0),
            GeoPoint(latitude=0.0, longitude=lng_offset),
            GeoPoint(latitude=0.0, longitude=-lng_offset),
        ]

        engine = GeoSearchEngine(candidates=boundary_points)
        response = engine.search(center, radius_km)

        assert response.total_count == len(boundary_points)

    def test_bbox_near_pole_handles_latitude_clamping(self):
        center = GeoPoint(89.5, 0.0)
        radius_km = 111.32

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        assert bbox.max_lat <= 90.0
        assert bbox.min_lat >= -90.0

    def test_bbox_near_south_pole(self):
        center = GeoPoint(-89.5, 0.0)
        radius_km = 111.32

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        assert bbox.max_lat <= 90.0
        assert bbox.min_lat >= -90.0


class TestZeroRadius:
    def test_zero_radius_returns_only_exact_match(self, beijing_center):
        exact_match = GeoPoint(39.9042, 116.4074)
        near_point = GeoPoint(39.9043, 116.4074)

        engine = GeoSearchEngine(candidates=[exact_match, near_point])
        response = engine.search(beijing_center, radius_km=0.0)

        assert response.total_count == 1
        assert response.results[0].point.latitude == exact_match.latitude
        assert response.results[0].point.longitude == exact_match.longitude
        assert abs(response.results[0].distance_km) < 1e-9

    def test_zero_radius_no_match(self, beijing_center):
        near_point = GeoPoint(39.9043, 116.4074)

        engine = GeoSearchEngine(candidates=[near_point])
        response = engine.search(beijing_center, radius_km=0.0)

        assert response.total_count == 0

    def test_zero_radius_multiple_exact_matches(self, beijing_center):
        duplicates = [
            GeoPoint(39.9042, 116.4074),
            GeoPoint(39.9042, 116.4074),
            GeoPoint(39.9043, 116.4074),
        ]

        engine = GeoSearchEngine(candidates=duplicates)
        response = engine.search(beijing_center, radius_km=0.0)

        assert response.total_count == 2


class TestVeryLargeRadius:
    def test_large_radius_covers_globe(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        earth_circumference = 40075.0
        radius_km = earth_circumference / 2

        response = engine.search(beijing_center, radius_km)

        assert response.total_count == len(candidates_around_beijing)

    def test_large_radius_at_equator(self, equator_center):
        candidates = [
            GeoPoint(0.0, 179.0),
            GeoPoint(0.0, -179.0),
            GeoPoint(89.0, 0.0),
            GeoPoint(-89.0, 0.0),
        ]

        engine = GeoSearchEngine(candidates=candidates)
        response = engine.search(equator_center, radius_km=20038.0)

        assert response.total_count == len(candidates)


class TestLatitudeDependentLongitudeOffset:
    def test_equator_lng_offset_is_km_per_degree(self):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        lng_span = bbox.max_lng - bbox.min_lng
        expected_lng_offset = radius_km / 111.32
        assert abs(lng_span - 2 * expected_lng_offset) < 1e-9

    def test_high_latitude_lng_offset_is_larger(self):
        equator = GeoPoint(0.0, 0.0)
        high_lat = GeoPoint(60.0, 0.0)
        radius_km = 100.0

        engine = GeoSearchEngine()
        bbox_equator = engine._build_bounding_box(equator, radius_km)
        bbox_high_lat = engine._build_bounding_box(high_lat, radius_km)

        lng_span_equator = bbox_equator.max_lng - bbox_equator.min_lng
        lng_span_high_lat = bbox_high_lat.max_lng - bbox_high_lat.min_lng

        assert lng_span_high_lat > lng_span_equator
        expected_ratio = 1.0 / math.cos(math.radians(60.0))
        actual_ratio = lng_span_high_lat / lng_span_equator
        assert abs(actual_ratio - expected_ratio) < 0.01

    def test_near_pole_lng_offset_is_very_large(self):
        center = GeoPoint(89.9, 0.0)
        radius_km = 1.0

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        lng_span = bbox.max_lng - bbox.min_lng
        assert lng_span > 10.0

    def test_near_pole_90_degrees(self):
        center = GeoPoint(90.0, 0.0)
        radius_km = 1.0

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        assert bbox.min_lng == bbox.max_lng - 360.0 or bbox.min_lng <= bbox.max_lng


class TestCrossAntimeridian:
    def test_bbox_crosses_antimeridian_positive_to_negative(self):
        center = GeoPoint(0.0, 179.5)
        radius_km = 111.32 * 2

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        assert bbox.min_lng > bbox.max_lng

    def test_point_on_either_side_of_antimeridian_included(self):
        center = GeoPoint(0.0, 179.5)
        radius_km = 111.32 * 2

        west_of_am = GeoPoint(0.0, 179.0)
        east_of_am = GeoPoint(0.0, -179.0)
        outside = GeoPoint(0.0, 170.0)

        engine = GeoSearchEngine(candidates=[west_of_am, east_of_am, outside])
        response = engine.search(center, radius_km)

        result_lngs = [r.point.longitude for r in response.results]
        assert 179.0 in result_lngs
        assert -179.0 in result_lngs
        assert 170.0 not in result_lngs

    def test_bbox_crosses_antimeridian_negative_to_positive(self):
        center = GeoPoint(0.0, -179.5)
        radius_km = 111.32 * 2

        engine = GeoSearchEngine()
        bbox = engine._build_bounding_box(center, radius_km)

        assert bbox.min_lng > bbox.max_lng

    def test_antimeridian_cross_with_northern_points(self):
        center = GeoPoint(45.0, 179.5)
        radius_km = 200.0

        p1 = GeoPoint(45.0, 179.8)
        p2 = GeoPoint(45.0, -179.8)
        p3 = GeoPoint(45.0, 179.2)

        engine = GeoSearchEngine(candidates=[p1, p2, p3])
        response = engine.search(center, radius_km)

        assert response.total_count >= 2
        lngs = [r.point.longitude for r in response.results]
        assert 179.8 in lngs
        assert -179.8 in lngs

    def test_antimeridian_exact_boundary(self):
        center = GeoPoint(0.0, 180.0)
        radius_km = 111.32

        exact_am_west = GeoPoint(0.0, 180.0)
        exact_am_east = GeoPoint(0.0, -180.0)

        engine = GeoSearchEngine(candidates=[exact_am_west, exact_am_east])
        response = engine.search(center, radius_km)

        result_lngs = [r.point.longitude for r in response.results]
        assert 180.0 in result_lngs
        assert -180.0 in result_lngs


class TestResultStructure:
    def test_response_contains_correct_fields(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        response = engine.search(beijing_center, radius_km=10.0)

        assert hasattr(response, 'results')
        assert hasattr(response, 'total_count')
        assert hasattr(response, 'filtered_count')
        assert hasattr(response, 'returned_count')

        assert isinstance(response.results, list)
        assert isinstance(response.total_count, int)
        assert isinstance(response.filtered_count, int)
        assert isinstance(response.returned_count, int)
        assert response.total_count >= response.returned_count

    def test_each_result_has_point_and_distance(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        response = engine.search(beijing_center, radius_km=10.0)

        for result in response.results:
            assert hasattr(result, 'point')
            assert hasattr(result, 'distance_km')
            assert hasattr(result.point, 'latitude')
            assert hasattr(result.point, 'longitude')
            assert isinstance(result.distance_km, float)

    def test_geopoint_is_frozen(self):
        point = GeoPoint(39.9042, 116.4074)
        with pytest.raises(Exception):
            point.latitude = 40.0


class TestDuplicatePoints:
    def test_duplicate_points_both_returned(self, beijing_center):
        p1 = GeoPoint(39.9043, 116.4074)
        p2 = GeoPoint(39.9043, 116.4074)

        engine = GeoSearchEngine(candidates=[p1, p2])
        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 2
        assert abs(response.results[0].distance_km - response.results[1].distance_km) < 1e-9

    def test_duplicate_with_limit(self, beijing_center):
        duplicates = [
            GeoPoint(39.9043, 116.4074) for _ in range(5)
        ]
        engine = GeoSearchEngine(candidates=duplicates)
        response = engine.search(beijing_center, radius_km=10.0, limit=3)

        assert response.total_count == 5
        assert response.returned_count == 3
        assert len(response.results) == 3
