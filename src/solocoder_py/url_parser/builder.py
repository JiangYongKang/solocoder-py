from __future__ import annotations

from typing import Optional

from .exceptions import UrlBuildError
from .parser import UrlComponents
from .percent import percent_encode
from .query import QueryParams
from .scheme import validate_scheme

_USERINFO_SAFE = "-._~:!$&'()*+,;="
_PATH_SAFE = "-._~"
_FRAGMENT_SAFE = "-._~/?"


class UrlBuilder:
    def __init__(self) -> None:
        self._scheme: Optional[str] = None
        self._userinfo: Optional[str] = None
        self._host: Optional[str] = None
        self._port: Optional[int] = None
        self._path_segments: list[str] = []
        self._query_params: QueryParams = QueryParams()
        self._fragment: Optional[str] = None

    def scheme(self, scheme: str) -> "UrlBuilder":
        validate_scheme(scheme)
        self._scheme = scheme.lower()
        return self

    def userinfo(self, userinfo: str) -> "UrlBuilder":
        self._userinfo = userinfo
        return self

    def host(self, host: str) -> "UrlBuilder":
        self._host = host
        return self

    def port(self, port: int) -> "UrlBuilder":
        if port < 0 or port > 65535:
            raise UrlBuildError(f"Port must be between 0 and 65535, got {port}")
        self._port = port
        return self

    def path(self, path_str: str) -> "UrlBuilder":
        self._path_segments = []
        if path_str:
            segments = path_str.split("/")
            for seg in segments:
                if seg:
                    self._path_segments.append(seg)
        return self

    def path_segment(self, segment: str) -> "UrlBuilder":
        if segment:
            self._path_segments.append(segment)
        return self

    def add_query_param(self, key: str, value: Optional[str] = None) -> "UrlBuilder":
        self._query_params.add_param(key, value)
        return self

    def set_query_param(self, key: str, value: Optional[str] = None) -> "UrlBuilder":
        self._query_params.set_param(key, value)
        return self

    def remove_query_param(self, key: str) -> "UrlBuilder":
        self._query_params.remove_param(key)
        return self

    def fragment(self, fragment: str) -> "UrlBuilder":
        self._fragment = fragment
        return self

    def build(self) -> str:
        if self._scheme is None:
            raise UrlBuildError("Scheme is required to build a URL")

        result = f"{self._scheme}:"

        if self._host is not None:
            result += "//"
            if self._userinfo is not None:
                encoded_userinfo = percent_encode(self._userinfo, safe=_USERINFO_SAFE)
                result += f"{encoded_userinfo}@"
            result += self._host
            if self._port is not None:
                result += f":{self._port}"

            if self._path_segments:
                result += "/" + "/".join(
                    percent_encode(seg, safe=_PATH_SAFE) for seg in self._path_segments
                )
        else:
            if self._path_segments:
                result += "/".join(
                    percent_encode(seg, safe=_PATH_SAFE) for seg in self._path_segments
                )

        query_str = self._query_params.to_string()
        if query_str is not None:
            result += f"?{query_str}"

        if self._fragment is not None:
            encoded_fragment = percent_encode(self._fragment, safe=_FRAGMENT_SAFE)
            result += f"#{encoded_fragment}"

        return result

    def build_components(self) -> UrlComponents:
        if self._scheme is None:
            raise UrlBuildError("Scheme is required to build URL components")

        path = ""
        if self._path_segments:
            if self._host is not None:
                path = "/" + "/".join(
                    percent_encode(seg, safe=_PATH_SAFE) for seg in self._path_segments
                )
            else:
                path = "/".join(
                    percent_encode(seg, safe=_PATH_SAFE) for seg in self._path_segments
                )

        return UrlComponents(
            scheme=self._scheme,
            userinfo=self._userinfo,
            host=self._host,
            port=self._port,
            path=path,
            query=self._query_params.to_string(),
            fragment=self._fragment,
        )
