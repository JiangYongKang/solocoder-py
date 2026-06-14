from __future__ import annotations

import threading
from typing import Optional, Sequence

from .exceptions import (
    DimensionPathError,
    DimensionStructureMismatchError,
    InvalidDimensionError,
    MergeError,
)
from .models import CounterState, DimensionSchema


class MultiDimCounter:
    def __init__(
        self,
        schema: Optional[DimensionSchema] = None,
        levels: Optional[Sequence[str]] = None,
    ) -> None:
        if schema is not None and levels is not None:
            raise ValueError("provide either schema or levels, not both")
        if schema is None and levels is None:
            raise ValueError("either schema or levels must be provided")
        if levels is not None:
            schema = DimensionSchema(levels=list(levels))
        self._schema = schema
        self._counts: dict[tuple[str, ...], int] = {}
        self._lock = threading.RLock()

    @property
    def schema(self) -> DimensionSchema:
        return self._schema

    @property
    def max_depth(self) -> int:
        return self._schema.max_depth

    @classmethod
    def from_state(cls, state: CounterState) -> "MultiDimCounter":
        obj = cls(schema=state.schema)
        with obj._lock:
            obj._counts = dict(state.counts)
        return obj

    def get_state(self) -> CounterState:
        with self._lock:
            return CounterState(
                schema=DimensionSchema(levels=list(self._schema.levels)),
                counts=dict(self._counts),
            )

    @staticmethod
    def _parse_path(path: str) -> tuple[str, ...]:
        if not isinstance(path, str):
            raise DimensionPathError("dimension path must be a string")
        if not path:
            raise DimensionPathError("dimension path cannot be empty")
        parts = path.split("/")
        for part in parts:
            if not part:
                raise DimensionPathError(
                    "dimension path contains empty segment"
                )
        return tuple(parts)

    def _validate_path_parts(self, path_parts: tuple[str, ...]) -> None:
        self._schema.validate_path(list(path_parts))

    def _validate_full_path(self, path_parts: tuple[str, ...]) -> None:
        self._validate_path_parts(path_parts)
        if not self._schema.is_full_path(list(path_parts)):
            raise DimensionPathError(
                f"path depth {len(path_parts)} does not match required depth "
                f"{self._schema.max_depth} for increment operations; "
                f"full dimension path is required"
            )

    def increment(self, path: str, delta: int = 1) -> None:
        path_parts = self._parse_path(path)
        self._validate_full_path(path_parts)

        if delta == 0:
            return

        with self._lock:
            leaf_key = path_parts
            old_leaf = self._counts.get(leaf_key, 0)
            new_leaf = old_leaf + delta
            if new_leaf < 0:
                new_leaf = 0
            actual_delta = new_leaf - old_leaf

            if actual_delta == 0:
                return

            for i in range(1, len(path_parts) + 1):
                ancestor = path_parts[:i]
                self._counts[ancestor] = (
                    self._counts.get(ancestor, 0) + actual_delta
                )

    def decrement(self, path: str, delta: int = 1) -> None:
        if delta < 0:
            raise ValueError("delta must be non-negative")
        self.increment(path, -delta)

    def query(self, path: str) -> int:
        path_parts = self._parse_path(path)
        try:
            self._validate_path_parts(path_parts)
        except InvalidDimensionError:
            return 0
        with self._lock:
            return self._counts.get(path_parts, 0)

    def query_children(self, path: str = "") -> dict[str, int]:
        if path == "":
            path_parts: tuple[str, ...] = ()
        else:
            path_parts = self._parse_path(path)
            try:
                self._validate_path_parts(path_parts)
            except InvalidDimensionError:
                return {}

        depth = len(path_parts)
        result: dict[str, int] = {}
        with self._lock:
            for key, value in self._counts.items():
                if len(key) == depth + 1 and key[:depth] == path_parts:
                    result[key[-1]] = value
        return result

    def merge(self, other: "MultiDimCounter") -> None:
        if not isinstance(other, MultiDimCounter):
            raise MergeError("can only merge with another MultiDimCounter")
        if other._schema.levels != self._schema.levels:
            raise DimensionStructureMismatchError(
                "cannot merge counters with different dimension schemas"
            )

        with self._lock, other._lock:
            for path_parts, count in other._counts.items():
                self._counts[path_parts] = (
                    self._counts.get(path_parts, 0) + count
                )

    def total(self) -> int:
        with self._lock:
            total = 0
            for key, value in self._counts.items():
                if len(key) == 1:
                    total += value
            return total

    def all_paths(self) -> list[tuple[str, ...]]:
        with self._lock:
            return list(self._counts.keys())

    def __contains__(self, path: str) -> bool:
        path_parts = self._parse_path(path)
        with self._lock:
            return path_parts in self._counts

    def __getitem__(self, path: str) -> int:
        return self.query(path)

