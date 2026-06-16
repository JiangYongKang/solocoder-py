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

    Normalization behavior
    ----------------------
    By default, CollisionPair normalizes the two colliders upon
    construction so that collider_a.id <= collider_b.id. This ensures
    that CollisionPair(A, B) and CollisionPair(B, A) are equal and have
    the same hash, which is useful for deduplication in sets and dicts.

    Use the ``was_swapped`` attribute to check whether the arguments
    were reordered during construction.

    Factory methods
    ---------------
    - ``from_unordered(a, b)``: Explicitly constructs a normalized pair
      (same as the default constructor, but makes the intent clear).
    - ``from_ordered(a, b)``: Preserves the given order without
      swapping. Use this when you care about which collider is "first"
      and which is "second".
    """

    collider_a: Collider
    collider_b: Collider
    was_swapped: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.collider_a.id > self.collider_b.id:
            self.collider_a, self.collider_b = self.collider_b, self.collider_a
            self.was_swapped = True

    @classmethod
    def from_unordered(cls, collider_a: Collider, collider_b: Collider) -> "CollisionPair":
        """
        Create a CollisionPair with automatic normalization by ID.

        This is equivalent to the default constructor, but the method
        name makes it explicit that the pair will be reordered so that
        ``collider_a.id <= collider_b.id``.

        Use ``pair.was_swapped`` to check whether the inputs were
        swapped during construction.

        Args:
            collider_a: First collider (order may change).
            collider_b: Second collider (order may change).

        Returns:
            A normalized CollisionPair.
        """
        return cls(collider_a=collider_a, collider_b=collider_b)

    @classmethod
    def from_ordered(cls, collider_a: Collider, collider_b: Collider) -> "CollisionPair":
        """
        Create a CollisionPair preserving the given order.

        Unlike the default constructor and ``from_unordered``, this
        factory method does NOT reorder the colliders by ID. The
        collider passed as ``collider_a`` stays as ``collider_a``, and
        the one passed as ``collider_b`` stays as ``collider_b``.

        ``was_swapped`` will always be ``False`` for pairs created via
        this method.

        Use this constructor when the ordering of the two colliders
        carries meaning (e.g. "source" vs "target", "actor" vs "victim")
        and you don't want the pair to be silently reordered.

        Note: Pairs created with this constructor are NOT guaranteed
        to be equal to pairs created with the default constructor if
        the IDs are in descending order, because their ``collider_a`` /
        ``collider_b`` assignments differ.

        Args:
            collider_a: First collider (order is preserved).
            collider_b: Second collider (order is preserved).

        Returns:
            A CollisionPair in the exact order given.
        """
        pair = cls.__new__(cls)
        pair.collider_a = collider_a
        pair.collider_b = collider_b
        pair.was_swapped = False
        return pair

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CollisionPair):
            return False
        return (
            self.collider_a.id == other.collider_a.id
            and self.collider_b.id == other.collider_b.id
        )

    def __hash__(self) -> int:
        return hash((self.collider_a.id, self.collider_b.id))
