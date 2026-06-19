from __future__ import annotations

from typing import Optional

from .exceptions import (
    BitCapacityExceededError,
    InvalidBitCountError,
    ValueOutOfRangeError,
)

MIN_BITS = 1
MAX_BITS = 64


class BitWriter:
    def __init__(self, capacity_bits: Optional[int] = None) -> None:
        self._buffer: bytearray = bytearray()
        self._bit_offset: int = 0
        self._total_bits_written: int = 0
        self._capacity_bits: Optional[int] = capacity_bits

    @property
    def total_bits_written(self) -> int:
        return self._total_bits_written

    @property
    def total_bytes_written(self) -> int:
        return len(self._buffer)

    @property
    def capacity_bits(self) -> Optional[int]:
        return self._capacity_bits

    @property
    def remaining_capacity_bits(self) -> Optional[int]:
        if self._capacity_bits is None:
            return None
        return self._capacity_bits - self._total_bits_written

    def write_bits(self, value: int, n: int) -> None:
        if n == 0:
            return
        if n < MIN_BITS or n > MAX_BITS:
            raise InvalidBitCountError(
                f"Bit count must be between {MIN_BITS} and {MAX_BITS}, got {n}"
            )
        if value < 0:
            raise ValueOutOfRangeError("Value must be non-negative")
        max_value = (1 << n) - 1
        if value > max_value:
            raise ValueOutOfRangeError(
                f"Value {value} exceeds maximum {max_value} for {n} bits"
            )

        if self._capacity_bits is not None:
            if self._total_bits_written + n > self._capacity_bits:
                raise BitCapacityExceededError(
                    f"Cannot write {n} bits: capacity {self._capacity_bits} "
                    f"exceeded (already wrote {self._total_bits_written})"
                )

        remaining = n
        value_shifted = value

        while remaining > 0:
            if self._bit_offset == 0 and len(self._buffer) == 0 or self._bit_offset == 8:
                self._buffer.append(0)
                self._bit_offset = 0

            current_byte_idx = len(self._buffer) - 1
            bits_in_current_byte = 8 - self._bit_offset
            bits_to_write = min(remaining, bits_in_current_byte)

            shift_amount = remaining - bits_to_write
            bits_val = (value_shifted >> shift_amount) & ((1 << bits_to_write) - 1)

            left_shift = bits_in_current_byte - bits_to_write
            self._buffer[current_byte_idx] |= bits_val << left_shift

            value_shifted &= (1 << shift_amount) - 1
            remaining -= bits_to_write
            self._bit_offset += bits_to_write
            self._total_bits_written += bits_to_write

    def align_to_byte(self, fill_bit: int = 0) -> int:
        if fill_bit not in (0, 1):
            raise ValueError("fill_bit must be 0 or 1")

        if self._bit_offset == 0 or self._bit_offset == 8:
            return 0

        padding_bits = 8 - self._bit_offset
        if self._capacity_bits is not None:
            if self._total_bits_written + padding_bits > self._capacity_bits:
                raise BitCapacityExceededError(
                    f"Cannot align: capacity {self._capacity_bits} exceeded"
                )

        fill_value = 0
        for i in range(padding_bits):
            if fill_bit == 1:
                fill_value |= 1 << (padding_bits - 1 - i)

        self._buffer[len(self._buffer) - 1] |= fill_value
        self._bit_offset = 8
        self._total_bits_written += padding_bits
        return padding_bits

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)

    def reset(self) -> None:
        self._buffer = bytearray()
        self._bit_offset = 0
        self._total_bits_written = 0
