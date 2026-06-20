from __future__ import annotations


class UrlError(Exception):
    pass


class InvalidSchemeError(UrlError):
    pass


class InvalidUrlError(UrlError):
    pass


class InvalidPortError(UrlError):
    pass


class PercentEncodeError(UrlError):
    pass


class PercentDecodeError(UrlError):
    pass


class UrlBuildError(UrlError):
    pass
