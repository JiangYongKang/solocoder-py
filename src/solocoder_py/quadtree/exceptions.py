class QuadtreeError(Exception):
    pass


class OutOfBoundsError(QuadtreeError):
    pass


class DuplicatePointError(QuadtreeError):
    pass


class InvalidCapacityError(QuadtreeError):
    pass


class InvalidDepthError(QuadtreeError):
    pass


class InvalidRectangleError(QuadtreeError):
    pass
