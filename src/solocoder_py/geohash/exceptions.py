from __future__ import annotations


class GeohashError(Exception):
    pass


class InvalidLatitudeError(GeohashError):
    pass


class InvalidLongitudeError(GeohashError):
    pass


class InvalidPrecisionError(GeohashError):
    pass


class InvalidGeohashCharacterError(GeohashError):
    pass


class EmptyGeohashError(GeohashError):
    pass
