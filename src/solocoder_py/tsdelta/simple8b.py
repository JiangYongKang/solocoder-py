from __future__ import annotations

import struct
from typing import List, Optional, Tuple

from .exceptions import (
    InvalidSimple8bSelectorError,
    Simple8bOverflowError,
    TruncatedDataError,
)
from .models import SIMPLE8B_MODES, Simple8bMode


def select_best_mode(values: List[int], max_count: int = 120) -> Simple8bMode:
    if not values:
        return SIMPLE8B_MODES[-1]

    slice_end = min(len(values), max_count)
    values_slice = values[:slice_end]
    max_val = max(values_slice)

    if max_val < 0:
        raise Simple8bOverflowError(
            f"Simple-8b can only encode non-negative values, got {max_val}"
        )

    best_mode = SIMPLE8B_MODES[0]
    best_bits_per_value = float('inf')

    for mode in SIMPLE8B_MODES:
        if max_val > mode.max_value:
            continue

        available_count = min(mode.count, len(values))
        if available_count == 0:
            continue

        bits_per_value = mode.total_bits / available_count

        if bits_per_value < best_bits_per_value:
            best_bits_per_value = bits_per_value
            best_mode = mode

    if max_val > best_mode.max_value:
        raise Simple8bOverflowError(
            f"Value {max_val} exceeds maximum representable value for Simple-8b "
            f"({(1 << 60) - 1})"
        )

    return best_mode


def pack_block(values: List[int], mode: Simple8bMode) -> Tuple[int, int]:
    if mode.selector < 0 or mode.selector > 14:
        raise InvalidSimple8bSelectorError(
            f"Invalid Simple-8b selector: {mode.selector}"
        )

    actual_count = min(mode.count, len(values))

    if mode.bit_width == 0:
        for v in values[:actual_count]:
            if v != 0:
                raise Simple8bOverflowError(
                    f"Mode 14 (0-bit) can only encode zeros, got {v}"
                )

    block = mode.selector

    for i in range(actual_count):
        val = values[i]
        if val > mode.max_value:
            raise Simple8bOverflowError(
                f"Value {val} exceeds maximum for mode {mode.selector} "
                f"({mode.max_value})"
            )
        block |= (val & mode.max_value) << (4 + i * mode.bit_width)

    return block, actual_count


def unpack_block(block: int, count: Optional[int] = None) -> Tuple[List[int], Simple8bMode]:
    selector = block & 0x0F

    if selector < 0 or selector > 14:
        raise InvalidSimple8bSelectorError(
            f"Invalid Simple-8b selector: {selector}"
        )

    mode = SIMPLE8B_MODES[selector]
    actual_count = count if count is not None else mode.count
    values: List[int] = []

    for i in range(actual_count):
        shift = 4 + i * mode.bit_width
        if mode.bit_width == 0:
            val = 0
        else:
            val = (block >> shift) & mode.max_value
        values.append(val)

    return values, mode


def simple8b_pack(values: List[int]) -> bytes:
    if not values:
        return b""

    result: List[int] = []
    pos = 0

    while pos < len(values):
        remaining = values[pos:]
        mode = select_best_mode(remaining)
        count = min(mode.count, len(remaining))
        block, _ = pack_block(remaining[:count], mode)
        result.append(block)
        pos += count

    return struct.pack(f"<{len(result)}Q", *result)


def simple8b_unpack(data: bytes, expected_count: int = -1) -> List[int]:
    if not data:
        return []

    if len(data) % 8 != 0:
        raise TruncatedDataError(
            f"Simple-8b data length must be a multiple of 8 bytes, got {len(data)}"
        )

    block_count = len(data) // 8
    blocks = struct.unpack(f"<{block_count}Q", data)

    result: List[int] = []

    for block in blocks:
        values, mode = unpack_block(block)
        result.extend(values)

        if expected_count > 0 and len(result) >= expected_count:
            break

    if expected_count > 0 and len(result) > expected_count:
        result = result[:expected_count]

    return result


def count_blocks(data: bytes) -> int:
    if not data:
        return 0
    if len(data) % 8 != 0:
        raise TruncatedDataError(
            f"Simple-8b data length must be a multiple of 8 bytes, got {len(data)}"
        )
    return len(data) // 8
