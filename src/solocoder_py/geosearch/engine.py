from __future__ import annotations

import math
from typing import Optional

from .exceptions import (
    InvalidCoordinateError,
    InvalidLatitudeError,
    InvalidLimitError,
    InvalidLongitudeError,
    InvalidRadiusError,
)
from .models import (
    BoundingBox,
    GeoPoint,
    GeoSearchResponse,
    GeoSearchResult,
)

EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_LAT = 111.32


class GeoSearchEngine:
    def __init__(self, candidates: Optional[list[GeoPoint]] = None) -> None:
        self._candidates: list[GeoPoint] = []
        if candidates is not None:
            for point in candidates:
                self._validate_coordinate(point.latitude, point.longitude)
                self._candidates.append(point)

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def add_candidate(self, point: GeoPoint) -> None:
        self._validate_coordinate(point.latitude, point.longitude)
        self._candidates.append(point)

    def add_candidates(self, points: list[GeoPoint]) -> None:
        validated = []
        for point in points:
            self._validate_coordinate(point.latitude, point.longitude)
            validated.append(point)
        self._candidates.extend(validated)

    def clear_candidates(self) -> None:
        self._candidates.clear()

    def search(
        self,
        center: GeoPoint,
        radius_km: float,
        limit: Optional[int] = None,
    ) -> GeoSearchResponse:
        self._validate_coordinate(center.latitude, center.longitude)

        if radius_km < 0:
            raise InvalidRadiusError(
                f"Search radius must be >= 0, got {radius_km}"
            )

        if limit is not None and limit < 0:
            raise InvalidLimitError(
                f"Result limit must be >= 0, got {limit}"
            )

        bbox = self._build_bounding_box(center, radius_km)

        valid_candidates: list[GeoPoint] = []
        for point in self._candidates:
            try:
                self._validate_coordinate(point.latitude, point.longitude)
                if self._is_in_bounding_box(point, bbox):
                    valid_candidates.append(point)
            except (InvalidLatitudeError, InvalidLongitudeError):
                continue

        filtered_count = len(valid_candidates)

        results: list[GeoSearchResult] = []
        for point in valid_candidates:
            distance = self._haversine_distance(center, point)
            if distance <= radius_km:
                results.append(GeoSearchResult(point=point, distance_km=distance))

        results.sort(key=lambda r: r.distance_km)

        total_count = len(results)

        if limit is not None:
            results = results[:limit]

        return GeoSearchResponse(
            results=results,
            total_count=total_count,
            filtered_count=filtered_count,
            returned_count=len(results),
        )

    def _build_bounding_box(self, center: GeoPoint, radius_km: float) -> BoundingBox:
        lat_offset = radius_km / KM_PER_DEGREE_LAT

        min_lat = center.latitude - lat_offset
        max_lat = center.latitude + lat_offset

        covers_pole = False
        if max_lat > 90.0:
            max_lat = 90.0
            min_lat = max(min_lat, -90.0)
            covers_pole = True
        if min_lat < -90.0:
            min_lat = -90.0
            max_lat = min(max_lat, 90.0)
            covers_pole = True

        center_lat_rad = math.radians(center.latitude)
        cos_lat = math.cos(center_lat_rad)
        if abs(cos_lat) < 1e-12:
            lng_offset = 180.0
        else:
            lng_offset = radius_km / (KM_PER_DEGREE_LAT * cos_lat)

        if covers_pole or lng_offset >= 180.0:
            min_lng = -180.0
            max_lng = 180.0
        else:
            min_lng_raw = center.longitude - lng_offset
            max_lng_raw = center.longitude + lng_offset

            min_lng = ((min_lng_raw + 180.0) % 360.0) - 180.0
            max_lng = ((max_lng_raw + 180.0) % 360.0) - 180.0

        return BoundingBox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )

    def _is_in_bounding_box(self, point: GeoPoint, bbox: BoundingBox) -> bool:
        lat_ok = bbox.min_lat <= point.latitude <= bbox.max_lat

        if bbox.min_lng <= bbox.max_lng:
            lng_ok = bbox.min_lng <= point.longitude <= bbox.max_lng
        else:
            lng_ok = (point.longitude >= bbox.min_lng) or (point.longitude <= bbox.max_lng)

        return lat_ok and lng_ok

    @staticmethod
    def _haversine_distance(p1: GeoPoint, p2: GeoPoint) -> float:
        lat1 = math.radians(p1.latitude)
        lon1 = math.radians(p1.longitude)
        lat2 = math.radians(p2.latitude)
        lon2 = math.radians(p2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_KM * c

    @staticmethod
    def _validate_coordinate(latitude: float, longitude: float) -> None:
        if not isinstance(latitude, (int, float)):
            raise InvalidLatitudeError(
                f"Latitude must be a number, got {type(latitude).__name__}"
            )
        if not isinstance(longitude, (int, float)):
            raise InvalidLongitudeError(
                f"Longitude must be a number, got {type(longitude).__name__}"
            )

        if math.isnan(latitude) or math.isinf(latitude):
            raise InvalidLatitudeError(
                f"Latitude must be a finite number, got {latitude}"
            )
        if math.isnan(longitude) or math.isinf(longitude):
            raise InvalidLongitudeError(
                f"Longitude must be a finite number, got {longitude}"
            )

        if latitude < -90.0 or latitude > 90.0:
            raise InvalidLatitudeError(
                f"Latitude must be between -90 and 90, got {latitude}"
            )
        if longitude < -180.0 or longitude > 180.0:
            raise InvalidLongitudeError(
                f"Longitude must be between -180 and 180, got {longitude}"
            )
