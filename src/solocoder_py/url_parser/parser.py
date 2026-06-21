from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .exceptions import InvalidPortError, InvalidSchemeError, InvalidUrlError
from .percent import percent_decode, percent_encode
from .scheme import validate_scheme

_URI_PATTERN_STRICT = re.compile(
    r"^"
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+\-.]*):"
    r"(?://"
    r"(?:(?P<userinfo>[^@]*)@)?"
    r"(?:"
    r"\[(?P<ipv6>[0-9A-Fa-f:.]+)\]"
    r"|(?P<ipv4>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"
    r"|(?P<reg_name>[^:/?#\[\]]*)"
    r")"
    r"(?::(?P<port>[0-9]+))?"
    r")?"
    r"(?P<path>[^?#]*)"
    r"(?:\?(?P<query>[^#]*))?"
    r"(?:#(?P<fragment>.*))?"
    r"$"
)

_URI_PATTERN_LENIENT = re.compile(
    r"^"
    r"(?P<scheme>[^:]+):"
    r"(?://"
    r"(?:(?P<userinfo>[^@]*)@)?"
    r"(?:"
    r"\[(?P<ipv6>[^\]]+)\]"
    r"|(?P<reg_name>[^:/?#\[\]]*)"
    r")"
    r"(?::(?P<port>[0-9]+))?"
    r")?"
    r"(?P<path>[^?#]*)"
    r"(?:\?(?P<query>[^#]*))?"
    r"(?:#(?P<fragment>.*))?"
    r"$"
)


@dataclass
class UrlComponents:
    scheme: str
    userinfo: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    path: str = ""
    query: Optional[str] = None
    fragment: Optional[str] = None
    has_authority: bool = False

    @property
    def authority(self) -> Optional[str]:
        if not self.has_authority:
            return None
        parts: list[str] = []
        if self.userinfo is not None:
            parts.append(f"{self.userinfo}@")
        if self.host is not None:
            parts.append(self.host)
        if self.port is not None:
            parts.append(f":{self.port}")
        result = "".join(parts)
        return result if result else None

    def rebuild(self) -> str:
        result = f"{self.scheme}:"
        if self.has_authority:
            result += "//"
            if self.userinfo is not None:
                result += f"{self.userinfo}@"
            if self.host is not None:
                result += self.host
            if self.port is not None:
                result += f":{self.port}"
        result += self.path
        if self.query is not None:
            result += f"?{self.query}"
        if self.fragment is not None:
            result += f"#{self.fragment}"
        return result


class UrlParser:
    def __init__(self, validate_scheme_strict: bool = True) -> None:
        self._validate_scheme_strict = validate_scheme_strict

    def parse(self, url: str) -> UrlComponents:
        if not url:
            raise InvalidUrlError("URL cannot be empty")

        pattern = _URI_PATTERN_STRICT if self._validate_scheme_strict else _URI_PATTERN_LENIENT
        match = pattern.match(url)
        if not match:
            raise InvalidUrlError(f"Invalid URL format: {url}")

        scheme = match.group("scheme").lower()

        if self._validate_scheme_strict:
            try:
                validate_scheme(scheme)
            except InvalidSchemeError:
                raise

        has_authority = url[len(scheme) + 1 : len(scheme) + 3] == "//"

        userinfo: Optional[str] = None
        userinfo_raw = match.group("userinfo")
        if userinfo_raw is not None:
            userinfo = userinfo_raw

        host: Optional[str] = None
        ipv6 = match.group("ipv6") if "ipv6" in match.groupdict() else None
        ipv4 = match.group("ipv4") if "ipv4" in match.groupdict() else None
        reg_name = match.group("reg_name") if "reg_name" in match.groupdict() else None

        if ipv6 is not None:
            host = f"[{ipv6}]"
        elif ipv4 is not None:
            host = ipv4
        elif reg_name is not None and reg_name != "":
            host = reg_name

        port: Optional[int] = None
        port_str = match.group("port")
        if port_str is not None:
            try:
                port = int(port_str)
            except ValueError:
                raise InvalidPortError(f"Invalid port number: {port_str}")

        path = match.group("path") or ""
        query = match.group("query")
        fragment = match.group("fragment")

        if has_authority and path.startswith(":"):
            port_part = path[1:].split("/", 1)[0]
            raise InvalidPortError(f"Invalid port in URL: {port_part}")

        return UrlComponents(
            scheme=scheme,
            userinfo=userinfo,
            host=host,
            port=port,
            path=path,
            query=query,
            fragment=fragment,
            has_authority=has_authority,
        )

    @staticmethod
    def decode_component(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return percent_decode(value)

    @staticmethod
    def encode_component(value: str, safe: str = "") -> str:
        return percent_encode(value, safe=safe)


def parse_url(url: str, validate_scheme_strict: bool = True) -> UrlComponents:
    parser = UrlParser(validate_scheme_strict=validate_scheme_strict)
    return parser.parse(url)
