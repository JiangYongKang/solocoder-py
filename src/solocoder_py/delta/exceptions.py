from __future__ import annotations


class DeltaCompressionError(Exception):
    pass


class DeltaDecompressionError(DeltaCompressionError):
    pass


class InvalidWidthMarkerError(DeltaDecompressionError):
    pass


class TruncatedDataError(DeltaDecompressionError):
    pass


class DataLengthMismatchError(DeltaDecompressionError):
    pass


class ValueOutOfRangeError(DeltaCompressionError):
    pass


class InvalidAnchorIntervalError(DeltaCompressionError):
    pass


class CorruptedDataError(DeltaDecompressionError):
    pass
