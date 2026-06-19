class CoordError(Exception):
    pass


class InvalidCoordinateError(CoordError):
    pass


class InvalidBoundsError(CoordError):
    pass


class NonFiniteCoordinateError(CoordError):
    pass
