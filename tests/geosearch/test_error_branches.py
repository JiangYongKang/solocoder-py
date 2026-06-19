import math

import pytest

from solocoder_py.geosearch import (
    GeoPoint,
    GeoSearchEngine,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidRadiusError,
)


class TestInvalidLatitude:
    def test_latitude_too_large_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(91.0, 0.0)

    def test_latitude_too_small_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(-91.0, 0.0)

    def test_latitude_nan_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(math.nan, 0.0)

    def test_latitude_positive_infinity_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(math.inf, 0.0)

    def test_latitude_negative_infinity_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(-math.inf, 0.0)

    def test_latitude_non_numeric_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate("90", 0.0)

    def test_latitude_none_raises(self):
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine._validate_coordinate(None, 0.0)

    def test_center_latitude_invalid_raises_on_search(self, beijing_center):
        engine = GeoSearchEngine()
        invalid_center = GeoPoint(91.0, 0.0)
        with pytest.raises(InvalidLatitudeError):
            engine.search(invalid_center, radius_km=10.0)

    def test_add_candidate_invalid_latitude_raises(self):
        engine = GeoSearchEngine()
        invalid_point = GeoPoint(91.0, 0.0)
        with pytest.raises(InvalidLatitudeError):
            engine.add_candidate(invalid_point)

    def test_init_with_invalid_latitude_raises(self):
        invalid_points = [GeoPoint(91.0, 0.0)]
        with pytest.raises(InvalidLatitudeError):
            GeoSearchEngine(candidates=invalid_points)


class TestInvalidLongitude:
    def test_longitude_too_large_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, 181.0)

    def test_longitude_too_small_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, -181.0)

    def test_longitude_nan_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, math.nan)

    def test_longitude_positive_infinity_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, math.inf)

    def test_longitude_negative_infinity_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, -math.inf)

    def test_longitude_non_numeric_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, "180")

    def test_longitude_none_raises(self):
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine._validate_coordinate(0.0, None)

    def test_center_longitude_invalid_raises_on_search(self):
        engine = GeoSearchEngine()
        invalid_center = GeoPoint(0.0, 181.0)
        with pytest.raises(InvalidLongitudeError):
            engine.search(invalid_center, radius_km=10.0)

    def test_add_candidate_invalid_longitude_raises(self):
        engine = GeoSearchEngine()
        invalid_point = GeoPoint(0.0, 181.0)
        with pytest.raises(InvalidLongitudeError):
            engine.add_candidate(invalid_point)

    def test_init_with_invalid_longitude_raises(self):
        invalid_points = [GeoPoint(0.0, 181.0)]
        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine(candidates=invalid_points)


class TestValidCoordinateBoundaries:
    def test_latitude_90_is_valid(self):
        GeoSearchEngine._validate_coordinate(90.0, 0.0)

    def test_latitude_minus_90_is_valid(self):
        GeoSearchEngine._validate_coordinate(-90.0, 0.0)

    def test_longitude_180_is_valid(self):
        GeoSearchEngine._validate_coordinate(0.0, 180.0)

    def test_longitude_minus_180_is_valid(self):
        GeoSearchEngine._validate_coordinate(0.0, -180.0)

    def test_zero_coordinates_are_valid(self):
        GeoSearchEngine._validate_coordinate(0.0, 0.0)


class TestNegativeRadius:
    def test_negative_radius_raises(self, beijing_center):
        engine = GeoSearchEngine()
        with pytest.raises(InvalidRadiusError):
            engine.search(beijing_center, radius_km=-1.0)

    def test_negative_radius_with_limit_raises(self, beijing_center):
        engine = GeoSearchEngine()
        with pytest.raises(InvalidRadiusError):
            engine.search(beijing_center, radius_km=-5.0, limit=10)

    def test_negative_limit_raises(self, beijing_center):
        engine = GeoSearchEngine()
        with pytest.raises(InvalidRadiusError):
            engine.search(beijing_center, radius_km=10.0, limit=-1)

    def test_zero_radius_is_valid(self, beijing_center):
        engine = GeoSearchEngine()
        response = engine.search(beijing_center, radius_km=0.0)
        assert response is not None

    def test_zero_limit_is_valid(self, beijing_center):
        engine = GeoSearchEngine(candidates=[beijing_center])
        response = engine.search(beijing_center, radius_km=10.0, limit=0)
        assert response.total_count == 0


class TestInvalidCandidatesSkippedDuringSearch:
    def test_search_skips_invalid_latitude_points(self, beijing_center):
        valid_point = GeoPoint(39.9043, 116.4074)

        class MockInvalidLatGeoPoint:
            @property
            def latitude(self):
                return 91.0

            @property
            def longitude(self):
                return 0.0

        engine = GeoSearchEngine(candidates=[valid_point])
        engine._candidates.append(MockInvalidLatGeoPoint())

        assert engine.candidate_count == 2

        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 1
        assert response.results[0].point.latitude == valid_point.latitude

    def test_search_skips_invalid_longitude_points(self, beijing_center):
        valid_point = GeoPoint(39.9043, 116.4074)

        class MockInvalidLngGeoPoint:
            @property
            def latitude(self):
                return 0.0

            @property
            def longitude(self):
                return 181.0

        engine = GeoSearchEngine(candidates=[valid_point])
        engine._candidates.append(MockInvalidLngGeoPoint())

        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 1

    def test_search_skips_nan_latitude(self, beijing_center):
        valid_point = GeoPoint(39.9043, 116.4074)

        class MockNaNLatGeoPoint:
            @property
            def latitude(self):
                return math.nan

            @property
            def longitude(self):
                return 0.0

        engine = GeoSearchEngine(candidates=[valid_point])
        engine._candidates.append(MockNaNLatGeoPoint())

        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 1

    def test_search_skips_multiple_invalid_points(self, beijing_center):
        valid_points = [
            GeoPoint(39.9043, 116.4074),
            GeoPoint(39.9044, 116.4074),
        ]

        class MockInvalidGeoPoint:
            def __init__(self, bad_lat=True):
                self._bad_lat = bad_lat

            @property
            def latitude(self):
                return 91.0 if self._bad_lat else 0.0

            @property
            def longitude(self):
                return 0.0 if self._bad_lat else 181.0

        engine = GeoSearchEngine(candidates=valid_points)
        engine._candidates.append(MockInvalidGeoPoint(bad_lat=True))
        engine._candidates.append(MockInvalidGeoPoint(bad_lat=False))
        engine._candidates.append(MockInvalidGeoPoint(bad_lat=True))

        assert engine.candidate_count == 5

        response = engine.search(beijing_center, radius_km=10.0)

        assert response.total_count == 2

    def test_all_candidates_invalid_returns_empty(self, beijing_center):
        class MockInvalidGeoPoint:
            @property
            def latitude(self):
                return 91.0

            @property
            def longitude(self):
                return 0.0

        engine = GeoSearchEngine()
        engine._candidates.append(MockInvalidGeoPoint())
        engine._candidates.append(MockInvalidGeoPoint())

        response = engine.search(beijing_center, radius_km=100.0)

        assert response.total_count == 0
        assert response.filtered_count == 0
        assert len(response.results) == 0

    def test_add_candidates_rejects_entire_list_if_any_invalid(self):
        points = [
            GeoPoint(0.0, 0.0),
            GeoPoint(91.0, 0.0),
            GeoPoint(1.0, 1.0),
        ]

        engine = GeoSearchEngine()
        with pytest.raises(InvalidLatitudeError):
            engine.add_candidates(points)

        assert engine.candidate_count == 0

    def test_init_rejects_entire_list_if_any_invalid(self):
        points = [
            GeoPoint(0.0, 0.0),
            GeoPoint(0.0, 181.0),
        ]

        with pytest.raises(InvalidLongitudeError):
            GeoSearchEngine(candidates=points)


class TestIntegerCoordinates:
    def test_integer_latitude_is_valid(self):
        GeoSearchEngine._validate_coordinate(90, 0)

    def test_integer_coordinates_in_search(self, beijing_center):
        point = GeoPoint(40, 116)
        engine = GeoSearchEngine(candidates=[point])
        response = engine.search(beijing_center, radius_km=100.0)
        assert response.total_count == 1
