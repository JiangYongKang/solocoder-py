from __future__ import annotations

from typing import Optional, Union

from .exceptions import (
    InsufficientBitsError,
    InvalidBitCountError,
)

MIN_BITS = 1
MAX_BITS = 64


class BitReader:
    def __init__(
        self,
        data: Union[bytes, bytearray],
        total_bits: Optional[int] = None,
    ) -> None:
        self._data: bytes = bytes(data)
        max_possible_bits = len(self._data) * 8
        if total_bits is not None:
            if total_bits < 0:
                raise ValueError("total_bits must be non-negative")
            if total_bits > max_possible_bits:
                raise ValueError(
                    f"total_bits ({total_bits}) exceeds maximum possible "
                    f"({max_possible_bits}) from data length"
                )
            self._total_bits_available: int = total_bits
        else:
            self._total_bits_available = max_possible_bits
        self._byte_pos: int = 0
        self._bit_offset: int = 0
        self._total_bits_read: int = 0

    @property
    def total_bits_available(self) -> int:
        return self._total_bits_available

    @property
    def total_bits_read(self) -> int:
        return self._total_bits_read

    @property
    def remaining_bits(self) -> int:
        return self._total_bits_available - self._total_bits_read

    @property
    def byte_position(self) -> int:
        return self._byte_pos

    @property
    def bit_offset(self) -> int:
        return self._bit_offset

    @property
    def is_aligned(self) -> bool:
        return self._bit_offset == 0

    def _read_bits_internal(self, n: int, advance: bool = True) -> int:
        if n == 0:
            return 0
        if n < MIN_BITS or n > MAX_BITS:
            raise InvalidBitCountError(
                f"Bit count must be between {MIN_BITS} and {MAX_BITS}, got {n}"
            )
        if self._total_bits_read + n > self._total_bits_available:
            raise InsufficientBitsError(
                f"Cannot read {n} bits: only {self.remaining_bits} bits remaining "
                f"(total available: {self._total_bits_available}, read so far: {self._total_bits_read})"
            )

        result = 0
        remaining = n
        byte_pos = self._byte_pos
        bit_offset = self._bit_offset

        while remaining > 0:
            bits_in_current_byte = 8 - bit_offset
            bits_to_read = min(remaining, bits_in_current_byte)

            right_shift = bits_in_current_byte - bits_to_read
            mask = ((1 << bits_to_read) - 1) << right_shift
            byte_val = self._data[byte_pos]
            bits_val = (byte_val & mask) >> right_shift

            result = (result << bits_to_read) | bits_val

            remaining -= bits_to_read
            bit_offset += bits_to_read

            if bit_offset == 8:
                bit_offset = 0
                byte_pos += 1

        if advance:
            self._byte_pos = byte_pos
            self._bit_offset = bit_offset
            self._total_bits_read += n

        return result

    def read_bits(self, n: int) -> int:
        return self._read_bits_internal(n, advance=True)

    def peek_bits(self, n: int) -> int:
        return self._read_bits_internal(n, advance=False)


    def align_to_byte(self) -> int:
        """Skip to the next byte boundary.

        When the reader is at a non-zero bit offset within a byte, advance
        to the start of the next byte, discarding the remaining bits in the
        current byte.

        Raises InsufficientBitsError if there are not enough bits remaining
        to reach the next byte boundary.  This can only happen when the
        reader was constructed with an explicit ``total_bits`` value that is
        not a multiple of 8 — for example ``BitReader(data, total_bits=3)``.
        When ``total_bits`` is omitted (the default), the available bit
        count is always ``len(data) * 8`` (a multiple of 8) and this
        exception is unreachable because ``_total_bits_read + skip_bits``
        will always equal a multiple of 8.
        """
        if self._bit_offset == 0:
            return 0

        skip_bits = 8 - self._bit_offset
        if self._total_bits_read + skip_bits > self._total_bits_available:
            raise InsufficientBitsError(
                f"Cannot align: need {skip_bits} bits but only "
                f"{self.remaining_bits} remaining"
            )

        self._bit_offset = 0
        self._byte_pos += 1
        self._total_bits_read += skip_bits
        return skip_bits

    def read_remaining(self) -> bytes:
        if self._bit_offset != 0:
            remaining_in_byte = 8 - self._bit_offset
            effective_remaining = min(remaining_in_byte, self.remaining_bits)
            result = bytearray()
            if self._byte_pos < len(self._data) and effective_remaining > 0:
                mask = (1 << effective_remaining) - 1
                last_bits = (self._data[self._byte_pos] >> (remaining_in_byte - effective_remaining)) & mask
                left_align = 8 - effective_remaining
                if last_bits != 0 or effective_remaining > 0:
                    result.append(last_bits << left_align)
                self._byte_pos += 1
                self._bit_offset = 0
                self._total_bits_read += effective_remaining
            remaining_full_bytes = self.remaining_bits // 8
            if remaining_full_bytes > 0:
                result.extend(self._data[self._byte_pos:self._byte_pos + remaining_full_bytes])
                self._byte_pos += remaining_full_bytes
                self._total_bits_read += remaining_full_bytes * 8
            return bytes(result)

        remaining_full_bytes = self.remaining_bits // 8
        result = self._data[self._byte_pos:self._byte_pos + remaining_full_bytes]
        self._byte_pos += remaining_full_bytes
        self._total_bits_read += remaining_full_bytes * 8
        return bytes(result)

    def reset(self) -> None:
        self._byte_pos = 0
        self._bit_offset = 0
        self._total_bits_read = 0
