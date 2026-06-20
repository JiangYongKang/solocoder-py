from __future__ import annotations

import hashlib
import pickle
import struct
from typing import Any, Callable, Iterable, Optional

from .exceptions import (
    IncompatibleSignatureError,
    InvalidConfigError,
    NonHashableElementError,
)


def _serialize(element: Any) -> bytes:
    try:
        hash(element)
    except TypeError as e:
        raise NonHashableElementError(
            f"Element {element!r} is not hashable: {e}"
        ) from e
    try:
        return pickle.dumps(element)
    except (pickle.PicklingError, TypeError, AttributeError) as e:
        raise NonHashableElementError(
            f"Element {element!r} is not hashable: {e}"
        ) from e


def _make_hash_fn(seed: int) -> Callable[[bytes], int]:
    def hash_fn(data: bytes) -> int:
        h = hashlib.sha256()
        h.update(struct.pack("<I", seed))
        h.update(data)
        digest = h.digest()
        return struct.unpack("<Q", digest[:8])[0]

    return hash_fn


class MinHash:
    _MAX_SEED = 2**32 - 1

    def __init__(
        self,
        num_hash_functions: int = 128,
        seed: int = 42,
        elements: Optional[Iterable[Any]] = None,
    ) -> None:
        if not isinstance(num_hash_functions, int):
            raise InvalidConfigError(
                "num_hash_functions must be an integer"
            )
        if num_hash_functions <= 0:
            raise InvalidConfigError(
                "num_hash_functions must be a positive integer"
            )

        self._num_hash_functions = num_hash_functions
        self._seed = seed
        self._hash_fns: list[Callable[[bytes], int]] = [
            _make_hash_fn((seed + i) % self._MAX_SEED)
            for i in range(num_hash_functions)
        ]
        self._signature: list[int] = [
            0xFFFFFFFFFFFFFFFF for _ in range(num_hash_functions)
        ]

        if elements is not None:
            self.add_many(elements)

    @property
    def h(self) -> int:
        return self._num_hash_functions

    @property
    def num_hash_functions(self) -> int:
        return self._num_hash_functions

    @property
    def signature(self) -> list[int]:
        return list(self._signature)

    def _is_empty(self) -> bool:
        return all(sig == 0xFFFFFFFFFFFFFFFF for sig in self._signature)

    def add(self, element: Any) -> None:
        data = _serialize(element)
        for i, hash_fn in enumerate(self._hash_fns):
            hash_val = hash_fn(data)
            if hash_val < self._signature[i]:
                self._signature[i] = hash_val

    def add_many(self, elements: Iterable[Any]) -> None:
        for element in elements:
            self.add(element)

    def update(self, elements: Iterable[Any]) -> None:
        self.add_many(elements)

    @classmethod
    def from_set(
        cls,
        elements: Iterable[Any],
        num_hash_functions: int = 128,
        seed: int = 42,
    ) -> "MinHash":
        return cls(
            num_hash_functions=num_hash_functions,
            seed=seed,
            elements=elements,
        )

    def is_compatible(self, other: "MinHash") -> bool:
        if not isinstance(other, MinHash):
            return False
        return (
            self._num_hash_functions == other._num_hash_functions
            and self._seed == other._seed
        )

    def _check_compatible(self, other: "MinHash") -> None:
        if not isinstance(other, MinHash):
            raise IncompatibleSignatureError(
                f"Signatures are incompatible: "
                f"other is not a MinHash instance, got {type(other).__name__}"
            )
        if not self.is_compatible(other):
            raise IncompatibleSignatureError(
                f"Signatures are incompatible: "
                f"self has h={self._num_hash_functions}, seed={self._seed}; "
                f"other has h={other._num_hash_functions}, seed={other._seed}"
            )

    def jaccard(self, other: "MinHash") -> float:
        self._check_compatible(other)
        if self._is_empty() and other._is_empty():
            return 1.0
        matches = sum(
            1
            for a, b in zip(self._signature, other._signature)
            if a == b
        )
        return matches / self._num_hash_functions

    def merge(self, other: "MinHash") -> "MinHash":
        self._check_compatible(other)
        result = MinHash(
            num_hash_functions=self._num_hash_functions,
            seed=self._seed,
        )
        result._signature = [
            min(a, b)
            for a, b in zip(self._signature, other._signature)
        ]
        return result

    def __or__(self, other: "MinHash") -> "MinHash":
        return self.merge(other)

    def __ior__(self, other: "MinHash") -> "MinHash":
        self._check_compatible(other)
        self._signature = [
            min(a, b)
            for a, b in zip(self._signature, other._signature)
        ]
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MinHash):
            return NotImplemented
        if not self.is_compatible(other):
            return False
        return self._signature == other._signature

    def __len__(self) -> int:
        return self._num_hash_functions

    def __repr__(self) -> str:
        return (
            f"MinHash(num_hash_functions={self._num_hash_functions}, "
            f"seed={self._seed})"
        )


def jaccard_similarity(set_a: set[Any], set_b: set[Any]) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union
