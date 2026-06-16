from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple

from .exceptions import InvalidAABBError, InvalidColliderError


@dataclass
class AABB:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        if self.max_x < self.min_x:
            raise InvalidAABBError(
                f"max_x ({self.max_x}) must be >= min_x ({self.min_x})"
            )
        if self.max_y < self.min_y:
            raise InvalidAABBError(
                f"max_y ({self.max_y}) must be >= min_y ({self.min_y})"
            )

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.min_x + self.max_x) / 2.0,
            (self.min_y + self.max_y) / 2.0,
        )

    def intersects(self, other: "AABB") -> bool:
        return (
            self.min_x <= other.max_x
            and self.max_x >= other.min_x
            and self.min_y <= other.max_y
            and self.max_y >= other.min_y
        )

    def contains(self, other: "AABB") -> bool:
        return (
            self.min_x <= other.min_x
            and self.max_x >= other.max_x
            and self.min_y <= other.min_y
            and self.max_y >= other.max_y
        )


@dataclass
class Collider:
    id: str
    aabb: AABB
    data: Any = None

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidColliderError("Collider id cannot be empty")

    @property
    def min_x(self) -> float:
        return self.aabb.min_x

    @property
    def min_y(self) -> float:
        return self.aabb.min_y

    @property
    def max_x(self) -> float:
        return self.aabb.max_x

    @property
    def max_y(self) -> float:
        return self.aabb.max_y

    def intersects(self, other: "Collider") -> bool:
        return self.aabb.intersects(other.aabb)


@dataclass
class CollisionPair:
    """
    Represents a pair of colliding Colliders.

    IMPORTANT: Upon construction, the two colliders are automatically
    reordered by their IDs in lexicographic ascending order to ensure
    consistent normalization. This means:
      - collider_a.id will always be <= collider_b.id
      - The object originally passed as collider_a may end up as
        collider_b (and vice versa) after construction.

    This normalization guarantees that CollisionPair(A, B) and
    CollisionPair(B, A) are equal and have the same hash.
    """

    collider_a: Collider
    collider_b: Collider

    def __post_init__(self) -> None:
        if self.collider_a.id > self.collider_b.id:
            self.collider_a, self.collider_b = self.collider_b, self.collider_a

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionPair):
            return False
        return (
            self.collider_a.id == other.collider_a.id
            and self.collider_b.id == other.collider_b.id
        )

    def __hash__(self) -> int:
        return hash((self.collider_a.id, self.collider_b.id))
