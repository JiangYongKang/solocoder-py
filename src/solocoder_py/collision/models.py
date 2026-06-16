from __future__ import annotations

import warnings
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

    When the default constructor reorders its arguments (i.e. when the
    first argument ends up as collider_b), a RuntimeWarning is emitted
    at construction time so callers can notice the reordering even
    without reading the documentation. Use ``pair.was_swapped`` to
    programmatically check whether a swap occurred.

    Factory methods
    ---------------
    - ``from_unordered(a, b)``: Explicitly constructs a normalized pair
      (same as the default constructor, but makes the intent clear).
      Still emits a RuntimeWarning when reordering occurs.
    - ``from_ordered(a, b)``: Preserves the given order without
      swapping and without warning. Use this when you care about which
      collider is "first" and which is "second".
    """

    collider_a: Collider
    collider_b: Collider
    was_swapped: bool = field(init=False, default=False)
    _preserve_order: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        if self._preserve_order:
            self.was_swapped = False
            return
        if self.collider_a.id > self.collider_b.id:
            original_a_id = self.collider_a.id
            original_b_id = self.collider_b.id
            self.collider_a, self.collider_b = self.collider_b, self.collider_a
            self.was_swapped = True
            warnings.warn(
                f"CollisionPair arguments were reordered by ID: "
                f"collider with id '{original_a_id}' was passed as collider_a "
                f"but is now collider_b, and collider with id '{original_b_id}' "
                f"was passed as collider_b but is now collider_a. "
                f"Use CollisionPair.from_ordered() to preserve the input order "
                f"and suppress this warning.",
                category=RuntimeWarning,
                stacklevel=2,
            )

    @classmethod
    def from_unordered(cls, collider_a: Collider, collider_b: Collider) -> "CollisionPair":
        """
        Create a CollisionPair with automatic normalization by ID.

        This is equivalent to the default constructor, but the method
        name makes it explicit that the pair will be reordered so that
        ``collider_a.id <= collider_b.id``.

        A RuntimeWarning is emitted if the inputs are swapped during
        construction. Use ``pair.was_swapped`` to check this
        programmatically.

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
        factory method does NOT reorder the colliders by ID and does
        NOT emit a reordering warning. The collider passed as
        ``collider_a`` stays as ``collider_a``, and the one passed as
        ``collider_b`` stays as ``collider_b``.

        ``was_swapped`` will always be ``False`` for pairs created via
        this method.

        Internally, this method sets a private ``_preserve_order``
        flag before allowing ``__post_init__`` to run, so all
        validation logic in ``__post_init__`` still executes uniformly
        across every construction path.

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
        pair._preserve_order = True
        pair.__post_init__()
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
