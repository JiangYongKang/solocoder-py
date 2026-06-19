from __future__ import annotations

import pytest

from solocoder_py.geohash import decode_bbox, encode, get_neighbors


class TestPrecisionBoundaries:
    def test_precision_1_coarsest(self):
        geohash = encode(37.371, -122.031, precision=1)
        assert len(geohash) == 1

        bbox = decode_bbox(geohash)
        lat_range = bbox.max_lat - bbox.min_lat
        lon_range = bbox.max_lon - bbox.min_lon

        assert lat_range > 40
        assert lon_range > 40

    def test_precision_12_finest(self):
        geohash = encode(37.371, -122.031, precision=12)
        assert len(geohash) == 12

        bbox = decode_bbox(geohash)
        lat_err = bbox.lat_error
        lon_err = bbox.lon_error
        assert lat_err < 1e-6
        assert lon_err < 1e-6

    def test_roundtrip_precision_1(self):
        test_coords = [
            (45.0, 90.0),
            (-45.0, -90.0),
            (0.0, 0.0),
        ]

        for lat, lon in test_coords:
            geohash = encode(lat, lon, precision=1)
            bbox = decode_bbox(geohash)
            decoded_lat = bbox.center_lat
            decoded_lon = bbox.center_lon
            lat_err = bbox.lat_error
            lon_err = bbox.lon_error

            assert abs(lat - decoded_lat) <= lat_err
            assert abs(lon - decoded_lon) <= lon_err

    def test_roundtrip_precision_12(self):
        test_coords = [
            (37.371123456789, -122.031987654321),
            (89.999999999, 179.999999999),
            (-89.999999999, -179.999999999),
        ]

        for lat, lon in test_coords:
            geohash = encode(lat, lon, precision=12)
            bbox = decode_bbox(geohash)
            decoded_lat = bbox.center_lat
            decoded_lon = bbox.center_lon
            lat_err = bbox.lat_error
            lon_err = bbox.lon_error

            assert abs(lat - decoded_lat) <= lat_err
            assert abs(lon - decoded_lon) <= lon_err


class TestEquatorCoordinates:
    def test_encode_equator_exact(self):
        geohash = encode(0.0, 0.0, precision=8)
        assert geohash is not None
        assert len(geohash) == 8

        bbox = decode_bbox(geohash)
        assert bbox.min_lat <= 0.0 <= bbox.max_lat
        assert bbox.min_lon <= 0.0 <= bbox.max_lon

    def test_encode_equator_nearby(self):
        for lat in [0.0001, -0.0001, 0.01, -0.01, 0.1, -0.1]:
            geohash = encode(lat, 0.0, precision=8)
            bbox = decode_bbox(geohash)
            assert bbox.contains(lat, 0.0)

    def test_equator_neighbors(self):
        geohash = encode(0.0, 30.0, precision=6)
        neighbors = get_neighbors(geohash)

        assert neighbors.north is not None
        assert neighbors.south is not None

        north_bbox = decode_bbox(neighbors.north)
        south_bbox = decode_bbox(neighbors.south)

        assert north_bbox.min_lat >= 0.0 or north_bbox.max_lat >= 0.0
        assert south_bbox.max_lat <= 0.0 or south_bbox.min_lat <= 0.0


class TestGreenwichMeridian:
    def test_encode_greenwich_exact(self):
        geohash = encode(51.5074, 0.0, precision=8)
        assert geohash is not None

        bbox = decode_bbox(geohash)
        assert bbox.min_lon <= 0.0 <= bbox.max_lon

    def test_encode_greenwich_nearby(self):
        for lon in [0.0001, -0.0001, 0.01, -0.01, 0.1, -0.1]:
            geohash = encode(51.5074, lon, precision=8)
            bbox = decode_bbox(geohash)
            assert bbox.contains(51.5074, lon)

    def test_greenwich_neighbors(self):
        geohash_east = encode(51.5074, 0.01, precision=6)
        geohash_west = encode(51.5074, -0.01, precision=6)

        neighbors_east = get_neighbors(geohash_east)
        neighbors_west = get_neighbors(geohash_west)

        assert neighbors_east.west is not None
        assert neighbors_west.east is not None


class TestPoleCoordinates:
    def test_encode_near_north_pole(self):
        lat = 89.9
        for precision in range(1, 13):
            geohash = encode(lat, 0.0, precision)
            bbox = decode_bbox(geohash)
            assert bbox.contains(lat, 0.0)
            assert bbox.max_lat <= 90.0

    def test_encode_near_south_pole(self):
        lat = -89.9
        for precision in range(1, 13):
            geohash = encode(lat, 0.0, precision)
            bbox = decode_bbox(geohash)
            assert bbox.contains(lat, 0.0)
            assert bbox.min_lat >= -90.0

    def test_north_pole_neighbors(self):
        geohash = encode(89.999, 0.0, precision=4)
        bbox = decode_bbox(geohash)

        assert abs(bbox.max_lat - 90.0) < 1e-10

        neighbors = get_neighbors(geohash)
        assert neighbors.north is None
        assert neighbors.north_east is None
        assert neighbors.north_west is None

    def test_north_non_pole_has_all_neighbors(self):
        geohash = encode(80.0, 0.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.max_lat < 90.0

        neighbors = get_neighbors(geohash)
        assert neighbors.north is not None
        assert neighbors.north_east is not None
        assert neighbors.north_west is not None

    def test_south_pole_neighbors(self):
        geohash = encode(-89.999, 0.0, precision=4)
        bbox = decode_bbox(geohash)

        assert abs(bbox.min_lat + 90.0) < 1e-10

        neighbors = get_neighbors(geohash)
        assert neighbors.south is None
        assert neighbors.south_east is None
        assert neighbors.south_west is None

    def test_south_non_pole_has_all_neighbors(self):
        geohash = encode(-80.0, 0.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.min_lat > -90.0

        neighbors = get_neighbors(geohash)
        assert neighbors.south is not None
        assert neighbors.south_east is not None
        assert neighbors.south_west is not None

    def test_pole_neighbor_nonexistence(self):
        geohash = encode(89.9999, 0.0, precision=2)
        bbox = decode_bbox(geohash)
        assert abs(bbox.max_lat - 90.0) < 1e-10

        neighbors = get_neighbors(geohash)
        assert neighbors.north is None


class TestAntimeridianCrossing:
    def test_encode_near_positive_180(self):
        lon = 179.999
        geohash = encode(0.0, lon, precision=8)
        bbox = decode_bbox(geohash)
        assert bbox.contains(0.0, lon)

    def test_encode_near_negative_180(self):
        lon = -179.999
        geohash = encode(0.0, lon, precision=8)
        bbox = decode_bbox(geohash)
        assert bbox.contains(0.0, lon)

    def test_east_neighbor_crosses_antimeridian(self):
        geohash = encode(0.0, 179.999, precision=6)
        bbox = decode_bbox(geohash)

        assert abs(bbox.max_lon - 180.0) < 1e-5

        neighbors = get_neighbors(geohash)
        assert neighbors.east is not None
        east_bbox = decode_bbox(neighbors.east)
        assert east_bbox.min_lon < 0
        assert east_bbox.max_lon < 0 or east_bbox.max_lon > 180

    def test_east_neighbor_not_at_antimeridian(self):
        geohash = encode(0.0, 120.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.max_lon < 180.0 - 1e-3

        neighbors = get_neighbors(geohash)
        assert neighbors.east is not None
        east_bbox = decode_bbox(neighbors.east)
        assert east_bbox.min_lon > bbox.min_lon
        assert east_bbox.max_lon < 180.0 or east_bbox.min_lon < 0

    def test_west_neighbor_crosses_antimeridian(self):
        geohash = encode(0.0, -179.999, precision=6)
        bbox = decode_bbox(geohash)

        assert abs(bbox.min_lon + 180.0) < 1e-5

        neighbors = get_neighbors(geohash)
        assert neighbors.west is not None
        west_bbox = decode_bbox(neighbors.west)
        assert west_bbox.max_lon > 0

    def test_west_neighbor_not_at_antimeridian(self):
        geohash = encode(0.0, -120.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.min_lon > -180.0 + 1e-3

        neighbors = get_neighbors(geohash)
        assert neighbors.west is not None
        west_bbox = decode_bbox(neighbors.west)
        assert west_bbox.min_lon < bbox.min_lon
        assert west_bbox.min_lon > -180.0 or west_bbox.max_lon > 0

    def test_antimeridian_adjacency(self):
        geohash_east = encode(0.0, 179.9999, precision=4)
        geohash_west = encode(0.0, -179.9999, precision=4)

        neighbors_east = get_neighbors(geohash_east)
        neighbors_west = get_neighbors(geohash_west)

        assert neighbors_east.east == geohash_west
        assert neighbors_west.west == geohash_east

    def test_diagonal_crosses_antimeridian(self):
        geohash = encode(1.0, 179.9999, precision=5)
        neighbors = get_neighbors(geohash)

        assert neighbors.east is not None
        east_bbox = decode_bbox(neighbors.east)
        assert east_bbox.min_lon < 0
        assert neighbors.north_east is not None or neighbors.south_east is not None

        if neighbors.north_east is not None:
            ne_bbox = decode_bbox(neighbors.north_east)
            assert abs(ne_bbox.min_lon - east_bbox.min_lon) < 1e-10
        if neighbors.south_east is not None:
            se_bbox = decode_bbox(neighbors.south_east)
            assert abs(se_bbox.min_lon - east_bbox.min_lon) < 1e-10


class TestBoundaryExactValues:
    def test_latitude_90_exact(self):
        geohash = encode(90.0, 0.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.max_lat <= 90.0
        assert bbox.contains(90.0, 0.0)

    def test_latitude_neg90_exact(self):
        geohash = encode(-90.0, 0.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.min_lat >= -90.0
        assert bbox.contains(-90.0, 0.0)

    def test_longitude_180_exact(self):
        geohash = encode(0.0, 180.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.max_lon <= 180.0
        assert bbox.contains(0.0, 180.0)

    def test_longitude_neg180_exact(self):
        geohash = encode(0.0, -180.0, precision=6)
        bbox = decode_bbox(geohash)
        assert bbox.min_lon >= -180.0
        assert bbox.contains(0.0, -180.0)

    def test_origin_point(self):
        geohash = encode(0.0, 0.0, precision=12)
        assert len(geohash) == 12

        bbox = decode_bbox(geohash)
        assert bbox.contains(0.0, 0.0)
        assert bbox.min_lat <= 0.0 <= bbox.max_lat
        assert bbox.min_lon <= 0.0 <= bbox.max_lon


class TestEvenOddPrecisionAtBoundaries:
    def test_odd_precision_at_equator(self):
        for precision in [1, 3, 5, 7, 9, 11]:
            geohash = encode(0.0, 0.0, precision)
            bbox = decode_bbox(geohash)
            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat
            assert abs(lon_width - lat_height) / max(lon_width, lat_height) < 0.01

    def test_even_precision_at_equator(self):
        for precision in [2, 4, 6, 8, 10, 12]:
            geohash = encode(0.0, 0.0, precision)
            bbox = decode_bbox(geohash)
            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat
            assert abs(lon_width - 2 * lat_height) / max(lon_width, lat_height) < 0.01

    def test_odd_precision_at_antimeridian(self):
        for precision in [1, 3, 5, 7, 9, 11]:
            geohash = encode(0.0, 179.999, precision)
            bbox = decode_bbox(geohash)
            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat
            assert abs(lon_width - lat_height) / max(lon_width, lat_height) < 0.01

    def test_even_precision_at_antimeridian(self):
        for precision in [2, 4, 6, 8, 10, 12]:
            geohash = encode(0.0, 179.999, precision)
            bbox = decode_bbox(geohash)
            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat
            assert abs(lon_width - 2 * lat_height) / max(lon_width, lat_height) < 0.01
