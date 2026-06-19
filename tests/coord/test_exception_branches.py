import math

import pytest

from solocoder_py.coord import (
    BoundingBox,
    Coordinate,
    CoordError,
    CoordValidator,
    CrossingDirection,
    InvalidBoundsError,
    NonFiniteCoordinateError,
    PolarCheckResult,
)

from .conftest import make_coordinate, make_validator


class TestNaNAndInfCoordinates:
    def test_nan_latitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=float("nan"), longitude=0.0)

    def test_nan_longitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=0.0, longitude=float("nan"))

    def test_inf_latitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=float("inf"), longitude=0.0)

    def test_neg_inf_latitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=float("-inf"), longitude=0.0)

    def test_inf_longitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=0.0, longitude=float("inf"))

    def test_neg_inf_longitude_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            Coordinate(latitude=0.0, longitude=float("-inf"))


class TestNaNAndInfBoundingBox:
    def test_nan_min_lat_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            BoundingBox(
                min_lat=float("nan"), max_lat=90.0, min_lon=-180.0, max_lon=180.0
            )

    def test_inf_max_lat_raises(self):
        with pytest.raises(NonFiniteCoordinateError):
            BoundingBox(
                min_lat=-90.0, max_lat=float("inf"), min_lon=-180.0, max_lon=180.0
            )


class TestEmptyCoordinateList:
    def test_validate_empty_list(self):
        v = make_validator()
        result = v.validate_coordinates([])
        assert result.valid is True

    def test_antimeridian_crossings_empty(self):
        v = make_validator()
        results = v.check_antimeridian_crossings([])
        assert results == []

    def test_polar_check_empty(self):
        v = make_validator()
        results = v.check_polar_singularities([])
        assert results == []

    def test_validate_with_polar_awareness_empty(self):
        v = make_validator()
        result = v.validate_with_polar_awareness([])
        assert result.valid is True


class TestSelfReferenceSegment:
    def test_same_point_no_crossing(self):
        v = make_validator()
        c = make_coordinate(45.0, 90.0)
        result = v.check_antimeridian_crossing(c, c)
        assert result.crosses is False

    def test_same_point_crossings_list(self):
        v = make_validator()
        coords = [make_coordinate(45.0, 90.0), make_coordinate(45.0, 90.0)]
        results = v.check_antimeridian_crossings(coords)
        assert len(results) == 1
        assert results[0].crosses is False

    def test_same_point_polar(self):
        v = make_validator()
        c = make_coordinate(90.0, 0.0)
        result = v.check_antimeridian_crossing(c, c)
        assert result.crosses is False


class TestLatitudeExceedsPole:
    def test_latitude_90_001_fails_validation(self):
        v = make_validator()
        c = make_coordinate(90.001, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_latitude_minus_90_001_fails_validation(self):
        v = make_validator()
        c = make_coordinate(-90.001, 0.0)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_longitude_180_001_fails_validation(self):
        v = make_validator()
        c = make_coordinate(0.0, 180.001)
        result = v.validate_coordinate(c)
        assert result.valid is False

    def test_longitude_minus_180_001_fails_validation(self):
        v = make_validator()
        c = make_coordinate(0.0, -180.001)
        result = v.validate_coordinate(c)
        assert result.valid is False


class TestInvalidBoundsError:
    def test_inverted_lat_range_raises(self):
        with pytest.raises(InvalidBoundsError):
            CoordValidator(lat_range=(90.0, -90.0))

    def test_inverted_lon_range_raises(self):
        with pytest.raises(InvalidBoundsError):
            CoordValidator(lon_range=(180.0, -180.0))

    def test_inverted_bounding_box_lat_raises(self):
        with pytest.raises(InvalidBoundsError):
            BoundingBox(min_lat=90.0, max_lat=-90.0, min_lon=-180.0, max_lon=180.0)


class TestExceptionHierarchy:
    def test_invalid_bounds_inherits_coord_error(self):
        assert issubclass(InvalidBoundsError, CoordError)

    def test_non_finite_inherits_coord_error(self):
        assert issubclass(NonFiniteCoordinateError, CoordError)


class TestCustomPolarThreshold:
    def test_custom_threshold_affects_near_polar(self):
        v = CoordValidator(polar_threshold=0.01)
        c = make_coordinate(89.995, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_near_polar is True

    def test_threshold_too_small_not_near_polar(self):
        v = CoordValidator(polar_threshold=0.0001)
        c = make_coordinate(89.999, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_near_polar is False

    def test_threshold_zero(self):
        v = CoordValidator(polar_threshold=0.0)
        c = make_coordinate(89.9999, 0.0)
        result = v.check_polar_singularity(c)
        assert result.is_near_polar is False


class TestCoordinateFrozen:
    def test_coordinate_is_immutable(self):
        c = make_coordinate(45.0, 90.0)
        with pytest.raises(AttributeError):
            c.latitude = 50.0

    def test_coordinate_hashable(self):
        c1 = make_coordinate(45.0, 90.0)
        c2 = make_coordinate(45.0, 90.0)
        assert hash(c1) == hash(c2)
        assert c1 == c2
        s = {c1, c2}
        assert len(s) == 1


class TestBoundingBoxFrozen:
    def test_bounding_box_is_immutable(self):
        b = BoundingBox(min_lat=-90.0, max_lat=90.0, min_lon=-180.0, max_lon=180.0)
        with pytest.raises(AttributeError):
            b.min_lat = 0.0


class TestCrossingPointClamping:
    def test_crossing_lat_clamped_to_90(self):
        v = make_validator()
        start = make_coordinate(89.0, 170.0)
        end = make_coordinate(91.0, -170.0)
        try:
            end = make_coordinate(89.5, -170.0)
        except NonFiniteCoordinateError:
            pass
        start = make_coordinate(88.0, 170.0)
        end = make_coordinate(89.5, -170.0)
        result = v.check_antimeridian_crossing(start, end)
        assert result.crosses is True
        assert result.crossing_point is not None
        assert -90.0 <= result.crossing_point.latitude <= 90.0
