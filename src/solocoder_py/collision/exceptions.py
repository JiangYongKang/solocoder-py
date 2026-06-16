class CollisionError(Exception):
    pass


class InvalidAABBError(CollisionError):
    pass


class InvalidColliderError(CollisionError):
    pass


class InvalidGridSizeError(CollisionError):
    pass


class ColliderNotFoundError(CollisionError):
    pass
