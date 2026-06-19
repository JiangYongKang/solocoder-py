from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .exceptions import (
    EmptyGeohashError,
    InvalidGeohashCharacterError,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidPrecisionError,
)

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_BASE32_MAP = {c: i for i, c in enumerate(_BASE32)}

_MIN_PRECISION = 1
_MAX_PRECISION = 12

_NEIGHBOR_CODES = {
    "n": ["p0r21436x8zb9dcf5h7kjnmqesgutwvy", "bc01fg45238967deuvhjyznpkmstqrwx"],
    "s": ["14365h7k9dcfesgujnmqp0r2twvyx8zb", "238967debc01fg45kmstqrwxuvhjyznp"],
    "e": ["bc01fg45238967deuvhjyznpkmstqrwx", "p0r21436x8zb9dcf5h7kjnmqesgutwvy"],
    "w": ["238967debc01fg45kmstqrwxuvhjyznp", "14365h7k9dcfesgujnmqp0r2twvyx8zb"],
}

_BORDER_CODES = {
    "n": ["prxz", "bcfguvyz"],
    "s": ["028b", "0145hjnp"],
    "e": ["bcfguvyz", "prxz"],
    "w": ["0145hjnp", "028b"],
}


@dataclass
class GeohashBoundingBox:
    min_lon: float
    max_lon: float
    min_lat: float
    max_lat: float

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2.0

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2.0

    @property
    def lat_error(self) -> float:
        return (self.max_lat - self.min_lat) / 2.0

    @property
    def lon_error(self) -> float:
        return (self.max_lon - self.min_lon) / 2.0

    def contains(self, lat: float, lon: float) -> bool:
        return (
            self.min_lat <= lat <= self.max_lat
            and self.min_lon <= lon <= self.max_lon
        )

    def is_adjacent(self, other: "GeohashBoundingBox") -> bool:
        lat_adjacent = (
            abs(self.max_lat - other.min_lat) < 1e-10
            or abs(self.min_lat - other.max_lat) < 1e-10
        )
        lon_adjacent = (
            abs(self.max_lon - other.min_lon) < 1e-10
            or abs(self.min_lon - other.max_lon) < 1e-10
        )
        lat_overlap = not (self.max_lat < other.min_lat or self.min_lat > other.max_lat)
        lon_overlap = not (self.max_lon < other.min_lon or self.min_lon > other.max_lon)

        return (lat_adjacent and lon_overlap) or (lon_adjacent and lat_overlap)


@dataclass
class GeohashNeighbors:
    north: Optional[str]
    north_east: Optional[str]
    east: Optional[str]
    south_east: Optional[str]
    south: Optional[str]
    south_west: Optional[str]
    west: Optional[str]
    north_west: Optional[str]

    def to_dict(self) -> dict[str, Optional[str]]:
        return {
            "north": self.north,
            "north_east": self.north_east,
            "east": self.east,
            "south_east": self.south_east,
            "south": self.south,
            "south_west": self.south_west,
            "west": self.west,
            "north_west": self.north_west,
        }

    def to_list(self) -> list[Optional[str]]:
        return [
            self.north,
            self.north_east,
            self.east,
            self.south_east,
            self.south,
            self.south_west,
            self.west,
            self.north_west,
        ]

    def __iter__(self):
        return iter(self.to_list())


class GeohashCodec:
    def __init__(self, precision: int = 12):
        if precision < _MIN_PRECISION or precision > _MAX_PRECISION:
            raise InvalidPrecisionError(
                f"Precision must be between {_MIN_PRECISION} and {_MAX_PRECISION}"
            )
        self.precision = precision

    def encode(self, lat: float, lon: float) -> str:
        return encode(lat, lon, self.precision)

    def decode(self, geohash: str) -> tuple[float, float, float, float]:
        return decode(geohash)

    def decode_bbox(self, geohash: str) -> GeohashBoundingBox:
        return decode_bbox(geohash)

    def get_neighbors(self, geohash: str) -> GeohashNeighbors:
        return get_neighbors(geohash)


def _validate_coordinates(lat: float, lon: float) -> None:
    if lat < -90.0 or lat > 90.0:
        raise InvalidLatitudeError(
            f"Latitude must be between -90 and 90, got {lat}"
        )
    if lon < -180.0 or lon > 180.0:
        raise InvalidLongitudeError(
            f"Longitude must be between -180 and 180, got {lon}"
        )


def _validate_geohash(geohash: str) -> None:
    if not geohash:
        raise EmptyGeohashError("Geohash string cannot be empty")
    for c in geohash:
        if c not in _BASE32_MAP:
            raise InvalidGeohashCharacterError(
                f"Invalid geohash character: '{c}'"
            )


def encode(lat: float, lon: float, precision: int = 12) -> str:
    if precision < _MIN_PRECISION or precision > _MAX_PRECISION:
        raise InvalidPrecisionError(
            f"Precision must be between {_MIN_PRECISION} and {_MAX_PRECISION}"
        )

    _validate_coordinates(lat, lon)

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    even_bit = True
    geohash_str = ""

    for _ in range(precision):
        char_bits = 0
        for _ in range(5):
            if even_bit:
                mid = (lon_min + lon_max) / 2.0
                if lon >= mid:
                    char_bits = (char_bits << 1) | 1
                    lon_min = mid
                else:
                    char_bits = (char_bits << 1) | 0
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2.0
                if lat >= mid:
                    char_bits = (char_bits << 1) | 1
                    lat_min = mid
                else:
                    char_bits = (char_bits << 1) | 0
                    lat_max = mid
            even_bit = not even_bit
        geohash_str += _BASE32[char_bits]

    return geohash_str


def decode(geohash: str) -> tuple[float, float, float, float]:
    _validate_geohash(geohash)

    bbox = decode_bbox(geohash)
    return (
        bbox.center_lat,
        bbox.center_lon,
        bbox.lat_error,
        bbox.lon_error,
    )


def decode_bbox(geohash: str) -> GeohashBoundingBox:
    _validate_geohash(geohash)

    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    even_bit = True

    for c in geohash:
        char_val = _BASE32_MAP[c]
        for i in range(4, -1, -1):
            bit = (char_val >> i) & 1
            if even_bit:
                mid = (lon_min + lon_max) / 2.0
                if bit:
                    lon_min = mid
                else:
                    lon_max = mid
            else:
                mid = (lat_min + lat_max) / 2.0
                if bit:
                    lat_min = mid
                else:
                    lat_max = mid
            even_bit = not even_bit

    return GeohashBoundingBox(lon_min, lon_max, lat_min, lat_max)


def _get_neighbor(geohash: str, direction: str) -> Optional[str]:
    if not geohash:
        return None

    last_char = geohash[-1]
    prefix = geohash[:-1]
    precision = len(geohash)
    is_even = precision % 2 == 0
    type_idx = 0 if is_even else 1

    if last_char in _BORDER_CODES[direction][type_idx]:
        if prefix:
            prefix = _get_neighbor(prefix, direction)
            if prefix is None:
                return None
        else:
            if direction in ("n", "s"):
                return None

    neighbor_char_idx = _NEIGHBOR_CODES[direction][type_idx].index(last_char)
    return prefix + _BASE32[neighbor_char_idx]


def get_neighbors(geohash: str) -> GeohashNeighbors:
    _validate_geohash(geohash)

    bbox = decode_bbox(geohash)

    north = _get_neighbor(geohash, "n")
    south = _get_neighbor(geohash, "s")
    east = _get_neighbor(geohash, "e")
    west = _get_neighbor(geohash, "w")

    north_east = None
    if north is not None:
        north_east = _get_neighbor(north, "e")

    south_east = None
    if south is not None:
        south_east = _get_neighbor(south, "e")

    south_west = None
    if south is not None:
        south_west = _get_neighbor(south, "w")

    north_west = None
    if north is not None:
        north_west = _get_neighbor(north, "w")

    if north is not None:
        north_bbox = decode_bbox(north)
        if north_bbox.min_lat >= 90.0 or abs(north_bbox.min_lat - 90.0) < 1e-10:
            if abs(bbox.max_lat - 90.0) < 1e-10:
                pass
            else:
                north = None
                north_east = None
                north_west = None

    if south is not None:
        south_bbox = decode_bbox(south)
        if south_bbox.max_lat <= -90.0 or abs(south_bbox.max_lat + 90.0) < 1e-10:
            if abs(bbox.min_lat + 90.0) < 1e-10:
                pass
            else:
                south = None
                south_east = None
                south_west = None

    return GeohashNeighbors(
        north=north,
        north_east=north_east,
        east=east,
        south_east=south_east,
        south=south,
        south_west=south_west,
        west=west,
        north_west=north_west,
    )
