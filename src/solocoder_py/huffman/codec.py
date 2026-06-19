from __future__ import annotations

from typing import Any, Iterable, Optional

from .canonical import (
    build_decode_table,
    generate_code_table,
    verify_prefix_code_property,
)
from .exceptions import (
    HuffmanDecodeError,
    HuffmanEmptyInputError,
    HuffmanInvalidCodeError,
    HuffmanTruncatedCodeError,
)
from .frequency import count_frequencies
from .models import (
    CodeTable,
    EncodedData,
    FrequencyTable,
)


class HuffmanEncoder:
    def __init__(self, freq_table: Optional[dict[Any, int] | FrequencyTable] = None):
        self._freq_table: Optional[FrequencyTable] = None
        self._code_table: Optional[CodeTable] = None
        self._buffer: list[Any] = []
        self._finished: bool = False

        if freq_table is not None:
            if isinstance(freq_table, FrequencyTable):
                self._freq_table = freq_table
            else:
                self._freq_table = FrequencyTable(frequencies=dict(freq_table))
            self._code_table = generate_code_table(self._freq_table)

    def write(self, data: Iterable[Any]) -> None:
        if self._finished:
            raise RuntimeError("Encoder has already been finished")
        if data is None:
            raise HuffmanEmptyInputError("Input data cannot be None")

        self._buffer.extend(list(data))

    def _rebuild_from_buffer(self) -> None:
        if not self._buffer:
            return
        self._freq_table = count_frequencies(self._buffer)
        if len(self._freq_table) == 0:
            return
        self._code_table = generate_code_table(self._freq_table)

    def set_frequency_table(self, freq_table: dict[Any, int] | FrequencyTable) -> None:
        if isinstance(freq_table, FrequencyTable):
            self._freq_table = freq_table
        else:
            self._freq_table = FrequencyTable(frequencies=dict(freq_table))
        self._code_table = generate_code_table(self._freq_table)

    def finish(self) -> EncodedData:
        if self._finished:
            return self._build_result()

        if not self._buffer:
            raise HuffmanEmptyInputError("No data to encode")

        if self._code_table is None:
            self._rebuild_from_buffer()
            if self._code_table is None or len(self._code_table) == 0:
                raise HuffmanEmptyInputError("No valid symbols to encode")

        self._finished = True
        return self._build_result()

    def _build_result(self) -> EncodedData:
        assert self._code_table is not None
        assert self._freq_table is not None

        bit_parts: list[str] = []
        for symbol in self._buffer:
            if symbol not in self._code_table:
                raise HuffmanInvalidCodeError(f"Unknown symbol: {symbol!r}")
            bit_parts.append(self._code_table.get_code(symbol))

        return EncodedData(
            bit_string="".join(bit_parts),
            code_table=self._code_table,
            original_length=len(self._buffer),
        )

    def reset(self) -> None:
        self._buffer = []
        self._freq_table = None
        self._code_table = None
        self._finished = False

    @property
    def code_table(self) -> Optional[CodeTable]:
        return self._code_table

    @property
    def freq_table(self) -> Optional[FrequencyTable]:
        return self._freq_table


class HuffmanDecoder:
    def __init__(self, code_table: CodeTable):
        if code_table is None or len(code_table) == 0:
            raise HuffmanEmptyInputError("Code table cannot be empty")
        self._code_table = code_table
        self._decode_table = build_decode_table(code_table)
        self._max_code_length = max(
            info.code_length for info in code_table.codes.values()
        )
        self._buffer: str = ""
        self._finished: bool = False
        self._output: list[Any] = []

    def write(self, bit_string: str) -> list[Any]:
        if self._finished:
            raise RuntimeError("Decoder has already been finished")
        if bit_string is None:
            raise HuffmanEmptyInputError("Input bit string cannot be None")

        for ch in bit_string:
            if ch not in ("0", "1"):
                raise HuffmanInvalidCodeError(
                    f"Invalid bit character: {ch!r}, expected '0' or '1'"
                )

        self._buffer += bit_string
        return self._decode_buffer()

    def _decode_buffer(self) -> list[Any]:
        decoded: list[Any] = []
        pos = 0
        current_code = ""

        while pos < len(self._buffer):
            current_code += self._buffer[pos]
            pos += 1

            if len(current_code) > self._max_code_length:
                raise HuffmanInvalidCodeError(
                    f"Code exceeds maximum length {self._max_code_length}: {current_code!r}"
                )

            if current_code in self._decode_table:
                decoded.append(self._decode_table[current_code])
                current_code = ""

        self._buffer = current_code
        self._output.extend(decoded)
        return decoded

    def finish(self, expected_length: Optional[int] = None) -> list[Any]:
        if self._finished:
            if expected_length is not None and len(self._output) != expected_length:
                raise HuffmanTruncatedCodeError(
                    f"Decoded length {len(self._output)} does not match expected {expected_length}"
                )
            return list(self._output)

        if self._buffer:
            raise HuffmanTruncatedCodeError(
                f"Truncated bit string remaining: {self._buffer!r}"
            )

        self._finished = True

        if expected_length is not None and len(self._output) != expected_length:
            raise HuffmanTruncatedCodeError(
                f"Decoded length {len(self._output)} does not match expected {expected_length}"
            )

        return list(self._output)

    def reset(self) -> None:
        self._buffer = ""
        self._output = []
        self._finished = False


def encode(data: Iterable[Any]) -> EncodedData:
    encoder = HuffmanEncoder()
    encoder.write(data)
    return encoder.finish()


def decode(
    bit_string: str,
    code_table: CodeTable,
    expected_length: Optional[int] = None,
) -> list[Any]:
    decoder = HuffmanDecoder(code_table)
    decoder.write(bit_string)
    return decoder.finish(expected_length=expected_length)
