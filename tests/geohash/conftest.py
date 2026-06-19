from __future__ import annotations

import pytest


@pytest.fixture
def known_geohashes():
    return [
        {"lat": 37.371, "lon": -122.031, "precision": 6, "geohash": "9q9hx5"},
        {"lat": 39.9087, "lon": 116.3975, "precision": 8, "geohash": "wx4g09nj"},
        {"lat": 51.5074, "lon": -0.1278, "precision": 6, "geohash": "gcpvj0"},
        {"lat": -33.8688, "lon": 151.2093, "precision": 6, "geohash": "r3gx2f"},
    ]


@pytest.fixture
def precision_errors():
    return [
        (p, 90.0 / (2 ** (5 * p // 2)), 180.0 / (2 ** ((5 * p + 1) // 2)))
        for p in range(1, 13)
    ]
