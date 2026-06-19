from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import List, Optional

from .exceptions import NonFiniteCoordinateError


@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if math.isnan(self.latitude) or math.isinf(self.latitude):
            raise NonFiniteCoordinateError(
                f"Latitude must be finite, got {self.latitude}"
            )
        if math.isnan(self.longitude) or math.isinf(self.longitude):
            raise NonFiniteCoordinateError(
                f"Longitude must be finite, got {self.longitude}"
            )

    @property
    def is_polar(self) -> bool:
        return abs(abs(self.latitude) - 90.0) < 1e-9

    @property
    def is_near_polar(self) -> bool:
        return abs(abs(self.latitude) - 90.0) < 0.001


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def __post_init__(self) -> None:
        if math.isnan(self.min_lat) or math.isinf(self.min_lat):
            raise NonFiniteCoordinateError(
                f"min_lat must be finite, got {self.min_lat}"
            )
        if math.isnan(self.max_lat) or math.isinf(self.max_lat):
            raise NonFiniteCoordinateError(
                f"max_lat must be finite, got {self.max_lat}"
            )
        if math.isnan(self.min_lon) or math.isinf(self.min_lon):
            raise NonFiniteCoordinateError(
                f"min_lon must be finite, got {self.min_lon}"
            )
        if math.isnan(self.max_lon) or math.isinf(self.max_lon):
            raise NonFiniteCoordinateError(
                f"max_lon must be finite, got {self.max_lon}"
            )
        if self.min_lat > self.max_lat:
            from .exceptions import InvalidBoundsError

            raise InvalidBoundsError(
                f"min_lat ({self.min_lat}) must be <= max_lat ({self.max_lat})"
            )
        if self.min_lon > self.max_lon:
            from .exceptions import InvalidBoundsError

            raise InvalidBoundsError(
                f"min_lon ({self.min_lon}) must be <= max_lon ({self.max_lon})"
            )

    def contains(self, coord: Coordinate) -> bool:
        return (
            self.min_lat <= coord.latitude <= self.max_lat
            and self.min_lon <= coord.longitude <= self.max_lon
        )


@dataclass(frozen=True)
class InvalidCoordinate:
    index: Optional[int]
    latitude: float
    longitude: float
    reason: str


@dataclass
class ValidationResult:
    valid: bool
    invalid_coordinates: List[InvalidCoordinate] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


class CrossingDirection(enum.Enum):
    EASTWARD = "eastward"
    WESTWARD = "westward"


@dataclass(frozen=True)
class AntimeridianCrossing:
    crosses: bool
    direction: Optional[CrossingDirection] = None
    crossing_point: Optional[Coordinate] = None
    segment_index: Optional[int] = None


@dataclass(frozen=True)
class PolarCheckResult:
    index: Optional[int]
    is_polar: bool
    is_near_polar: bool
    latitude_warning: Optional[str] = None
