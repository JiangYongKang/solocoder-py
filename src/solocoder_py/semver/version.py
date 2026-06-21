from __future__ import annotations

import re
from functools import total_ordering
from typing import Optional

from .exceptions import InvalidVersionError

_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
    r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

_PRERELEASE_ID_PATTERN = re.compile(r"^(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)$")
_BUILD_ID_PATTERN = re.compile(r"^[0-9a-zA-Z-]+$")


def _validate_prerelease(prerelease: str) -> None:
    if not isinstance(prerelease, str):
        raise InvalidVersionError("Prerelease must be a string")
    if not prerelease:
        raise InvalidVersionError("Prerelease must not be empty")
    for part in prerelease.split("."):
        if not part:
            raise InvalidVersionError(f"Empty prerelease identifier in '{prerelease}'")
        if not _PRERELEASE_ID_PATTERN.match(part):
            raise InvalidVersionError(
                f"Invalid prerelease identifier '{part}' in '{prerelease}' "
                "(numeric identifiers must not have leading zeros)"
            )


def _validate_build_metadata(build_metadata: str) -> None:
    if not isinstance(build_metadata, str):
        raise InvalidVersionError("Build metadata must be a string")
    if not build_metadata:
        raise InvalidVersionError("Build metadata must not be empty")
    for part in build_metadata.split("."):
        if not part:
            raise InvalidVersionError(
                f"Empty build metadata identifier in '{build_metadata}'"
            )
        if not _BUILD_ID_PATTERN.match(part):
            raise InvalidVersionError(
                f"Invalid build metadata identifier '{part}' in '{build_metadata}' "
                "(only alphanumeric characters and hyphens are allowed)"
            )


@total_ordering
class SemverVersion:
    __slots__ = (
        "major",
        "minor",
        "patch",
        "prerelease",
        "build_metadata",
        "_prerelease_ids",
    )

    def __init__(
        self,
        major: int,
        minor: int = 0,
        patch: int = 0,
        prerelease: Optional[str] = None,
        build_metadata: Optional[str] = None,
    ) -> None:
        if not isinstance(major, int) or not isinstance(minor, int) or not isinstance(patch, int):
            raise InvalidVersionError("Version numbers must be integers")
        if major < 0 or minor < 0 or patch < 0:
            raise InvalidVersionError("Version numbers must be non-negative")
        if prerelease is not None:
            _validate_prerelease(prerelease)
        if build_metadata is not None:
            _validate_build_metadata(build_metadata)
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build_metadata = build_metadata
        self._prerelease_ids: list[int | str] = self._parse_prerelease_ids(prerelease)

    @staticmethod
    def _parse_prerelease_ids(prerelease: Optional[str]) -> list[int | str]:
        if prerelease is None:
            return []
        ids: list[int | str] = []
        for part in prerelease.split("."):
            if part.isdigit():
                ids.append(int(part))
            else:
                ids.append(part)
        return ids

    @classmethod
    def parse(cls, version_str: str) -> SemverVersion:
        if not isinstance(version_str, str):
            raise InvalidVersionError("Version string must be a string")

        stripped = version_str.strip()
        if not stripped:
            raise InvalidVersionError("Version string must not be empty")

        match = _SEMVER_PATTERN.match(stripped)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3))
            prerelease = match.group(4)
            build_metadata = match.group(5)
            return cls(major, minor, patch, prerelease, build_metadata)

        cls._diagnose_invalid_version(stripped, version_str)

    @classmethod
    def _diagnose_invalid_version(cls, stripped: str, original: str) -> None:
        build_idx = stripped.rfind("+")
        build_metadata = None
        core_part = stripped
        if build_idx != -1:
            build_metadata = stripped[build_idx + 1 :]
            core_part = stripped[:build_idx]

        prerelease = None
        version_core = core_part
        prerelease_idx = core_part.find("-")
        if prerelease_idx != -1:
            prerelease = core_part[prerelease_idx + 1 :]
            version_core = core_part[:prerelease_idx]

        core_parts = version_core.split(".")
        if len(core_parts) != 3:
            raise InvalidVersionError(
                f"Invalid semver string: '{original}' "
                "(version core must have exactly three parts: MAJOR.MINOR.PATCH)"
            )

        for i, part in enumerate(core_parts):
            name = ["MAJOR", "MINOR", "PATCH"][i]
            if not part:
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' "
                    f"({name} version must not be empty)"
                )
            if not part.isdigit():
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' "
                    f"({name} version must be a non-negative integer)"
                )
            if len(part) > 1 and part[0] == "0":
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' "
                    f"({name} version must not have leading zeros)"
                )
            if int(part) < 0:
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' "
                    f"({name} version must be non-negative)"
                )

        if prerelease is not None:
            try:
                _validate_prerelease(prerelease)
            except InvalidVersionError as e:
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' ({e})"
                ) from e

        if build_metadata is not None:
            try:
                _validate_build_metadata(build_metadata)
            except InvalidVersionError as e:
                raise InvalidVersionError(
                    f"Invalid semver string: '{original}' ({e})"
                ) from e

        raise InvalidVersionError(f"Invalid semver string: '{original}'")

    def without_build_metadata(self) -> str:
        parts = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            parts += f"-{self.prerelease}"
        return parts

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is not None:
            result += f"-{self.prerelease}"
        if self.build_metadata is not None:
            result += f"+{self.build_metadata}"
        return result

    def __repr__(self) -> str:
        return f"SemverVersion.parse('{self}')"

    def _comparison_key(self) -> tuple:
        prerelease_key: list[tuple[int, int, str]] = []
        if self.prerelease is not None:
            for pid in self._prerelease_ids:
                if isinstance(pid, int):
                    prerelease_key.append((0, pid, ""))
                else:
                    prerelease_key.append((1, 0, pid))
        if self.prerelease is None:
            return (self.major, self.minor, self.patch, (1,))
        return (self.major, self.minor, self.patch, (0, tuple(prerelease_key)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemverVersion):
            return NotImplemented
        return self._comparison_key() == other._comparison_key()

    def __lt__(self, other: SemverVersion) -> bool:
        if not isinstance(other, SemverVersion):
            return NotImplemented
        return self._comparison_key() < other._comparison_key()

    def __hash__(self) -> int:
        return hash(self._comparison_key())
