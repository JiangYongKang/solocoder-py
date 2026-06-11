from __future__ import annotations


class BaseCodecError(Exception):
    pass


class InvalidCharacterError(BaseCodecError):
    pass


class InvalidPaddingError(BaseCodecError):
    pass


class TruncatedInputError(BaseCodecError):
    pass


class InvalidLengthError(BaseCodecError):
    pass
