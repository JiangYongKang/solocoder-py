from __future__ import annotations

import math
from dataclasses import dataclass

from .exceptions import InvalidLatitudeError, InvalidLongitudeError


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not isinstance(self.latitude, (int, float)):
            raise InvalidLatitudeError(
                f"Latitude must be a number, got {type(self.latitude).__name__}"
            )
        if not isinstance(self.longitude, (int, float)):
            raise InvalidLongitudeError(
                f"Longitude must be a number, got {type(self.longitude).__name__}"
            )

        if math.isnan(self.latitude) or math.isinf(self.latitude):
            raise InvalidLatitudeError(
                f"Latitude must be a finite number, got {self.latitude}"
            )
        if math.isnan(self.longitude) or math.isinf(self.longitude):
            raise InvalidLongitudeError(
                f"Longitude must be a finite number, got {self.longitude}"
            )

        if self.latitude < -90.0 or self.latitude > 90.0:
            raise InvalidLatitudeError(
                f"Latitude must be between -90 and 90, got {self.latitude}"
            )
        if self.longitude < -180.0 or self.longitude > 180.0:
            raise InvalidLongitudeError(
                f"Longitude must be between -180 and 180, got {self.longitude}"
            )


@dataclass
class BoundingBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


@dataclass
class GeoSearchResult:
    point: GeoPoint
    distance_km: float


@dataclass
class GeoSearchResponse:
    results: list[GeoSearchResult]
    total_count: int
    filtered_count: int
    returned_count: int
