from __future__ import annotations

import math
from typing import List, Optional

from .exceptions import InvalidBoundsError
from .models import (
    AntimeridianCrossing,
    BoundingBox,
    Coordinate,
    CrossingDirection,
    InvalidCoordinate,
    PolarCheckResult,
    ValidationResult,
)

_LAT_MIN = -90.0
_LAT_MAX = 90.0
_LON_MIN = -180.0
_LON_MAX = 180.0
_POLAR_THRESHOLD = 0.001
_CROSSING_LON_DIFF = 180.0


class CoordValidator:
    def __init__(
        self,
        lat_range: tuple[float, float] = (_LAT_MIN, _LAT_MAX),
        lon_range: tuple[float, float] = (_LON_MIN, _LON_MAX),
        polar_threshold: float = _POLAR_THRESHOLD,
    ) -> None:
        if lat_range[0] > lat_range[1]:
            raise InvalidBoundsError(
                f"lat_range min ({lat_range[0]}) must be <= max ({lat_range[1]})"
            )
        if lon_range[0] > lon_range[1]:
            raise InvalidBoundsError(
                f"lon_range min ({lon_range[0]}) must be <= max ({lon_range[1]})"
            )
        self._lat_min, self._lat_max = lat_range
        self._lon_min, self._lon_max = lon_range
        self._polar_threshold = polar_threshold

    @property
    def lat_range(self) -> tuple[float, float]:
        return (self._lat_min, self._lat_max)

    @property
    def lon_range(self) -> tuple[float, float]:
        return (self._lon_min, self._lon_max)

    @property
    def polar_threshold(self) -> float:
        return self._polar_threshold

    def validate_coordinate(
        self, coord: Coordinate, index: Optional[int] = None
    ) -> ValidationResult:
        reasons: list[str] = []
        if coord.latitude < self._lat_min or coord.latitude > self._lat_max:
            reasons.append(
                f"latitude {coord.latitude} out of range [{self._lat_min}, {self._lat_max}]"
            )
        if coord.longitude < self._lon_min or coord.longitude > self._lon_max:
            reasons.append(
                f"longitude {coord.longitude} out of range [{self._lon_min}, {self._lon_max}]"
            )
        if not reasons:
            return ValidationResult(valid=True, invalid_coordinates=[])
        invalid = InvalidCoordinate(
            index=index,
            latitude=coord.latitude,
            longitude=coord.longitude,
            reason="; ".join(reasons),
        )
        return ValidationResult(valid=False, invalid_coordinates=[invalid])

    def validate_coordinates(self, coords: List[Coordinate]) -> ValidationResult:
        all_invalid: list[InvalidCoordinate] = []
        for i, coord in enumerate(coords):
            result = self.validate_coordinate(coord, index=i)
            if not result.valid:
                all_invalid.extend(result.invalid_coordinates)
        return ValidationResult(
            valid=len(all_invalid) == 0, invalid_coordinates=all_invalid
        )

    def validate_against_bounds(
        self, coord: Coordinate, bounds: BoundingBox, index: Optional[int] = None
    ) -> ValidationResult:
        reasons: list[str] = []
        if coord.latitude < bounds.min_lat or coord.latitude > bounds.max_lat:
            reasons.append(
                f"latitude {coord.latitude} out of bounds [{bounds.min_lat}, {bounds.max_lat}]"
            )
        if coord.longitude < bounds.min_lon or coord.longitude > bounds.max_lon:
            reasons.append(
                f"longitude {coord.longitude} out of bounds [{bounds.min_lon}, {bounds.max_lon}]"
            )
        if not reasons:
            return ValidationResult(valid=True, invalid_coordinates=[])
        invalid = InvalidCoordinate(
            index=index,
            latitude=coord.latitude,
            longitude=coord.longitude,
            reason="; ".join(reasons),
        )
        return ValidationResult(valid=False, invalid_coordinates=[invalid])

    def validate_list_against_bounds(
        self, coords: List[Coordinate], bounds: BoundingBox
    ) -> ValidationResult:
        all_invalid: list[InvalidCoordinate] = []
        for i, coord in enumerate(coords):
            result = self.validate_against_bounds(coord, bounds, index=i)
            if not result.valid:
                all_invalid.extend(result.invalid_coordinates)
        return ValidationResult(
            valid=len(all_invalid) == 0, invalid_coordinates=all_invalid
        )

    def check_antimeridian_crossing(
        self, start: Coordinate, end: Coordinate, segment_index: Optional[int] = None
    ) -> AntimeridianCrossing:
        lon_diff = abs(end.longitude - start.longitude)
        if lon_diff <= _CROSSING_LON_DIFF:
            return AntimeridianCrossing(
                crosses=False, direction=None, crossing_point=None, segment_index=segment_index
            )
        direction = self._determine_crossing_direction(start, end)
        crossing_point = self._compute_crossing_point(start, end)
        return AntimeridianCrossing(
            crosses=True,
            direction=direction,
            crossing_point=crossing_point,
            segment_index=segment_index,
        )

    def check_antimeridian_crossings(
        self, coords: List[Coordinate]
    ) -> List[AntimeridianCrossing]:
        results: list[AntimeridianCrossing] = []
        if len(coords) < 2:
            return results
        for i in range(len(coords) - 1):
            result = self.check_antimeridian_crossing(
                coords[i], coords[i + 1], segment_index=i
            )
            results.append(result)
        return results

    def check_polar_singularity(
        self, coord: Coordinate, index: Optional[int] = None
    ) -> PolarCheckResult:
        abs_lat = abs(coord.latitude)
        is_polar = abs(abs_lat - 90.0) < 1e-9
        is_near_polar = abs(abs_lat - 90.0) <= self._polar_threshold + 1e-9 and abs_lat <= 90.0 + 1e-9
        latitude_warning = None
        if abs_lat > 90.0:
            overshoot = abs_lat - 90.0
            latitude_warning = (
                f"latitude {coord.latitude} exceeds polar maximum by {overshoot:.6f} degrees"
            )
        elif is_near_polar and not is_polar:
            latitude_warning = (
                f"latitude {coord.latitude} is near the pole; "
                f"longitude values may be ambiguous"
            )
        return PolarCheckResult(
            index=index,
            is_polar=is_polar,
            is_near_polar=is_near_polar,
            latitude_warning=latitude_warning,
        )

    def check_polar_singularities(
        self, coords: List[Coordinate]
    ) -> List[PolarCheckResult]:
        return [self.check_polar_singularity(c, index=i) for i, c in enumerate(coords)]

    def validate_with_polar_awareness(
        self, coords: List[Coordinate]
    ) -> ValidationResult:
        base_result = self.validate_coordinates(coords)
        polar_results = self.check_polar_singularities(coords)

        merged: dict[int, dict] = {}
        for inv in base_result.invalid_coordinates:
            if inv.index is not None:
                merged[inv.index] = {
                    "latitude": inv.latitude,
                    "longitude": inv.longitude,
                    "reasons": [inv.reason],
                }

        for i, (coord, polar) in enumerate(zip(coords, polar_results)):
            if polar.latitude_warning is not None and "exceeds" in polar.latitude_warning:
                if i in merged:
                    merged[i]["reasons"].append(polar.latitude_warning)
                else:
                    merged[i] = {
                        "latitude": coord.latitude,
                        "longitude": coord.longitude,
                        "reasons": [polar.latitude_warning],
                    }

        all_invalid: list[InvalidCoordinate] = []
        for idx in sorted(merged.keys()):
            entry = merged[idx]
            all_invalid.append(
                InvalidCoordinate(
                    index=idx,
                    latitude=entry["latitude"],
                    longitude=entry["longitude"],
                    reason="; ".join(entry["reasons"]),
                )
            )
        return ValidationResult(
            valid=len(all_invalid) == 0, invalid_coordinates=all_invalid
        )

    def _determine_crossing_direction(
        self, start: Coordinate, end: Coordinate
    ) -> CrossingDirection:
        if end.longitude > start.longitude:
            if (end.longitude - start.longitude) > _CROSSING_LON_DIFF:
                return CrossingDirection.WESTWARD
            return CrossingDirection.EASTWARD
        else:
            if (start.longitude - end.longitude) > _CROSSING_LON_DIFF:
                return CrossingDirection.EASTWARD
            return CrossingDirection.WESTWARD

    def _compute_crossing_point(
        self, start: Coordinate, end: Coordinate
    ) -> Coordinate:
        d_lon = end.longitude - start.longitude
        if d_lon > _CROSSING_LON_DIFF:
            d_lon -= 360.0
        elif d_lon < -_CROSSING_LON_DIFF:
            d_lon += 360.0
        if d_lon == 0.0:
            crossing_lat = (start.latitude + end.latitude) / 2.0
        else:
            t = (180.0 - start.longitude) / d_lon if d_lon > 0 else (-180.0 - start.longitude) / d_lon
            crossing_lat = start.latitude + t * (end.latitude - start.latitude)
        crossing_lat = max(-90.0, min(90.0, crossing_lat))
        crossing_lon = 180.0 if start.longitude > 0 else -180.0
        return Coordinate(latitude=crossing_lat, longitude=crossing_lon)
