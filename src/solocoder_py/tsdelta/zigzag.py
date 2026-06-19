from __future__ import annotations

from typing import List

from .exceptions import ZigZagOverflowError


MAX_SIGNED_60BIT = (1 << 59) - 1
MIN_SIGNED_60BIT = -(1 << 59)


def zigzag_encode(value: int, max_bits: int = 60) -> int:
    max_signed = (1 << (max_bits - 1)) - 1
    min_signed = -(1 << (max_bits - 1))

    if value > max_signed or value < min_signed:
        raise ZigZagOverflowError(
            f"Value {value} out of range for {max_bits}-bit ZigZag encoding "
            f"(expected {min_signed} to {max_signed})"
        )

    return (value << 1) ^ (value >> (max_bits - 1))


def zigzag_decode(encoded: int, max_bits: int = 60) -> int:
    max_unsigned = (1 << max_bits) - 1

    if encoded < 0 or encoded > max_unsigned:
        raise ZigZagOverflowError(
            f"Encoded value {encoded} out of range for {max_bits}-bit ZigZag decoding "
            f"(expected 0 to {max_unsigned})"
        )

    return (encoded >> 1) ^ (-(encoded & 1))


def zigzag_encode_list(values: List[int], max_bits: int = 60) -> List[int]:
    return [zigzag_encode(v, max_bits) for v in values]


def zigzag_decode_list(encoded: List[int], max_bits: int = 60) -> List[int]:
    return [zigzag_decode(v, max_bits) for v in encoded]
