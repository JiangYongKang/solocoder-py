from __future__ import annotations

from typing import List

from .exceptions import BufferOverflowError


class Buffer:
    def __init__(self, initial_data: bytes | None = None) -> None:
        self._data: bytearray = bytearray(initial_data) if initial_data else bytearray()
        self._read_pos: int = 0

    @property
    def data(self) -> bytes:
        return bytes(self._data)

    @property
    def read_position(self) -> int:
        return self._read_pos

    @property
    def write_position(self) -> int:
        return len(self._data)

    @property
    def remaining(self) -> int:
        return len(self._data) - self._read_pos

    def reset_read(self) -> None:
        self._read_pos = 0

    def clear(self) -> None:
        self._data.clear()
        self._read_pos = 0

    def write_byte(self, value: int) -> None:
        if not (0 <= value <= 255):
            raise ValueError("byte value must be in range [0, 255]")
        self._data.append(value)

    def write_bytes(self, values: bytes | bytearray) -> None:
        self._data.extend(values)

    def read_byte(self) -> int:
        if self._read_pos >= len(self._data):
            raise BufferOverflowError("attempted to read beyond buffer end")
        result = self._data[self._read_pos]
        self._read_pos += 1
        return result

    def read_bytes(self, count: int) -> bytes:
        if count < 0:
            raise ValueError("count must be non-negative")
        if self._read_pos + count > len(self._data):
            raise BufferOverflowError("attempted to read beyond buffer end")
        result = bytes(self._data[self._read_pos:self._read_pos + count])
        self._read_pos += count
        return result

    def peek_byte(self, offset: int = 0) -> int:
        pos = self._read_pos + offset
        if pos >= len(self._data):
            raise BufferOverflowError("attempted to peek beyond buffer end")
        return self._data[pos]

    def skip(self, count: int) -> None:
        if count < 0:
            raise ValueError("count must be non-negative")
        if self._read_pos + count > len(self._data):
            raise BufferOverflowError("attempted to skip beyond buffer end")
        self._read_pos += count
