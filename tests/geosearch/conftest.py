import pytest

from solocoder_py.geosearch import GeoPoint


@pytest.fixture
def beijing_center():
    return GeoPoint(latitude=39.9042, longitude=116.4074)


@pytest.fixture
def equator_center():
    return GeoPoint(latitude=0.0, longitude=0.0)


@pytest.fixture
def north_pole_center():
    return GeoPoint(latitude=89.0, longitude=0.0)


@pytest.fixture
def candidates_around_beijing():
    return [
        GeoPoint(latitude=39.9042, longitude=116.4074),
        GeoPoint(latitude=39.9142, longitude=116.4074),
        GeoPoint(latitude=39.8942, longitude=116.4074),
        GeoPoint(latitude=39.9042, longitude=116.4174),
        GeoPoint(latitude=39.9042, longitude=116.3974),
        GeoPoint(latitude=39.9542, longitude=116.4074),
        GeoPoint(latitude=39.8542, longitude=116.4074),
        GeoPoint(latitude=39.9042, longitude=116.4574),
        GeoPoint(latitude=39.9042, longitude=116.3574),
        GeoPoint(latitude=40.0, longitude=116.5),
        GeoPoint(latitude=39.8, longitude=116.3),
        GeoPoint(latitude=31.2304, longitude=121.4737),
        GeoPoint(latitude=31.2304, longitude=121.4737),
    ]
