from __future__ import annotations

import pytest

from solocoder_py.geohash import (
    GeohashCodec,
    decode,
    decode_bbox,
    encode,
    get_neighbors,
)


class TestEncodeDecodeRoundtrip:
    def test_different_precisions_roundtrip(self):
        test_coords = [
            (37.371, -122.031),
            (39.9087, 116.3975),
            (51.5074, -0.1278),
            (-33.8688, 151.2093),
            (0.0, 0.0),
            (89.0, 0.0),
            (-89.0, 0.0),
            (0.0, 179.0),
            (0.0, -179.0),
        ]

        for lat, lon in test_coords:
            for precision in range(1, 13):
                geohash = encode(lat, lon, precision)
                assert len(geohash) == precision

                decoded_lat, decoded_lon, lat_err, lon_err = decode(geohash)
                assert abs(lat - decoded_lat) <= lat_err
                assert abs(lon - decoded_lon) <= lon_err

    def test_encode_known_values(self, known_geohashes):
        for item in known_geohashes:
            result = encode(item["lat"], item["lon"], item["precision"])
            assert result == item["geohash"]

    def test_decode_returns_center_within_bbox(self):
        geohash = encode(37.371, -122.031, 8)
        lat, lon, lat_err, lon_err = decode(geohash)
        bbox = decode_bbox(geohash)

        assert bbox.min_lat <= lat <= bbox.max_lat
        assert bbox.min_lon <= lon <= bbox.max_lon
        assert abs(lat - bbox.center_lat) < 1e-10
        assert abs(lon - bbox.center_lon) < 1e-10
        assert abs(lat_err - bbox.lat_error) < 1e-10
        assert abs(lon_err - bbox.lon_error) < 1e-10

    def test_precision_vs_error(self, precision_errors):
        for precision, expected_lat_err, expected_lon_err in precision_errors:
            geohash = encode(0.0, 0.0, precision)
            _, _, lat_err, lon_err = decode(geohash)
            assert abs(lat_err - expected_lat_err) < 1e-10
            assert abs(lon_err - expected_lon_err) < 1e-10


class TestBoundingBox:
    def test_bbox_four_boundaries(self):
        geohash = "9q9hx5"
        bbox = decode_bbox(geohash)

        assert bbox.min_lon < bbox.max_lon
        assert bbox.min_lat < bbox.max_lat
        assert -180 <= bbox.min_lon <= 180
        assert -180 <= bbox.max_lon <= 180
        assert -90 <= bbox.min_lat <= 90
        assert -90 <= bbox.max_lat <= 90

    def test_bbox_center_calculation(self):
        geohash = "wx4g0s8q"
        bbox = decode_bbox(geohash)

        expected_center_lat = (bbox.min_lat + bbox.max_lat) / 2.0
        expected_center_lon = (bbox.min_lon + bbox.max_lon) / 2.0

        assert abs(bbox.center_lat - expected_center_lat) < 1e-10
        assert abs(bbox.center_lon - expected_center_lon) < 1e-10

    def test_bbox_error_calculation(self):
        geohash = "gcpvj0"
        bbox = decode_bbox(geohash)

        expected_lat_error = (bbox.max_lat - bbox.min_lat) / 2.0
        expected_lon_error = (bbox.max_lon - bbox.min_lon) / 2.0

        assert abs(bbox.lat_error - expected_lat_error) < 1e-10
        assert abs(bbox.lon_error - expected_lon_error) < 1e-10

    def test_bbox_contains_point(self):
        lat, lon = 37.371, -122.031
        for precision in range(1, 13):
            geohash = encode(lat, lon, precision)
            bbox = decode_bbox(geohash)
            assert bbox.contains(lat, lon)

    def test_decode_bbox_vs_decode_consistency(self):
        test_geohashes = ["9q9hx5", "wx4g0s8q", "gcpvj0", "r3gx2f", "u09tunqrn"]

        for geohash in test_geohashes:
            lat, lon, lat_err, lon_err = decode(geohash)
            bbox = decode_bbox(geohash)

            assert abs(lat - bbox.center_lat) < 1e-10
            assert abs(lon - bbox.center_lon) < 1e-10
            assert abs(lat_err - bbox.lat_error) < 1e-10
            assert abs(lon_err - bbox.lon_error) < 1e-10


class TestNeighborEnumeration:
    def test_eight_neighbors_exist_for_interior_cell(self):
        geohash = encode(37.371, -122.031, 6)
        neighbors = get_neighbors(geohash)

        assert neighbors.north is not None
        assert neighbors.north_east is not None
        assert neighbors.east is not None
        assert neighbors.south_east is not None
        assert neighbors.south is not None
        assert neighbors.south_west is not None
        assert neighbors.west is not None
        assert neighbors.north_west is not None

    def test_neighbors_are_adjacent(self):
        geohash = encode(37.371, -122.031, 6)
        bbox = decode_bbox(geohash)
        neighbors = get_neighbors(geohash)

        for neighbor_gh in neighbors:
            assert neighbor_gh is not None
            neighbor_bbox = decode_bbox(neighbor_gh)
            assert bbox.is_adjacent(neighbor_bbox)

    def test_neighbors_have_same_length(self):
        for precision in range(1, 13):
            geohash = encode(37.371, -122.031, precision)
            neighbors = get_neighbors(geohash)

            for neighbor_gh in neighbors:
                if neighbor_gh is not None:
                    assert len(neighbor_gh) == len(geohash)

    def test_neighbor_directions(self):
        geohash = encode(37.371, -122.031, 8)
        bbox = decode_bbox(geohash)
        neighbors = get_neighbors(geohash)

        north_bbox = decode_bbox(neighbors.north)
        assert abs(north_bbox.min_lat - bbox.max_lat) < 1e-10

        south_bbox = decode_bbox(neighbors.south)
        assert abs(south_bbox.max_lat - bbox.min_lat) < 1e-10

        east_bbox = decode_bbox(neighbors.east)
        assert abs(east_bbox.min_lon - bbox.max_lon) < 1e-10

        west_bbox = decode_bbox(neighbors.west)
        assert abs(west_bbox.max_lon - bbox.min_lon) < 1e-10

    def test_diagonal_neighbors(self):
        geohash = encode(37.371, -122.031, 6)
        neighbors = get_neighbors(geohash)

        north_from_north_east = get_neighbors(neighbors.north_east).south
        west_from_north_east = get_neighbors(neighbors.north_east).west
        assert north_from_north_east == neighbors.east
        assert west_from_north_east == neighbors.north

    def test_neighbors_to_dict(self):
        geohash = "9q9hx5"
        neighbors = get_neighbors(geohash)
        neighbor_dict = neighbors.to_dict()

        assert isinstance(neighbor_dict, dict)
        assert "north" in neighbor_dict
        assert "south" in neighbor_dict
        assert "east" in neighbor_dict
        assert "west" in neighbor_dict

    def test_neighbors_to_list(self):
        geohash = "9q9hx5"
        neighbors = get_neighbors(geohash)
        neighbor_list = neighbors.to_list()

        assert isinstance(neighbor_list, list)
        assert len(neighbor_list) == 8


class TestEvenOddPrecisionBbox:
    def test_even_precision_bbox_shape(self):
        lat, lon = 37.371, -122.031

        for precision in [2, 4, 6, 8, 10, 12]:
            geohash = encode(lat, lon, precision)
            bbox = decode_bbox(geohash)

            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat

            assert abs(lon_width - 2 * lat_height) / max(lon_width, lat_height) < 0.01

    def test_odd_precision_bbox_shape(self):
        lat, lon = 37.371, -122.031

        for precision in [1, 3, 5, 7, 9, 11]:
            geohash = encode(lat, lon, precision)
            bbox = decode_bbox(geohash)

            lon_width = bbox.max_lon - bbox.min_lon
            lat_height = bbox.max_lat - bbox.min_lat

            assert abs(lon_width - lat_height) / max(lon_width, lat_height) < 0.01


class TestCodecClass:
    def test_codec_encode(self):
        codec = GeohashCodec(precision=6)
        geohash = codec.encode(37.371, -122.031)
        assert geohash == "9q9hx5"
        assert len(geohash) == 6

    def test_codec_decode(self):
        codec = GeohashCodec()
        lat, lon, lat_err, lon_err = codec.decode("9q9hx5")
        assert isinstance(lat, float)
        assert isinstance(lon, float)

    def test_codec_decode_bbox(self):
        codec = GeohashCodec()
        bbox = codec.decode_bbox("9q9hx5")
        assert bbox.min_lon < bbox.max_lon
        assert bbox.min_lat < bbox.max_lat

    def test_codec_get_neighbors(self):
        codec = GeohashCodec()
        neighbors = codec.get_neighbors("9q9hx5")
        assert neighbors.north is not None


class TestBoundingBoxAdjacency:
    def test_adjacent_bboxes(self):
        bbox1 = decode_bbox("9q9hx5")
        bbox2 = decode_bbox("9q9hxh")

        assert bbox1.is_adjacent(bbox2)
        assert bbox2.is_adjacent(bbox1)

    def test_diagonal_adjacent(self):
        bbox1 = decode_bbox("9q9hx5")
        bbox2 = decode_bbox("9q9hxk")

        assert bbox1.is_adjacent(bbox2)

    def test_non_adjacent_bboxes(self):
        bbox1 = decode_bbox("9q9hx5")
        bbox2 = decode_bbox("wx4g0s")

        assert not bbox1.is_adjacent(bbox2)

    def test_same_bbox_not_adjacent(self):
        bbox1 = decode_bbox("9q9hx5")
        bbox2 = decode_bbox("9q9hx5")

        assert not bbox1.is_adjacent(bbox2)
