from __future__ import annotations


class ForexError(Exception):
    pass


class CurrencyPrecisionNotFoundError(ForexError):
    pass


class ExchangeRateNotFoundError(ForexError):
    pass


class NoConversionPathError(ForexError):
    pass


class InvalidExchangeRateError(ForexError):
    pass


class VersionNotFoundError(ForexError):
    pass


class CircularPathDetectedError(ForexError):
    pass


class PathExplosionError(ForexError):
    pass
