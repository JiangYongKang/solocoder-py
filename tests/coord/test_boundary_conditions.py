import math

import pytest

from solocoder_py.coord import (
    BoundingBox,
    Coordinate,
    CoordValidator,
    CrossingDirection,
    NonFiniteCoordinateError,
    ValidationResult,
)

from .conftest import make_coordinate, make_validator


class TestBoundaryLatitude:
    def test_latitude_exactly_90(self):
        v = make_validator()
        c = make_coordinate(90.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is True

    def test_latitude_exactly_minus_90(self):
        v = make_validator()
        c = make_coordinate(-90.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is True

    def test_latitude_just_above_90(self):
        v = make_validator()
        c = make_coordinate(90.0001, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_latitude_just_below_minus_90(self):
        v = make_validator()
        c = make_coordinate(-90.0001, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False


class TestBoundaryLongitude:
    def test_longitude_exactly_180(self):
        v = make_validator()
        c = make_coordinate(0.0, 180.0)
        result = v.validate_coordinate(c)
        assert result.valid is True

    def test_longitude_exactly_minus_180(self):
        v = make_validator()
        c = make_coordinate(0.0, -180.0)
        result = v.validate_coordinate(c)
        assert result.valid is True

    def test_longitude_just_above_180(self):
        v = make_validator()
        c = make_coordinate(0.0, 180.0001)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_longitude_just_below_minus_180(self):
        v = make_validator()
        c = make_coordinate(0.0, -180.0001)
        result = v.validate_coordinate(c)
        assert result.valid is False


class TestAntimeridianBoundaryConditions:
    def test_lon_diff_exactly_180_no_crossing(self):
        v = make_validator()
        start = make_coordinate(0.0, -90.0)
        end = make_coordinate(0.0, 90.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False

    def test_lon_diff_just_above_180_crossing(self):
        v = make_validator()
        start = make_coordinate(0.0, 170.0)
        end = make_coordinate(0.0, -170.001)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True

    def test_near_antimeridian_no_false_positive(self):
        v = make_validator()
        start = make_coordinate(0.0, 179.0)
        end = make_coordinate(0.0, -179.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True

    def test_near_antimeridian_valid_short_line(self):
        v = make_validator()
        start = make_coordinate(0.0, 179.0)
        end = make_coordinate(0.0, 179.5)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False

    def test_long_arc_away_from_antimeridian(self):
        v = make_validator()
        start = make_coordinate(0.0, -10.0)
        end = make_coordinate(0.0, 170.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False

    def test_same_longitude_no_crossing(self):
        v = make_validator()
        start = make_coordinate(0.0, 45.0)
        end = make_coordinate(10.0, 45.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False

    def test_crossing_from_positive_side_eastward(self):
        v = make_validator()
        start = make_coordinate(10.0, 150.0)
        end = make_coordinate(20.0, -150.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.direction == CrossingDirection.EASTWARD
        assert result.crossing_point.longitude == 180.0

    def test_crossing_from_negative_side_westward(self):
        v = make_validator()
        start = make_coordinate(10.0, -150.0)
        end = make_coordinate(20.0, 150.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.direction == CrossingDirection.WESTWARD
        assert result.crossing_point.longitude == -180.0

    def test_lon_diff_exactly_180_east_to_west(self):
        v = make_validator()
        start = make_coordinate(0.0, 90.0)
        end = make_coordinate(0.0, -90.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False


class TestPolarBoundaryConditions:
    def test_latitude_exactly_90_polar(self):
        v = make_validator()
        c = make_coordinate(90.0, 45.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is True
        assert result.latitude_warning is None

    def test_latitude_exactly_minus_90_polar(self):
        v = make_validator()
        c = make_coordinate(-90.0, 45.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is True
        assert result.latitude_warning is None

    def test_latitude_89_999_near_polar(self):
        v = make_validator()
        c = make_coordinate(89.999, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is False
        assert result.is_near_polar is True

    def test_latitude_minus_89_999_near_polar(self):
        v = make_validator()
        c = make_coordinate(-89.999, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is False
        assert result.is_near_polar is True

    def test_latitude_90_001_exceeds_warning(self):
        v = make_validator()
        c = make_coordinate(90.001, 0.0)
        result = v.check_polar_singularity(c)
        assert result.latitude_warning is not None
        assert "exceeds" in result.latitude_warning

    def test_polar_different_longitudes_same_point(self):
        v = make_validator()
        for lon in [-180.0, -90.0, 0.0, 90.0, 180.0]:
            c = make_coordinate(90.0, lon)
            result = v.check_polar_singularity(c)
            assert result.is_polar is True
            assert result.latitude_warning is None


class TestBoundingBoxBoundary:
    def test_coordinate_on_bounds_edge(self):
        bounds = BoundingBox(min_lat=0.0, max_lat=90.0, min_lon=0.0, max_lon=180.0)
        c = make_coordinate(90.0, 180.0)
        assert bounds.contains(c) is True

    def test_coordinate_just_outside_bounds(self):
        bounds = BoundingBox(min_lat=0.0, max_lat=90.0, min_lon=0.0, max_lon=180.0)
        c = make_coordinate(90.001, 180.0)
        assert bounds.contains(c) is False


class TestValidationResultBool:
    def test_valid_result_is_truthy(self):
        result = ValidationResult(valid=True, invalid_coordinates=[])
        assert bool(result) is True

    def test_invalid_result_is_falsy(self):
        result = ValidationResult(
            valid=False,
            invalid_coordinates=[
                {"index": 0, "latitude": 91.0, "longitude": 0.0, "reason": "bad"}
            ],
        )
        assert bool(result) is False
