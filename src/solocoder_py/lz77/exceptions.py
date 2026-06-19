from __future__ import annotations


class LZ77Error(Exception):
    pass


class LZ77CompressionError(LZ77Error):
    pass


class LZ77DecompressionError(LZ77Error):
    pass


class InvalidConfigError(LZ77Error):
    pass


class CorruptedDataError(LZ77DecompressionError):
    pass


class TruncatedDataError(LZ77DecompressionError):
    pass


class DistanceOutOfRangeError(LZ77DecompressionError):
    pass


class LengthOutOfRangeError(LZ77DecompressionError):
    pass


class ValueOutOfRangeError(LZ77CompressionError):
    pass
