from __future__ import annotations

from .exceptions import (
    InvalidPortError,
    InvalidSchemeError,
    InvalidUrlError,
    PercentDecodeError,
    PercentEncodeError,
    UrlBuildError,
    UrlError,
)
from .parser import UrlComponents, UrlParser, parse_url
from .percent import percent_decode, percent_encode, percent_encode_component
from .query import QueryParam, QueryParams
from .scheme import (
    get_known_schemes,
    is_scheme_known,
    register_scheme,
    validate_scheme,
)
from .builder import UrlBuilder

__all__ = [
    "UrlError",
    "InvalidSchemeError",
    "InvalidUrlError",
    "InvalidPortError",
    "PercentEncodeError",
    "PercentDecodeError",
    "UrlBuildError",
    "UrlComponents",
    "UrlParser",
    "parse_url",
    "percent_encode",
    "percent_decode",
    "percent_encode_component",
    "QueryParam",
    "QueryParams",
    "validate_scheme",
    "is_scheme_known",
    "register_scheme",
    "get_known_schemes",
    "UrlBuilder",
]
