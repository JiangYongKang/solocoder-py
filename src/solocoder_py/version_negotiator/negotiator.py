from __future__ import annotations

import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol

from .exceptions import (
    DefaultVersionNotSetError,
    DuplicateVersionError,
    EmptyProcessorRegistryError,
    InvalidCompatibilityError,
    InvalidVersionFormatError,
    VersionDeprecatedError,
    VersionNegotiatorError,
    VersionNotFoundError,
)
from .models import (
    NegotiationResult,
    ParsedVersion,
    VersionHandler,
    VersionedRequest,
    VersionedResponse,
    VersionNegotiatorConfig,
    VersionProcessor,
)


class Clock(Protocol):
    def now(self) -> float:
        ...


class SystemClock:
    def now(self) -> float:
        import datetime
        return datetime.datetime.now(datetime.timezone.utc).timestamp()


class VersionNegotiator:
    def __init__(
        self,
        config: Optional[VersionNegotiatorConfig] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._config = config or VersionNegotiatorConfig()
        self._clock: Clock = clock or SystemClock()
        self._processors: Dict[str, VersionProcessor] = {}
        self._parsed_versions: Dict[str, ParsedVersion] = {}

    def register(
        self,
        version: str,
        handler: VersionHandler,
        is_deprecated: bool = False,
        sunset_at: Optional[float] = None,
        deprecated_at: Optional[float] = None,
        deprecation_message: Optional[str] = None,
        compatible_with: Optional[List[str]] = None,
    ) -> VersionProcessor:
        if version in self._processors:
            raise DuplicateVersionError(version)

        parsed = ParsedVersion.parse(version)
        self._parsed_versions[version] = parsed

        compatible_versions = compatible_with or []
        for compat_version in compatible_versions:
            if compat_version not in self._processors:
                raise InvalidCompatibilityError(compat_version, version)

        processor = VersionProcessor(
            version=version,
            parsed_version=parsed,
            handler=handler,
            is_deprecated=is_deprecated,
            sunset_at=sunset_at,
            deprecated_at=deprecated_at,
            deprecation_message=deprecation_message,
            compatible_with=compatible_versions,
        )

        self._processors[version] = processor
        return processor

    def unregister(self, version: str) -> None:
        if version in self._processors:
            del self._processors[version]
            del self._parsed_versions[version]

    def get_processor(self, version: str) -> Optional[VersionProcessor]:
        return self._processors.get(version)

    def list_versions(self) -> List[str]:
        return list(self._processors.keys())

    def set_default_version(self, version: str) -> None:
        if version not in self._processors:
            raise VersionNotFoundError(version, self.list_versions())
        self._config.default_version = version

    def get_default_version(self) -> str:
        if self._config.default_version is None:
            raise DefaultVersionNotSetError()
        return self._config.default_version

    def negotiate(self, request: VersionedRequest) -> NegotiationResult:
        if not self._processors:
            raise EmptyProcessorRegistryError()

        version_header = request.get_header(self._config.accept_version_header)

        if version_header is None or version_header.strip() == "":
            if self._config.require_version_header:
                raise VersionNotFoundError(
                    "none", self.list_versions()
                )
            return self._negotiate_default()

        try:
            requested_parsed = ParsedVersion.parse(version_header)
        except InvalidVersionFormatError:
            raise VersionNotFoundError(version_header, self.list_versions())

        exact_match = self._find_exact_match(requested_parsed)
        if exact_match is not None:
            return NegotiationResult(
                processor=exact_match,
                matched_exactly=True,
                used_default=False,
                matched_version=exact_match.version,
            )

        if not self._config.strict_version_matching:
            compatible_match = self._find_compatible_match(requested_parsed)
            if compatible_match is not None:
                return NegotiationResult(
                    processor=compatible_match,
                    matched_exactly=False,
                    used_default=False,
                    matched_version=compatible_match.version,
                )

        raise VersionNotFoundError(requested_parsed.raw, self.list_versions())

    def process(self, request: VersionedRequest) -> VersionedResponse:
        result = self.negotiate(request)
        processor = result.processor

        now = self._clock.now()
        if processor.is_deprecated and processor.is_sunset_passed(now):
            raise VersionDeprecatedError(processor.version, processor.sunset_at)

        response = processor.handler(request)

        if response is None:
            response = VersionedResponse()

        if processor.is_deprecated:
            self._add_deprecation_headers(response, processor)

        response.set_header("X-API-Version", processor.version)
        if not result.matched_exactly and not result.used_default:
            response.set_header(
                "X-API-Version-Matched-As", "compatible"
            )
        elif result.used_default:
            response.set_header("X-API-Version-Matched-As", "default")

        return response

    def _negotiate_default(self) -> NegotiationResult:
        default_version = self.get_default_version()
        processor = self._processors.get(default_version)
        if processor is None:
            raise VersionNotFoundError(default_version, self.list_versions())
        return NegotiationResult(
            processor=processor,
            matched_exactly=True,
            used_default=True,
            matched_version=default_version,
        )

    def _find_exact_match(self, requested: ParsedVersion) -> Optional[VersionProcessor]:
        for processor in self._processors.values():
            if processor.parsed_version.raw == requested.raw:
                return processor
        return None

    def _find_compatible_match(self, requested: ParsedVersion) -> Optional[VersionProcessor]:
        best_match: Optional[VersionProcessor] = None

        for processor in self._processors.values():
            if processor.parsed_version.is_compatible_with(requested):
                if best_match is None or self._is_better_compatible_match(
                    processor, best_match, requested
                ):
                    best_match = processor
            else:
                for compat_version in processor.compatible_with:
                    if compat_version == requested.raw:
                        if best_match is None or self._is_better_compatible_match(
                            processor, best_match, requested
                        ):
                            best_match = processor

        return best_match

    def _is_better_compatible_match(
        self,
        candidate: VersionProcessor,
        current_best: VersionProcessor,
        requested: ParsedVersion,
    ) -> bool:
        if requested.date_suffix:
            return False

        cand_parsed = candidate.parsed_version
        best_parsed = current_best.parsed_version

        if cand_parsed.major != best_parsed.major:
            return cand_parsed.major > best_parsed.major
        if cand_parsed.minor != best_parsed.minor:
            return cand_parsed.minor > best_parsed.minor
        return cand_parsed.patch > best_parsed.patch

    def _add_deprecation_headers(
        self, response: VersionedResponse, processor: VersionProcessor
    ) -> None:
        response.set_header(self._config.deprecation_header, "true")

        if processor.deprecation_message:
            response.set_header(
                "X-Deprecation-Message", processor.deprecation_message
            )

        if processor.sunset_at is not None:
            sunset_dt = datetime.datetime.fromtimestamp(
                processor.sunset_at, tz=datetime.timezone.utc
            )
            sunset_str = sunset_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
            response.set_header(self._config.sunset_header, sunset_str)

        if self._config.deprecation_link:
            link = f'<{self._config.deprecation_link}>; rel="deprecation"'
            response.set_header(self._config.deprecation_link_header, link)

        if self._config.default_version is not None:
            response.set_header(
                "X-Recommended-Version", self._config.default_version
            )

    def __len__(self) -> int:
        return len(self._processors)

    def __contains__(self, version: str) -> bool:
        return version in self._processors


__all__ = [
    "Clock",
    "SystemClock",
    "VersionNegotiator",
]
