from __future__ import annotations

import io
from abc import ABC, abstractmethod
from typing import Optional

from .exceptions import (
    InvalidCharacterError,
    InvalidLengthError,
    InvalidPaddingError,
    TruncatedInputError,
)


class _BaseEncoder(ABC):
    _BITS_PER_BYTE = 8
    _PAD_CHAR = "="

    def __init__(
        self,
        pad: bool = True,
        line_width: int = 0,
        newline: str = "\n",
    ) -> None:
        if line_width < 0:
            raise ValueError("line_width must be non-negative")
        self._pad = pad
        self._line_width = line_width
        self._newline = newline
        self._buffer: bytearray = bytearray()
        self._output: io.StringIO = io.StringIO()
        self._char_count: int = 0
        self._finalized: bool = False

    @property
    @abstractmethod
    def _bits_per_char(self) -> int:
        ...

    @property
    @abstractmethod
    def _alphabet(self) -> str:
        ...

    @property
    def _bytes_per_block(self) -> int:
        lcm = self._bits_per_char * self._BITS_PER_BYTE // self._gcd(
            self._bits_per_char, self._BITS_PER_BYTE
        )
        return lcm // self._BITS_PER_BYTE

    @property
    def _chars_per_block(self) -> int:
        lcm = self._bits_per_char * self._BITS_PER_BYTE // self._gcd(
            self._bits_per_char, self._BITS_PER_BYTE
        )
        return lcm // self._bits_per_char

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    def _encode_block(self, block: bytes) -> str:
        input_bits = len(block) * self._BITS_PER_BYTE
        num_chars = (input_bits + self._bits_per_char - 1) // self._bits_per_char
        pad_bits = num_chars * self._bits_per_char - input_bits
        value = 0
        for byte in block:
            value = (value << self._BITS_PER_BYTE) | byte
        value = value << pad_bits
        result = []
        for i in range(num_chars - 1, -1, -1):
            idx = (value >> (i * self._bits_per_char)) & ((1 << self._bits_per_char) - 1)
            result.append(self._alphabet[idx])
        return "".join(result)

    def _pad_encoded(self, encoded: str, input_len: int) -> str:
        if not self._pad:
            return encoded
        total_bits = input_len * self._BITS_PER_BYTE
        required_chars = (total_bits + self._bits_per_char - 1) // self._bits_per_char
        pad_len = self._chars_per_block - (required_chars % self._chars_per_block)
        if pad_len == self._chars_per_block:
            pad_len = 0
        return encoded + self._PAD_CHAR * pad_len

    def _write_with_line_break(self, text: str) -> None:
        if self._line_width == 0:
            self._output.write(text)
            self._char_count += len(text)
            return
        for char in text:
            if self._char_count >= self._line_width:
                self._output.write(self._newline)
                self._char_count = 0
            self._output.write(char)
            self._char_count += 1

    def update(self, data: bytes) -> None:
        if self._finalized:
            raise RuntimeError("Encoder has already been finalized")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes-like")
        self._buffer.extend(data)
        while len(self._buffer) >= self._bytes_per_block:
            block = bytes(self._buffer[: self._bytes_per_block])
            self._buffer = self._buffer[self._bytes_per_block :]
            encoded = self._encode_block(block)
            self._write_with_line_break(encoded)

    def finalize(self) -> str:
        if self._finalized:
            raise RuntimeError("Encoder has already been finalized")
        self._finalized = True
        input_len = len(self._buffer)
        if input_len > 0:
            encoded = self._encode_block(bytes(self._buffer))
            encoded = self._pad_encoded(encoded, input_len)
            self._write_with_line_break(encoded)
        if self._line_width > 0 and self._char_count == self._line_width:
            self._output.write(self._newline)
            self._char_count = 0
        self._buffer.clear()
        result = self._output.getvalue()
        self._output = io.StringIO()
        self._char_count = 0
        return result

    def reset(self) -> None:
        self._buffer.clear()
        self._output = io.StringIO()
        self._char_count = 0
        self._finalized = False

    def encode(self, data: bytes) -> str:
        self.reset()
        self.update(data)
        return self.finalize()


class _BaseDecoder(ABC):
    _BITS_PER_BYTE = 8
    _PAD_CHAR = "="
    _WHITESPACE = frozenset(" \t\n\r\x0b\x0c")

    def __init__(self, pad: bool = True) -> None:
        self._pad = pad
        self._buffer: str = ""
        self._output: bytearray = bytearray()
        self._finalized: bool = False
        self._reverse_table: dict[str, int] | None = None
        self._total_chars: int = 0

    @property
    @abstractmethod
    def _bits_per_char(self) -> int:
        ...

    @property
    @abstractmethod
    def _alphabet(self) -> str:
        ...

    @property
    def _bytes_per_block(self) -> int:
        lcm = self._bits_per_char * self._BITS_PER_BYTE // self._gcd(
            self._bits_per_char, self._BITS_PER_BYTE
        )
        return lcm // self._BITS_PER_BYTE

    @property
    def _chars_per_block(self) -> int:
        lcm = self._bits_per_char * self._BITS_PER_BYTE // self._gcd(
            self._bits_per_char, self._BITS_PER_BYTE
        )
        return lcm // self._bits_per_char

    @staticmethod
    def _gcd(a: int, b: int) -> int:
        while b:
            a, b = b, a % b
        return a

    def _build_reverse_table(self) -> dict[str, int]:
        if self._reverse_table is None:
            self._reverse_table = {char: idx for idx, char in enumerate(self._alphabet)}
        return self._reverse_table

    def _validate_and_strip_padding(self, data: str) -> tuple[str, int]:
        if not self._pad:
            return data, 0
        pad_count = 0
        i = len(data) - 1
        while i >= 0 and data[i] == self._PAD_CHAR:
            pad_count += 1
            i -= 1
        if pad_count > 0:
            if pad_count >= self._chars_per_block:
                raise InvalidPaddingError(
                    f"Invalid padding: {pad_count} padding characters"
                )
            stripped = data[: i + 1]
            total_chars = len(stripped) + pad_count
            if total_chars % self._chars_per_block != 0:
                raise InvalidPaddingError(
                    f"Invalid input length with padding: {total_chars} characters"
                )
            return stripped, pad_count
        if len(data) % self._chars_per_block != 0:
            raise InvalidLengthError(
                f"Invalid input length: {len(data)} characters (not a multiple of {self._chars_per_block})"
            )
        return data, 0

    def _decode_block(self, block: str, pad_count: int = 0) -> bytes:
        reverse_table = self._build_reverse_table()
        value = 0
        for char in block:
            if char not in reverse_table:
                raise InvalidCharacterError(f"Invalid character: {repr(char)}")
            value = (value << self._bits_per_char) | reverse_table[char]
        output_bytes = (len(block) * self._bits_per_char) // self._BITS_PER_BYTE
        pad_bits = len(block) * self._bits_per_char - output_bytes * self._BITS_PER_BYTE
        if pad_bits > 0:
            pad_bits_mask = (1 << pad_bits) - 1
            if (value & pad_bits_mask) != 0:
                if self._pad and pad_count > 0:
                    raise InvalidPaddingError(
                        f"Invalid input length with padding: non-zero padding bits"
                    )
                else:
                    raise TruncatedInputError(
                        f"Truncated input: {len(block) + pad_count} characters cannot produce an integer number of bytes"
                    )
            value = value >> pad_bits
        result = bytearray()
        for i in range(output_bytes - 1, -1, -1):
            byte = (value >> (i * self._BITS_PER_BYTE)) & 0xFF
            result.append(byte)
        return bytes(result)

    def _validate_no_padding_length(self, char_count: int) -> int:
        output_bytes = (char_count * self._bits_per_char) // self._BITS_PER_BYTE
        required_chars = (output_bytes * self._BITS_PER_BYTE + self._bits_per_char - 1) // self._bits_per_char
        if required_chars != char_count:
            raise TruncatedInputError(
                f"Truncated input: {char_count} characters cannot produce an integer number of bytes"
            )
        return output_bytes

    def _filter_whitespace(self, data: str) -> str:
        return "".join(c for c in data if c not in self._WHITESPACE)

    def update(self, data: str) -> None:
        if self._finalized:
            raise RuntimeError("Decoder has already been finalized")
        if not isinstance(data, str):
            raise TypeError("data must be a string")
        filtered = self._filter_whitespace(data)
        self._buffer += filtered
        if not self._pad:
            self._total_chars += len(filtered)
        while len(self._buffer) >= self._chars_per_block:
            if self._pad:
                has_padding = self._PAD_CHAR in self._buffer[: self._chars_per_block]
                if has_padding:
                    break
            block = self._buffer[: self._chars_per_block]
            self._buffer = self._buffer[self._chars_per_block :]
            decoded = self._decode_block(block, 0)
            self._output.extend(decoded)

    def finalize(self) -> bytes:
        if self._finalized:
            raise RuntimeError("Decoder has already been finalized")
        self._finalized = True
        buffer_len = len(self._buffer)
        if buffer_len == 0:
            result = bytes(self._output)
            self._output.clear()
            return result
        data, pad_count = self._validate_and_strip_padding(self._buffer)
        if self._pad:
            if len(data) > 0:
                decoded = self._decode_block(data, pad_count)
                self._output.extend(decoded)
        else:
            expected_bytes = self._validate_no_padding_length(self._total_chars)
            if len(data) > 0:
                decoded = self._decode_block(data, 0)
                self._output.extend(decoded)
            if len(self._output) != expected_bytes:
                raise TruncatedInputError(
                    f"Decoded length mismatch: expected {expected_bytes} bytes, got {len(self._output)}"
                )
        result = bytes(self._output)
        self._output.clear()
        self._buffer = ""
        return result

    def reset(self) -> None:
        self._buffer = ""
        self._output.clear()
        self._finalized = False
        self._total_chars = 0

    def decode(self, data: str) -> bytes:
        self.reset()
        self.update(data)
        return self.finalize()
