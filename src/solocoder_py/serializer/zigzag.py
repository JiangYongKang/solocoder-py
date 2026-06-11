from __future__ import annotations

from .exceptions import ZigZagOverflowError


def _validate_bits(bits: int) -> None:
    if bits not in (8, 16, 32, 64):
        raise ValueError(f"unsupported bit width: {bits}, must be one of 8, 16, 32, 64")


def encode_zigzag(value: int, bits: int = 64) -> int:
    _validate_bits(bits)
    min_val = -(1 << (bits - 1))
    max_val = (1 << (bits - 1)) - 1
    if value < min_val or value > max_val:
        raise ZigZagOverflowError(
            f"value {value} out of range for signed {bits}-bit integer [{min_val}, {max_val}]"
        )
    if value >= 0:
        return value << 1
    else:
        return (abs(value) << 1) - 1


def decode_zigzag(value: int, bits: int = 64) -> int:
    _validate_bits(bits)
    max_unsigned = (1 << bits) - 1
    if value < 0 or value > max_unsigned:
        raise ZigZagOverflowError(
            f"unsigned value {value} out of range for {bits}-bit integer [0, {max_unsigned}]"
        )
    if (value & 1) == 0:
        return value >> 1
    else:
        return -((value + 1) >> 1)
