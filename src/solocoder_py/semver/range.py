from __future__ import annotations

import re
from typing import Optional

from .exceptions import InvalidRangeError
from .version import SemverVersion

_CONDITION_PATTERN = re.compile(r"^(>=|<=|>|<|=)(.+)$")

_VALID_OPERATORS = {">=", "<=", ">", "<", "="}


class VersionRange:
    __slots__ = ("_conditions",)

    def __init__(self, conditions: Optional[list[tuple[str, SemverVersion]]] = None) -> None:
        self._conditions: list[tuple[str, SemverVersion]] = conditions or []

    @classmethod
    def parse(cls, range_str: str) -> VersionRange:
        if not isinstance(range_str, str):
            raise InvalidRangeError("Range expression must be a string")

        stripped = range_str.strip()
        if not stripped:
            raise InvalidRangeError("Range expression must not be empty")

        tokens = stripped.split()
        conditions: list[tuple[str, SemverVersion]] = []

        for token in tokens:
            match = _CONDITION_PATTERN.match(token)
            if not match:
                raise InvalidRangeError(
                    f"Invalid range condition: '{token}'. "
                    f"Expected format: <operator><version> where operator is one of {sorted(_VALID_OPERATORS)}"
                )

            op = match.group(1)
            ver_str = match.group(2)

            try:
                ver = SemverVersion.parse(ver_str)
            except Exception as e:
                raise InvalidRangeError(
                    f"Invalid version in range condition '{token}': {e}"
                ) from e

            conditions.append((op, ver))

        if not conditions:
            raise InvalidRangeError("Range expression must contain at least one condition")

        return cls(conditions)

    def satisfies(self, version: SemverVersion) -> bool:
        for op, target in self._conditions:
            if not self._check_condition(op, version, target):
                return False
        return True

    @staticmethod
    def _check_condition(op: str, version: SemverVersion, target: SemverVersion) -> bool:
        if op == "=":
            return version == target
        if op == ">=":
            return version >= target
        if op == ">":
            return version > target
        if op == "<=":
            return version <= target
        if op == "<":
            return version < target
        return False

    @property
    def conditions(self) -> list[tuple[str, SemverVersion]]:
        return list(self._conditions)

    def __str__(self) -> str:
        parts = []
        for op, ver in self._conditions:
            parts.append(f"{op}{ver.without_build_metadata()}")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"VersionRange.parse('{self}')"
