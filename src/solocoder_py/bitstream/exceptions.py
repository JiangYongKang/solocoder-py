from __future__ import annotations


class BitStreamError(Exception):
    pass


class BitWriterError(BitStreamError):
    pass


class BitReaderError(BitStreamError):
    pass


class InvalidBitCountError(BitStreamError):
    pass


class BitCapacityExceededError(BitWriterError):
    pass


class InsufficientBitsError(BitReaderError):
    pass


class ValueOutOfRangeError(BitWriterError):
    pass
