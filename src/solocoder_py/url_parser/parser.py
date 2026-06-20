from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .exceptions import InvalidPortError, InvalidSchemeError, InvalidUrlError
from .percent import percent_decode, percent_encode
from .scheme import validate_scheme

_URI_PATTERN = re.compile(
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


@dataclass
class UrlComponents:
    scheme: str
    userinfo: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    path: str = ""
    query: Optional[str] = None
    fragment: Optional[str] = None

    @property
    def authority(self) -> Optional[str]:
        if self.host is None:
            return None
        result = ""
        if self.userinfo is not None:
            result += f"{self.userinfo}@"
        result += self.host
        if self.port is not None:
            result += f":{self.port}"
        return result

    def rebuild(self) -> str:
        result = f"{self.scheme}:"
        authority = self.authority
        if authority is not None:
            result += f"//{authority}"
            if self.path and not self.path.startswith("/"):
                result += f"/{self.path}"
            else:
                result += self.path
        else:
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

        match = _URI_PATTERN.match(url)
        if not match:
            raise InvalidUrlError(f"Invalid URL format: {url}")

        scheme = match.group("scheme")
        try:
            validate_scheme(scheme)
        except InvalidSchemeError:
            raise

        userinfo: Optional[str] = None
        userinfo_raw = match.group("userinfo")
        if userinfo_raw is not None:
            userinfo = userinfo_raw

        host: Optional[str] = None
        ipv6 = match.group("ipv6")
        ipv4 = match.group("ipv4")
        reg_name = match.group("reg_name")

        if ipv6 is not None:
            host = f"[{ipv6}]"
        elif ipv4 is not None:
            host = ipv4
        elif reg_name is not None and reg_name != "":
            host = reg_name

        has_authority = (
            userinfo_raw is not None
            or ipv6 is not None
            or ipv4 is not None
            or (reg_name is not None and reg_name != "")
        )

        if has_authority and host is None:
            raise InvalidUrlError(f"Host is missing in authority")

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
            raise InvalidPortError(
                f"Invalid port in URL: {path.split('/', 1)[0][1:]}"
            )

        return UrlComponents(
            scheme=scheme,
            userinfo=userinfo,
            host=host,
            port=port,
            path=path,
            query=query,
            fragment=fragment,
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
