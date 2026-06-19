from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


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
