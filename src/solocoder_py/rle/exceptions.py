from __future__ import annotations


class RLEError(Exception):
    pass


class RLEDecodeError(RLEError):
    pass


class RLETruncatedDataError(RLEDecodeError):
    pass


class RLEInvalidCountError(RLEDecodeError):
    pass


class RLEInvalidLengthError(RLEDecodeError):
    pass


class RLEOutputLengthMismatchError(RLEDecodeError):
    pass
