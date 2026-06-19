import pytest

from solocoder_py.coord import (
    AntimeridianCrossing,
    BoundingBox,
    Coordinate,
    CoordValidator,
    CrossingDirection,
    InvalidCoordinate,
    PolarCheckResult,
    ValidationResult,
)

from .conftest import make_coordinate, make_validator, make_bounds


class TestValidateSingleCoordinate:
    def test_valid_coordinate_passes(self):
        v = make_validator()
        c = make_coordinate(45.0, 90.0)
        result = v.validate_coordinate(c)
        assert result.valid is True
        assert result.invalid_coordinates == []

    def test_zero_zero_passes(self):
        v = make_validator()
        c = make_coordinate(0.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is True

    def test_latitude_out_of_range_high(self):
        v = make_validator()
        c = make_coordinate(91.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 1
        assert "latitude" in result.invalid_coordinates[0].reason

    def test_latitude_out_of_range_low(self):
        v = make_validator()
        c = make_coordinate(-91.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 1

    def test_longitude_out_of_range_high(self):
        v = make_validator()
        c = make_coordinate(0.0, 181.0)
        result = v.validate_coordinate(c)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 1
        assert "longitude" in result.invalid_coordinates[0].reason

    def test_longitude_out_of_range_low(self):
        v = make_validator()
        c = make_coordinate(0.0, -181.0)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_both_out_of_range(self):
        v = make_validator()
        c = make_coordinate(91.0, 181.0)
        result = v.validate_coordinate(c)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 1
        assert "latitude" in result.invalid_coordinates[0].reason
        assert "longitude" in result.invalid_coordinates[0].reason

    def test_index_is_set(self):
        v = make_validator()
        c = make_coordinate(91.0, 0.0)
        result = v.validate_coordinate(c, index=5)
        assert result.invalid_coordinates[0].index == 5

    def test_index_none_by_default(self):
        v = make_validator()
        c = make_coordinate(91.0, 0.0)
        result = v.validate_coordinate(c)
        assert result.invalid_coordinates[0].index is None


class TestValidateCoordinateList:
    def test_all_valid_passes(self):
        v = make_validator()
        coords = [
            make_coordinate(0.0, 0.0),
            make_coordinate(45.0, 90.0),
            make_coordinate(-45.0, -90.0),
        ]
        result = v.validate_coordinates(coords)
        assert result.valid is True
        assert result.invalid_coordinates == []

    def test_returns_all_invalid_with_indices(self):
        v = make_validator()
        coords = [
            make_coordinate(0.0, 0.0),
            make_coordinate(91.0, 0.0),
            make_coordinate(0.0, 181.0),
            make_coordinate(-91.0, -181.0),
        ]
        result = v.validate_coordinates(coords)
        assert result.valid is False
        indices = [inv.index for inv in result.invalid_coordinates]
        assert 1 in indices
        assert 2 in indices
        assert 3 in indices
        assert 0 not in indices

    def test_empty_list_passes(self):
        v = make_validator()
        result = v.validate_coordinates([])
        assert result.valid is True
        assert result.invalid_coordinates == []

    def test_single_invalid_in_list(self):
        v = make_validator()
        coords = [make_coordinate(0.0, 0.0), make_coordinate(0.0, 200.0)]
        result = v.validate_coordinates(coords)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 1
        assert result.invalid_coordinates[0].index == 1


class TestValidateAgainstBounds:
    def test_coordinate_within_bounds(self):
        v = make_validator()
        c = make_coordinate(45.0, 90.0)
        bounds = make_bounds(min_lat=0.0, max_lat=60.0, min_lon=0.0, max_lon=100.0)
        result = v.validate_against_bounds(c, bounds)
        assert result.valid is True

    def test_coordinate_outside_bounds(self):
        v = make_validator()
        c = make_coordinate(70.0, 90.0)
        bounds = make_bounds(min_lat=0.0, max_lat=60.0, min_lon=0.0, max_lon=100.0)
        result = v.validate_against_bounds(c, bounds)
        assert result.valid is False

    def test_list_against_bounds(self):
        v = make_validator()
        coords = [
            make_coordinate(30.0, 50.0),
            make_coordinate(70.0, 50.0),
            make_coordinate(30.0, 150.0),
        ]
        bounds = make_bounds(min_lat=0.0, max_lat=60.0, min_lon=0.0, max_lon=100.0)
        result = v.validate_list_against_bounds(coords, bounds)
        assert result.valid is False
        assert len(result.invalid_coordinates) == 2


class TestAntimeridianCrossing:
    def test_no_crossing_normal_line(self):
        v = make_validator()
        start = make_coordinate(0.0, 10.0)
        end = make_coordinate(0.0, 20.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is False
        assert result.direction is None
        assert result.crossing_point is None

    def test_eastward_crossing(self):
        v = make_validator()
        start = make_coordinate(0.0, 170.0)
        end = make_coordinate(0.0, -170.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.direction == CrossingDirection.EASTWARD
        assert result.crossing_point is not None
        assert result.crossing_point.longitude == 180.0

    def test_westward_crossing(self):
        v = make_validator()
        start = make_coordinate(0.0, -170.0)
        end = make_coordinate(0.0, 170.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.direction == CrossingDirection.WESTWARD
        assert result.crossing_point is not None
        assert result.crossing_point.longitude == -180.0

    def test_crossing_point_latitude_interpolation(self):
        v = make_validator()
        start = make_coordinate(10.0, 170.0)
        end = make_coordinate(30.0, -170.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.crossing_point is not None
        assert 10.0 < result.crossing_point.latitude < 30.0

    def test_segment_index_set(self):
        v = make_validator()
        start = make_coordinate(0.0, 170.0)
        end = make_coordinate(0.0, -170.0)
        result = v.check_antimeridian_crossing(start, end, segment_index=3)
        assert result.segment_index == 3

    def test_crossings_for_route(self):
        v = make_validator()
        coords = [
            make_coordinate(0.0, 10.0),
            make_coordinate(0.0, 170.0),
            make_coordinate(0.0, -170.0),
            make_coordinate(0.0, 170.0),
        ]
        results = v.check_antimeridian_crossings(coords)
        assert len(results) == 3
        assert results[0].crosses is False
        assert results[1].crosses is True
        assert results[2].crosses is True

    def test_crossings_single_point_returns_empty(self):
        v = make_validator()
        results = v.check_antimeridian_crossings([make_coordinate(0.0, 0.0)])
        assert results == []

    def test_crossings_empty_list_returns_empty(self):
        v = make_validator()
        results = v.check_antimeridian_crossings([])
        assert results == []


class TestPolarSingularity:
    def test_north_pole_is_polar(self):
        v = make_validator()
        c = make_coordinate(90.0, 45.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is True
        assert result.is_near_polar is True
        assert result.latitude_warning is None

    def test_south_pole_is_polar(self):
        v = make_validator()
        c = make_coordinate(-90.0, 120.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is True
        assert result.is_near_polar is True
        assert result.latitude_warning is None

    def test_near_pole_not_exactly_polar(self):
        v = make_validator()
        c = make_coordinate(89.999, 45.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is False
        assert result.is_near_polar is True
        assert result.latitude_warning is not None
        assert "near the pole" in result.latitude_warning

    def test_normal_latitude_not_polar(self):
        v = make_validator()
        c = make_coordinate(45.0, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is False
        assert result.is_near_polar is False
        assert result.latitude_warning is None

    def test_latitude_exceeds_pole(self):
        v = make_validator()
        c = make_coordinate(90.001, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_polar is False
        assert result.is_near_polar is False
        assert result.latitude_warning is not None
        assert "exceeds" in result.latitude_warning

    def test_polar_longitude_not_flagged_as_anomaly(self):
        v = make_validator()
        c1 = make_coordinate(90.0, 0.0)
        c2 = make_coordinate(90.0, 180.0)
        r1 = v.check_polar_singularity(c1)
        r2 = v.check_polar_singularity(c2)
        assert r1.is_polar is True
        assert r2.is_polar is True
        assert r1.latitude_warning is None
        assert r2.latitude_warning is None

    def test_near_polar_longitude_changes_not_anomaly(self):
        v = make_validator()
        c = make_coordinate(89.999, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_near_polar is True
        assert result.latitude_warning is not None
        assert "near the pole" in result.latitude_warning

    def test_polar_check_list(self):
        v = make_validator()
        coords = [
            make_coordinate(90.0, 0.0),
            make_coordinate(45.0, 0.0),
            make_coordinate(89.999, 0.0),
        ]
        results = v.check_polar_singularities(coords)
        assert len(results) == 3
        assert results[0].is_polar is True
        assert results[1].is_polar is False
        assert results[2].is_near_polar is True

    def test_polar_check_index_set_in_list(self):
        v = make_validator()
        coords = [
            make_coordinate(90.0, 0.0),
            make_coordinate(45.0, 0.0),
        ]
        results = v.check_polar_singularities(coords)
        assert results[0].index == 0
        assert results[1].index == 1

    def test_polar_check_single_with_index(self):
        v = make_validator()
        c = make_coordinate(90.0, 0.0)
        result = v.check_polar_singularity(c, index=7)
        assert result.index == 7

    def test_polar_check_single_default_index_none(self):
        v = make_validator()
        c = make_coordinate(90.0, 0.0)
        result = v.check_polar_singularity(c)
        assert result.index is None


class TestValidateWithPolarAwareness:
    def test_polar_coords_valid(self):
        v = make_validator()
        coords = [make_coordinate(90.0, 45.0), make_coordinate(-90.0, 120.0)]
        result = v.validate_with_polar_awareness(coords)
        assert result.valid is True

    def test_exceeds_pole_flagged(self):
        v = make_validator()
        coords = [make_coordinate(90.001, 0.0)]
        result = v.validate_with_polar_awareness(coords)
        assert result.valid is False
        assert any("exceeds" in inv.reason for inv in result.invalid_coordinates)

    def test_near_polar_coords_not_flagged_as_invalid(self):
        v = make_validator()
        coords = [make_coordinate(89.999, 45.0), make_coordinate(-89.999, 120.0)]
        result = v.validate_with_polar_awareness(coords)
        assert result.valid is True
        assert len(result.invalid_coordinates) == 0

    def test_mixed_coords_only_exceeds_flagged(self):
        v = make_validator()
        coords = [
            make_coordinate(89.999, 0.0),
            make_coordinate(90.001, 0.0),
            make_coordinate(45.0, 0.0),
        ]
        result = v.validate_with_polar_awareness(coords)
        assert result.valid is False
        indices = [inv.index for inv in result.invalid_coordinates]
        assert 1 in indices
        assert 0 not in indices
        assert 2 not in indices
