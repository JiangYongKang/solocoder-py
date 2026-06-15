from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from .exceptions import InvalidVersionFormatError


VERSION_PATTERN = re.compile(
    r"^v(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-(\d{2}(?:-\d{2})?))?$"
)


@dataclass(frozen=True)
class ParsedVersion:
    raw: str
    major: int
    minor: int = 0
    patch: int = 0
    date_suffix: Optional[str] = None

    @classmethod
    def parse(cls, version_str: str) -> "ParsedVersion":
        if not version_str:
            raise InvalidVersionFormatError(version_str)
        match = VERSION_PATTERN.match(version_str.strip())
        if not match:
            raise InvalidVersionFormatError(version_str)
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0
        date_partial = match.group(4)
        date_suffix = None
        if date_partial is not None:
            date_suffix = f"{major}-{date_partial}"
        return cls(
            raw=version_str.strip(),
            major=major,
            minor=minor,
            patch=patch,
            date_suffix=date_suffix,
        )

    def is_compatible_with(self, requested: "ParsedVersion") -> bool:
        if self.date_suffix or requested.date_suffix:
            return self.raw == requested.raw
        if self.major != requested.major:
            return False
        if self.minor < requested.minor:
            return False
        if self.minor == requested.minor and self.patch < requested.patch:
            return False
        return True

    def __str__(self) -> str:
        return self.raw


class VersionHandler(Protocol):
    def __call__(self, request: "VersionedRequest") -> "VersionedResponse":
        ...


@dataclass
class VersionedRequest:
    path: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    query_params: dict[str, Any] = field(default_factory=dict)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return default


@dataclass
class VersionedResponse:
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None

    def set_header(self, name: str, value: str) -> None:
        self.headers[name] = value

    def get_header(self, name: str) -> Optional[str]:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return None


@dataclass
class VersionProcessor:
    version: str
    parsed_version: ParsedVersion
    handler: VersionHandler
    is_deprecated: bool = False
    sunset_at: Optional[float] = None
    deprecated_at: Optional[float] = None
    deprecation_message: Optional[str] = None
    compatible_with: list[str] = field(default_factory=list)

    def is_sunset_passed(self, now: float) -> bool:
        return self.sunset_at is not None and self.sunset_at <= now


@dataclass
class NegotiationResult:
    processor: VersionProcessor
    matched_exactly: bool
    used_default: bool
    matched_version: str


@dataclass
class VersionNegotiatorConfig:
    default_version: Optional[str] = None
    accept_version_header: str = "Accept-Version"
    deprecation_header: str = "Deprecation"
    sunset_header: str = "Sunset"
    deprecation_link_header: str = "Link"
    deprecation_link: Optional[str] = None
    strict_version_matching: bool = False
    require_version_header: bool = False

    def __post_init__(self) -> None:
        if self.accept_version_header is None:
            raise ValueError("accept_version_header must not be None")
        if self.deprecation_header is None:
            raise ValueError("deprecation_header must not be None")
        if self.sunset_header is None:
            raise ValueError("sunset_header must not be None")


__all__ = [
    "VERSION_PATTERN",
    "ParsedVersion",
    "VersionHandler",
    "VersionedRequest",
    "VersionedResponse",
    "VersionProcessor",
    "NegotiationResult",
    "VersionNegotiatorConfig",
]
