from __future__ import annotations


class GeoSearchError(Exception):
    pass


class InvalidLatitudeError(GeoSearchError):
    pass


class InvalidLongitudeError(GeoSearchError):
    pass


class InvalidRadiusError(GeoSearchError):
    pass


class InvalidCoordinateError(GeoSearchError):
    pass
