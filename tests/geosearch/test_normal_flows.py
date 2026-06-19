import math

import pytest

from solocoder_py.geosearch import (
    GeoPoint,
    GeoSearchEngine,
)


class TestEngineInit:
    def test_default_init_empty(self):
        engine = GeoSearchEngine()
        assert engine.candidate_count == 0

    def test_init_with_candidates(self, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        assert engine.candidate_count == len(candidates_around_beijing)

    def test_add_single_candidate(self):
        engine = GeoSearchEngine()
        engine.add_candidate(GeoPoint(39.9042, 116.4074))
        assert engine.candidate_count == 1

    def test_add_multiple_candidates(self):
        engine = GeoSearchEngine()
        points = [GeoPoint(39.9, 116.4), GeoPoint(39.8, 116.3)]
        engine.add_candidates(points)
        assert engine.candidate_count == 2

    def test_clear_candidates(self, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        assert engine.candidate_count > 0
        engine.clear_candidates()
        assert engine.candidate_count == 0


class TestBoundingBoxFiltering:
    def test_bbox_filters_points_outside_radius(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        radius_km = 5.0
        response = engine.search(beijing_center, radius_km)

        shanghai = GeoPoint(31.2304, 121.4737)
        shanghai_in_results = any(
            r.point.latitude == shanghai.latitude and r.point.longitude == shanghai.longitude
            for r in response.results
        )
        assert not shanghai_in_results

    def test_bbox_includes_points_near_center(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        radius_km = 20.0
        response = engine.search(beijing_center, radius_km)

        assert len(response.results) >= 5
        for result in response.results:
            assert result.distance_km <= radius_km

    def test_filtered_count_greater_than_final_count(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        radius_km = 10.0
        response = engine.search(beijing_center, radius_km)

        assert response.filtered_count >= response.total_count


class TestHaversineDistanceSorting:
    def test_results_sorted_by_distance_ascending(self, beijing_center):
        far_point = GeoPoint(39.9542, 116.4074)
        near_point = GeoPoint(39.9142, 116.4074)
        center_point = GeoPoint(39.9042, 116.4074)

        candidates = [far_point, near_point, center_point]
        engine = GeoSearchEngine(candidates=candidates)

        response = engine.search(beijing_center, radius_km=50.0)

        assert len(response.results) == 3
        assert response.results[0].distance_km <= response.results[1].distance_km
        assert response.results[1].distance_km <= response.results[2].distance_km

        assert response.results[0].point.latitude == center_point.latitude
        assert response.results[0].point.longitude == center_point.longitude

    def test_haversine_known_distance(self):
        new_york = GeoPoint(40.7128, -74.0060)
        london = GeoPoint(51.5074, -0.1278)

        engine = GeoSearchEngine(candidates=[london])
        response = engine.search(new_york, radius_km=6000.0)

        assert len(response.results) == 1
        distance = response.results[0].distance_km
        assert 5560 <= distance <= 5590

    def test_zero_distance_for_same_point(self, beijing_center):
        engine = GeoSearchEngine(candidates=[beijing_center])
        response = engine.search(beijing_center, radius_km=1.0)

        assert len(response.results) == 1
        assert abs(response.results[0].distance_km) < 1e-9

    def test_symmetric_distance(self):
        p1 = GeoPoint(39.9042, 116.4074)
        p2 = GeoPoint(31.2304, 121.4737)

        engine1 = GeoSearchEngine(candidates=[p2])
        response1 = engine1.search(p1, radius_km=2000.0)

        engine2 = GeoSearchEngine(candidates=[p1])
        response2 = engine2.search(p2, radius_km=2000.0)

        assert abs(response1.results[0].distance_km - response2.results[0].distance_km) < 1e-9

    def test_haversine_distance_accuracy(self):
        paris = GeoPoint(48.8566, 2.3522)
        berlin = GeoPoint(52.5200, 13.4050)

        engine = GeoSearchEngine(candidates=[berlin])
        response = engine.search(paris, radius_km=1000.0)

        distance = response.results[0].distance_km
        assert 870 <= distance <= 880


class TestResultLimiting:
    def test_limit_truncates_results(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        limit = 3
        response = engine.search(beijing_center, radius_km=50.0, limit=limit)

        assert response.total_count == limit
        assert len(response.results) == limit

    def test_limit_larger_than_available(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        limit = 100
        response = engine.search(beijing_center, radius_km=10.0, limit=limit)

        assert response.total_count < limit
        assert len(response.results) == response.total_count

    def test_limit_zero_returns_empty(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        response = engine.search(beijing_center, radius_km=50.0, limit=0)

        assert response.total_count == 0
        assert len(response.results) == 0

    def test_limit_none_returns_all(self, beijing_center, candidates_around_beijing):
        engine = GeoSearchEngine(candidates=candidates_around_beijing)
        response = engine.search(beijing_center, radius_km=100.0, limit=None)
        response_no_limit = engine.search(beijing_center, radius_km=100.0)

        assert response.total_count == response_no_limit.total_count
        assert len(response.results) == len(response_no_limit.results)


class TestBoundingBoxEdges:
    def test_point_on_north_edge_included(self, beijing_center):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        north_edge = GeoPoint(latitude=1.0, longitude=0.0)
        inside = GeoPoint(latitude=0.5, longitude=0.0)
        outside = GeoPoint(latitude=1.1, longitude=0.0)

        engine = GeoSearchEngine(candidates=[north_edge, inside, outside])
        response = engine.search(center, radius_km)

        result_points = [(r.point.latitude, r.point.longitude) for r in response.results]
        assert (1.0, 0.0) in result_points
        assert (0.5, 0.0) in result_points
        assert (1.1, 0.0) not in result_points

    def test_point_on_south_edge_included(self, beijing_center):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        south_edge = GeoPoint(latitude=-1.0, longitude=0.0)

        engine = GeoSearchEngine(candidates=[south_edge])
        response = engine.search(center, radius_km)

        result_points = [(r.point.latitude, r.point.longitude) for r in response.results]
        assert (-1.0, 0.0) in result_points

    def test_point_on_east_edge_included(self):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        east_edge = GeoPoint(latitude=0.0, longitude=1.0)

        engine = GeoSearchEngine(candidates=[east_edge])
        response = engine.search(center, radius_km)

        result_points = [(r.point.latitude, r.point.longitude) for r in response.results]
        assert (0.0, 1.0) in result_points

    def test_point_on_west_edge_included(self):
        center = GeoPoint(0.0, 0.0)
        radius_km = 111.32

        west_edge = GeoPoint(latitude=0.0, longitude=-1.0)

        engine = GeoSearchEngine(candidates=[west_edge])
        response = engine.search(center, radius_km)

        result_points = [(r.point.latitude, r.point.longitude) for r in response.results]
        assert (0.0, -1.0) in result_points

    def test_bbox_corners_are_approximate(self):
        center = GeoPoint(0.0, 0.0)
        radius_km = 100.0

        lat_offset = radius_km / 111.32
        lng_offset = radius_km / (111.32 * math.cos(math.radians(center.latitude)))

        corner = GeoPoint(
            latitude=center.latitude + lat_offset,
            longitude=center.longitude + lng_offset,
        )

        engine = GeoSearchEngine(candidates=[corner])
        response = engine.search(center, radius_km)

        corner_distance = engine._haversine_distance(center, corner)
        assert corner_distance > radius_km

        if corner_distance <= radius_km:
            assert len(response.results) == 1
        else:
            assert len(response.results) == 0


class TestUniformDistribution:
    def test_candidates_at_varying_distances(self, beijing_center):
        distances_km = [1, 3, 5, 10, 15, 20, 30]
        candidates = []
        for i, d in enumerate(distances_km):
            lat_offset = d / 111.32
            candidates.append(
                GeoPoint(
                    latitude=beijing_center.latitude + lat_offset * math.cos(i * 0.5),
                    longitude=beijing_center.longitude + lat_offset * math.sin(i * 0.5),
                )
            )

        engine = GeoSearchEngine(candidates=candidates)
        response = engine.search(beijing_center, radius_km=15.0)

        assert response.total_count == 5
        for i, result in enumerate(response.results[:-1]):
            assert result.distance_km <= response.results[i + 1].distance_km
            assert result.distance_km <= 15.0
