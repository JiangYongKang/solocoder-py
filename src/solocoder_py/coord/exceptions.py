class CoordError(Exception):
    pass


class InvalidBoundsError(CoordError):
    pass


class NonFiniteCoordinateError(CoordError):
    pass
