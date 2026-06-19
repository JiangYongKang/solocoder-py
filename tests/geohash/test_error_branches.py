from __future__ import annotations

import pytest

from solocoder_py.geohash import (
    EmptyGeohashError,
    GeohashCodec,
    GeohashError,
    InvalidGeohashCharacterError,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidPrecisionError,
    decode,
    decode_bbox,
    encode,
    get_neighbors,
)


class TestInvalidLatitude:
    def test_latitude_above_90(self):
        with pytest.raises(InvalidLatitudeError, match="Latitude must be between"):
            encode(91.0, 0.0)

    def test_latitude_below_neg90(self):
        with pytest.raises(InvalidLatitudeError, match="Latitude must be between"):
            encode(-91.0, 0.0)

    def test_latitude_just_above_90(self):
        with pytest.raises(InvalidLatitudeError):
            encode(90.0001, 0.0)

    def test_latitude_just_below_neg90(self):
        with pytest.raises(InvalidLatitudeError):
            encode(-90.0001, 0.0)

    def test_latitude_large_positive(self):
        with pytest.raises(InvalidLatitudeError):
            encode(1000.0, 0.0)

    def test_latitude_large_negative(self):
        with pytest.raises(InvalidLatitudeError):
            encode(-1000.0, 0.0)

    def test_invalid_latitude_via_codec(self):
        codec = GeohashCodec(precision=6)
        with pytest.raises(InvalidLatitudeError):
            codec.encode(95.0, 0.0)


class TestInvalidLongitude:
    def test_longitude_above_180(self):
        with pytest.raises(InvalidLongitudeError, match="Longitude must be between"):
            encode(0.0, 181.0)

    def test_longitude_below_neg180(self):
        with pytest.raises(InvalidLongitudeError, match="Longitude must be between"):
            encode(0.0, -181.0)

    def test_longitude_just_above_180(self):
        with pytest.raises(InvalidLongitudeError):
            encode(0.0, 180.0001)

    def test_longitude_just_below_neg180(self):
        with pytest.raises(InvalidLongitudeError):
            encode(0.0, -180.0001)

    def test_longitude_large_positive(self):
        with pytest.raises(InvalidLongitudeError):
            encode(0.0, 1000.0)

    def test_longitude_large_negative(self):
        with pytest.raises(InvalidLongitudeError):
            encode(0.0, -1000.0)

    def test_invalid_longitude_via_codec(self):
        codec = GeohashCodec(precision=6)
        with pytest.raises(InvalidLongitudeError):
            codec.encode(0.0, 185.0)


class TestInvalidPrecision:
    def test_precision_zero(self):
        with pytest.raises(InvalidPrecisionError, match="Precision must be between"):
            encode(0.0, 0.0, precision=0)

    def test_precision_negative(self):
        with pytest.raises(InvalidPrecisionError):
            encode(0.0, 0.0, precision=-1)

    def test_precision_above_max(self):
        with pytest.raises(InvalidPrecisionError):
            encode(0.0, 0.0, precision=13)

    def test_precision_large_negative(self):
        with pytest.raises(InvalidPrecisionError):
            encode(0.0, 0.0, precision=-100)

    def test_codec_invalid_precision_zero(self):
        with pytest.raises(InvalidPrecisionError):
            GeohashCodec(precision=0)

    def test_codec_invalid_precision_above_max(self):
        with pytest.raises(InvalidPrecisionError):
            GeohashCodec(precision=15)


class TestInvalidGeohashCharacters:
    def test_decode_invalid_character_a(self):
        with pytest.raises(InvalidGeohashCharacterError, match="Invalid geohash character"):
            decode("abcdef")

    def test_decode_invalid_character_i(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9q9hxi")

    def test_decode_invalid_character_l(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9q9hxl")

    def test_decode_invalid_character_o(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9q9hxo")

    def test_decode_invalid_character_special(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9q9hx!")

    def test_decode_invalid_character_space(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9q9hx ")

    def test_decode_invalid_character_uppercase(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("9Q9HX5")

    def test_decode_bbox_invalid_character(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode_bbox("invalid")

    def test_get_neighbors_invalid_character(self):
        with pytest.raises(InvalidGeohashCharacterError):
            get_neighbors("9q9hxA")

    def test_multiple_invalid_characters(self):
        with pytest.raises(InvalidGeohashCharacterError):
            decode("aAil!")


class TestEmptyGeohash:
    def test_decode_empty_string(self):
        with pytest.raises(EmptyGeohashError, match="Geohash string cannot be empty"):
            decode("")

    def test_decode_bbox_empty_string(self):
        with pytest.raises(EmptyGeohashError):
            decode_bbox("")

    def test_get_neighbors_empty_string(self):
        with pytest.raises(EmptyGeohashError):
            get_neighbors("")

    def test_codec_decode_empty_string(self):
        codec = GeohashCodec()
        with pytest.raises(EmptyGeohashError):
            codec.decode("")


class TestPoleNeighborNonexistence:
    def test_north_pole_no_north_neighbor(self):
        northmost_geohash = encode(89.9999, 0.0, precision=2)
        bbox = decode_bbox(northmost_geohash)

        if abs(bbox.max_lat - 90.0) < 1e-10:
            neighbors = get_neighbors(northmost_geohash)
            assert neighbors.north is None
            assert neighbors.north_east is None
            assert neighbors.north_west is None

    def test_south_pole_no_south_neighbor(self):
        southmost_geohash = encode(-89.9999, 0.0, precision=2)
        bbox = decode_bbox(southmost_geohash)

        if abs(bbox.min_lat + 90.0) < 1e-10:
            neighbors = get_neighbors(southmost_geohash)
            assert neighbors.south is None
            assert neighbors.south_east is None
            assert neighbors.south_west is None

    def test_pole_neighbor_none_type(self):
        geohash = encode(89.9999, 0.0, precision=1)
        bbox = decode_bbox(geohash)

        neighbors = get_neighbors(geohash)

        if bbox.max_lat >= 90.0 or abs(bbox.max_lat - 90.0) < 1e-10:
            assert neighbors.north is None
            assert isinstance(neighbors.north, type(None))

    def test_non_pole_has_all_neighbors(self):
        geohash = encode(45.0, 0.0, precision=4)
        neighbors = get_neighbors(geohash)

        assert neighbors.north is not None
        assert neighbors.south is not None
        assert neighbors.east is not None
        assert neighbors.west is not None
        assert neighbors.north_east is not None
        assert neighbors.north_west is not None
        assert neighbors.south_east is not None
        assert neighbors.south_west is not None


class TestExceptionHierarchy:
    def test_invalid_latitude_is_geohash_error(self):
        try:
            encode(91.0, 0.0)
        except GeohashError as e:
            assert isinstance(e, InvalidLatitudeError)

    def test_invalid_longitude_is_geohash_error(self):
        try:
            encode(0.0, 181.0)
        except GeohashError as e:
            assert isinstance(e, InvalidLongitudeError)

    def test_invalid_precision_is_geohash_error(self):
        try:
            encode(0.0, 0.0, precision=0)
        except GeohashError as e:
            assert isinstance(e, InvalidPrecisionError)

    def test_invalid_character_is_geohash_error(self):
        try:
            decode("invalid")
        except GeohashError as e:
            assert isinstance(e, InvalidGeohashCharacterError)

    def test_empty_geohash_is_geohash_error(self):
        try:
            decode("")
        except GeohashError as e:
            assert isinstance(e, EmptyGeohashError)

    def test_geohash_error_is_exception(self):
        assert issubclass(GeohashError, Exception)
        assert issubclass(InvalidLatitudeError, Exception)
        assert issubclass(InvalidLongitudeError, Exception)
        assert issubclass(InvalidPrecisionError, Exception)
        assert issubclass(InvalidGeohashCharacterError, Exception)
        assert issubclass(EmptyGeohashError, Exception)


class TestCombinedInvalidInputs:
    def test_both_coordinates_invalid(self):
        with pytest.raises((InvalidLatitudeError, InvalidLongitudeError)):
            encode(100.0, 200.0)

    def test_invalid_coords_and_precision(self):
        with pytest.raises(GeohashError):
            encode(100.0, 200.0, precision=0)

    def test_invalid_character_and_empty(self):
        with pytest.raises(GeohashError):
            decode("")

    def test_codec_with_invalid_precision_then_encode(self):
        with pytest.raises(InvalidPrecisionError):
            codec = GeohashCodec(precision=0)
            codec.encode(0.0, 0.0)
