from __future__ import annotations

from typing import Optional


class VersionNegotiatorError(Exception):
    pass


class VersionNotFoundError(VersionNegotiatorError):
    def __init__(self, requested_version: str, available_versions: list[str]) -> None:
        super().__init__(
            f"Version '{requested_version}' not found. Available versions: {available_versions}"
        )
        self.requested_version = requested_version
        self.available_versions = available_versions


class DuplicateVersionError(VersionNegotiatorError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Version '{version}' is already registered")
        self.version = version


class VersionDeprecatedError(VersionNegotiatorError):
    def __init__(self, version: str, sunset_at: float) -> None:
        super().__init__(
            f"Version '{version}' was deprecated and sunset at {sunset_at}"
        )
        self.version = version
        self.sunset_at = sunset_at


class InvalidVersionFormatError(VersionNegotiatorError):
    def __init__(self, version: str) -> None:
        super().__init__(f"Invalid version format: '{version}'")
        self.version = version


class EmptyProcessorRegistryError(VersionNegotiatorError):
    def __init__(self) -> None:
        super().__init__("No version processors registered")


class DefaultVersionNotSetError(VersionNegotiatorError):
    def __init__(self) -> None:
        super().__init__("Default version is not set")


class InvalidCompatibilityError(VersionNegotiatorError):
    def __init__(self, from_version: str, to_version: str) -> None:
        super().__init__(
            f"Invalid compatibility: cannot register version '{to_version}' as compatible with '{from_version}' (which is not registered)"
        )
        self.from_version = from_version
        self.to_version = to_version


__all__ = [
    "VersionNegotiatorError",
    "VersionNotFoundError",
    "DuplicateVersionError",
    "VersionDeprecatedError",
    "InvalidVersionFormatError",
    "EmptyProcessorRegistryError",
    "DefaultVersionNotSetError",
    "InvalidCompatibilityError",
]
