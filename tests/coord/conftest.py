from solocoder_py.coord import CoordValidator, Coordinate, BoundingBox


def make_validator() -> CoordValidator:
    return CoordValidator()


def make_coordinate(lat: float, lon: float) -> Coordinate:
    return Coordinate(latitude=lat, longitude=lon)


def make_bounds(
    min_lat: float = -90.0,
    max_lat: float = 90.0,
    min_lon: float = -180.0,
    max_lon: float = 180.0,
) -> BoundingBox:
    return BoundingBox(
        min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon
    )
