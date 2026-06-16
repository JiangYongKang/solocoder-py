class CollisionError(Exception):
    pass


class InvalidAABBError(CollisionError):
    pass


class InvalidGridSizeError(CollisionError):
    pass


class ColliderNotFoundError(CollisionError):
    pass
