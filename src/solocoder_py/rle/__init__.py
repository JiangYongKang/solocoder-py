from __future__ import annotations

from .exceptions import (
    RLEError,
    RLEDecodeError,
    RLETruncatedDataError,
    RLEInvalidCountError,
    RLEInvalidLengthError,
    RLEOutputLengthMismatchError,
)
from .rle import (
    ESC_BYTE,
    TYPE_ESC_ESCAPE,
    TYPE_RUN,
    TYPE_LITERAL,
    MIN_RUN_LENGTH,
    MAX_COUNT,
    MAX_LITERAL_LENGTH,
    encode,
    decode,
    RLEEncoder,
    RLEDecoder,
)

__all__ = [
    "RLEError",
    "RLEDecodeError",
    "RLETruncatedDataError",
    "RLEInvalidCountError",
    "RLEInvalidLengthError",
    "RLEOutputLengthMismatchError",
    "ESC_BYTE",
    "TYPE_ESC_ESCAPE",
    "TYPE_RUN",
    "TYPE_LITERAL",
    "MIN_RUN_LENGTH",
    "MAX_COUNT",
    "MAX_LITERAL_LENGTH",
    "encode",
    "decode",
    "RLEEncoder",
    "RLEDecoder",
]
