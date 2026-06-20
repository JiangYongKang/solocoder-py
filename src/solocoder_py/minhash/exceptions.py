from __future__ import annotations


class MinHashError(Exception):
    pass


class InvalidConfigError(MinHashError):
    pass


class IncompatibleSignatureError(MinHashError):
    pass


class NonHashableElementError(MinHashError):
    pass


class UnserializableElementError(MinHashError):
    pass
