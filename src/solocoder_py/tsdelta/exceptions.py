from __future__ import annotations


class TsDeltaError(Exception):
    pass


class TsDeltaCompressionError(TsDeltaError):
    pass


class TsDeltaDecompressionError(TsDeltaError):
    pass


class NonMonotonicTimestampError(TsDeltaCompressionError):
    pass


class InvalidTimestampError(TsDeltaCompressionError):
    pass


class ValueOutOfRangeError(TsDeltaCompressionError):
    pass


class ZigZagOverflowError(TsDeltaCompressionError):
    pass


class Simple8bOverflowError(TsDeltaCompressionError):
    pass


class InvalidSimple8bSelectorError(TsDeltaDecompressionError):
    pass


class TruncatedDataError(TsDeltaDecompressionError):
    pass


class CorruptedDataError(TsDeltaDecompressionError):
    pass


class DataLengthMismatchError(TsDeltaDecompressionError):
    pass
