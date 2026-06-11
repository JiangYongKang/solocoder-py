from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .exceptions import HeaderFilterError
from .models import FilterMode, Request, Response


@dataclass
class HeaderFilterConfig:
    mode: FilterMode = FilterMode.BLACKLIST
    headers: List[str] = field(default_factory=list)
    case_insensitive: bool = True

    def __post_init__(self) -> None:
        if self.case_insensitive:
            self.headers = [h.lower() for h in self.headers]


class HeaderFilter:
    def __init__(self, config: Optional[HeaderFilterConfig] = None) -> None:
        self._config = config or HeaderFilterConfig()
        self._header_set: Set[str] = set(self._config.headers)

    def set_config(self, config: HeaderFilterConfig) -> "HeaderFilter":
        self._config = config
        self._header_set = set(config.headers)
        return self

    def add_header(self, header: str) -> "HeaderFilter":
        normalized = header.lower() if self._config.case_insensitive else header
        self._header_set.add(normalized)
        self._config.headers = list(self._header_set)
        return self

    def remove_header(self, header: str) -> "HeaderFilter":
        normalized = header.lower() if self._config.case_insensitive else header
        self._header_set.discard(normalized)
        self._config.headers = list(self._header_set)
        return self

    def _normalize(self, header: str) -> str:
        return header.lower() if self._config.case_insensitive else header

    def _matches(self, header: str) -> bool:
        return self._normalize(header) in self._header_set

    def filter_request_headers(self, request: Request) -> Request:
        try:
            modified = request.copy()
            filtered: Dict[str, str] = {}
            for name, value in request.headers.items():
                if self._config.mode == FilterMode.WHITELIST:
                    if self._matches(name):
                        filtered[name] = value
                else:
                    if not self._matches(name):
                        filtered[name] = value
            modified.headers = filtered
            return modified
        except Exception as e:
            raise HeaderFilterError(f"Request header filter failed: {e}") from e

    def filter_response_headers(self, response: Response) -> Response:
        try:
            modified = response.copy()
            filtered: Dict[str, str] = {}
            for name, value in response.headers.items():
                if self._config.mode == FilterMode.WHITELIST:
                    if self._matches(name):
                        filtered[name] = value
                else:
                    if not self._matches(name):
                        filtered[name] = value
            modified.headers = filtered
            return modified
        except Exception as e:
            raise HeaderFilterError(f"Response header filter failed: {e}") from e

    @property
    def mode(self) -> FilterMode:
        return self._config.mode

    @property
    def headers(self) -> List[str]:
        return list(self._header_set)


class RequestHeaderFilter(HeaderFilter):
    def __call__(self, request: Request) -> Request:
        return self.filter_request_headers(request)


class ResponseHeaderFilter(HeaderFilter):
    def __call__(self, response: Response) -> Response:
        return self.filter_response_headers(response)
