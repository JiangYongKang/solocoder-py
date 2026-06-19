class PipError(Exception):
    pass


class InvalidPointError(PipError):
    pass


class InvalidPolygonError(PipError):
    pass


class EmptyPolygonError(InvalidPolygonError):
    pass


class InsufficientVerticesError(InvalidPolygonError):
    pass


class InvalidCoordinateError(InvalidPointError):
    pass
