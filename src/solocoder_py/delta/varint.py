from __future__ import annotations

import struct
from typing import Tuple

from .exceptions import (
    InvalidWidthMarkerError,
    TruncatedDataError,
    ValueOutOfRangeError,
)
from .models import WidthMarker


WIDTH_MARKER_MASK = 0x03
WIDTH_MARKER_SHIFT = 6
SIGN_BIT_MASK = 0x20
ANCHOR_FLAG_MASK = 0x10
RESERVED_BITS_MASK = 0x0F
WIDTH_TO_BYTES = {
    WidthMarker.WIDTH_1: 1,
    WidthMarker.WIDTH_2: 2,
    WidthMarker.WIDTH_4: 4,
    WidthMarker.WIDTH_8: 8,
}
BYTES_TO_WIDTH = {v: k for k, v in WIDTH_TO_BYTES.items()}


def determine_width(value: int, signed: bool = True) -> WidthMarker:
    if signed:
        if -128 <= value <= 127:
            return WidthMarker.WIDTH_1
        elif -32768 <= value <= 32767:
            return WidthMarker.WIDTH_2
        elif -2147483648 <= value <= 2147483647:
            return WidthMarker.WIDTH_4
        elif -9223372036854775808 <= value <= 9223372036854775807:
            return WidthMarker.WIDTH_8
    else:
        if value < 0:
            raise ValueOutOfRangeError(f"Unsigned value cannot be negative: {value}")
        if value <= 255:
            return WidthMarker.WIDTH_1
        elif value <= 65535:
            return WidthMarker.WIDTH_2
        elif value <= 4294967295:
            return WidthMarker.WIDTH_4
        elif value <= 18446744073709551615:
            return WidthMarker.WIDTH_8

    raise ValueOutOfRangeError(
        f"Value {value} exceeds the maximum encodable range"
    )


def encode_int(value: int, signed: bool = True, is_anchor: bool = False) -> bytes:
    width = determine_width(value, signed)
    width_bytes = WIDTH_TO_BYTES[width]

    marker_byte = width << WIDTH_MARKER_SHIFT

    if signed and value < 0:
        marker_byte |= SIGN_BIT_MASK

    if is_anchor:
        marker_byte |= ANCHOR_FLAG_MASK

    if signed:
        if width_bytes == 1:
            fmt = ">b"
        elif width_bytes == 2:
            fmt = ">h"
        elif width_bytes == 4:
            fmt = ">i"
        else:
            fmt = ">q"
        value_bytes = struct.pack(fmt, value)
    else:
        if width_bytes == 1:
            fmt = ">B"
        elif width_bytes == 2:
            fmt = ">H"
        elif width_bytes == 4:
            fmt = ">I"
        else:
            fmt = ">Q"
        value_bytes = struct.pack(fmt, value)

    return bytes([marker_byte]) + value_bytes


def decode_int(
    data: bytes, offset: int, signed: bool = True
) -> Tuple[int, int, bool]:
    if offset >= len(data):
        raise TruncatedDataError(
            f"Truncated data: cannot read width marker at offset {offset}"
        )

    marker_byte = data[offset]

    if marker_byte & RESERVED_BITS_MASK:
        raise InvalidWidthMarkerError(
            f"Invalid width marker: reserved bits are set at offset {offset}"
        )

    width_value = (marker_byte >> WIDTH_MARKER_SHIFT) & WIDTH_MARKER_MASK

    try:
        width = WidthMarker(width_value)
    except ValueError:
        raise InvalidWidthMarkerError(
            f"Invalid width marker: {width_value} at offset {offset}"
        )

    width_bytes = WIDTH_TO_BYTES[width]
    is_anchor = bool(marker_byte & ANCHOR_FLAG_MASK)

    value_start = offset + 1
    value_end = value_start + width_bytes

    if value_end > len(data):
        raise TruncatedDataError(
            f"Truncated data: expected {width_bytes} bytes at offset {value_start}, "
            f"but only {len(data) - value_start} bytes available"
        )

    value_bytes = data[value_start:value_end]

    if signed:
        if width_bytes == 1:
            fmt = ">b"
        elif width_bytes == 2:
            fmt = ">h"
        elif width_bytes == 4:
            fmt = ">i"
        else:
            fmt = ">q"
    else:
        if width_bytes == 1:
            fmt = ">B"
        elif width_bytes == 2:
            fmt = ">H"
        elif width_bytes == 4:
            fmt = ">I"
        else:
            fmt = ">Q"

    try:
        value = struct.unpack(fmt, value_bytes)[0]
    except struct.error as e:
        raise TruncatedDataError(f"Failed to unpack value: {e}")

    consumed = 1 + width_bytes
    return value, consumed, is_anchor


def encode_anchor(value: int, signed: bool = True) -> bytes:
    return encode_int(value, signed, is_anchor=True)


def decode_anchor(
    data: bytes, offset: int, signed: bool = True
) -> Tuple[int, int, bool]:
    return decode_int(data, offset, signed)
