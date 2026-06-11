from __future__ import annotations

from typing import Tuple

from .exceptions import (
    RLEInvalidCountError,
    RLEInvalidLengthError,
    RLEOutputLengthMismatchError,
    RLETruncatedDataError,
)


ESC_BYTE = 0x1B
TYPE_ESC_ESCAPE = 0x00
TYPE_RUN = 0x01
TYPE_LITERAL = 0x02
MIN_RUN_LENGTH = 3
MAX_COUNT = 255
MAX_LITERAL_LENGTH = 255


def _count_run(data: bytes, start: int) -> int:
    if start >= len(data):
        return 0
    value = data[start]
    count = 0
    while start + count < len(data) and data[start + count] == value:
        count += 1
        if count >= MAX_COUNT:
            break
    return count


def encode(data: bytes) -> bytes:
    result = bytearray()
    i = 0
    n = len(data)

    while i < n:
        run_len = _count_run(data, i)

        if run_len >= MIN_RUN_LENGTH:
            chunk_size = min(run_len, MAX_COUNT)
            result.append(ESC_BYTE)
            result.append(TYPE_RUN)
            result.append(chunk_size)
            result.append(data[i])
            i += chunk_size
        else:
            literal_start = i
            literal_buf = bytearray()

            while i < n and len(literal_buf) < MAX_LITERAL_LENGTH:
                run_len_here = _count_run(data, i)
                if run_len_here >= MIN_RUN_LENGTH:
                    break
                literal_buf.append(data[i])
                i += 1

            if len(literal_buf) == 1 and literal_buf[0] == ESC_BYTE:
                result.append(ESC_BYTE)
                result.append(TYPE_ESC_ESCAPE)
            else:
                result.append(ESC_BYTE)
                result.append(TYPE_LITERAL)
                result.append(len(literal_buf))
                result.extend(literal_buf)

    return bytes(result)


def decode(data: bytes, expected_length: int | None = None) -> bytes:
    result = bytearray()
    i = 0
    n = len(data)

    while i < n:
        if data[i] != ESC_BYTE:
            raise RLETruncatedDataError(
                f"Expected escape byte at position {i}, got 0x{data[i]:02x}"
            )

        i += 1
        if i >= n:
            raise RLETruncatedDataError(
                "Truncated escape sequence: missing type byte"
            )

        seq_type = data[i]
        i += 1

        if seq_type == TYPE_ESC_ESCAPE:
            result.append(ESC_BYTE)

        elif seq_type == TYPE_RUN:
            if i >= n:
                raise RLETruncatedDataError(
                    "Truncated run sequence: missing count byte"
                )
            count = data[i]
            i += 1

            if count < MIN_RUN_LENGTH:
                raise RLEInvalidCountError(
                    f"Invalid run count: {count}, must be >= {MIN_RUN_LENGTH}"
                )

            if i >= n:
                raise RLETruncatedDataError(
                    "Truncated run sequence: missing value byte"
                )
            value = data[i]
            i += 1

            result.extend(bytes([value]) * count)

        elif seq_type == TYPE_LITERAL:
            if i >= n:
                raise RLETruncatedDataError(
                    "Truncated literal sequence: missing length byte"
                )
            length = data[i]
            i += 1

            if length == 0:
                raise RLEInvalidLengthError("Literal length cannot be zero")

            if i + length > n:
                raise RLETruncatedDataError(
                    f"Literal length {length} exceeds remaining data "
                    f"({n - i} bytes)"
                )

            result.extend(data[i : i + length])
            i += length

        else:
            raise RLETruncatedDataError(
                f"Unknown escape sequence type: 0x{seq_type:02x}"
            )

    if expected_length is not None and len(result) != expected_length:
        raise RLEOutputLengthMismatchError(
            f"Decoded output length {len(result)} does not match "
            f"expected length {expected_length}"
        )

    return bytes(result)


class RLEEncoder:
    def __init__(self) -> None:
        self._buffer = bytearray()
        self._output = bytearray()
        self._finished = False

    def write(self, data: bytes) -> None:
        if self._finished:
            raise RuntimeError("Encoder has already been finished")
        self._buffer.extend(data)
        self._process_buffer()

    def _process_buffer(self) -> None:
        n = len(self._buffer)
        i = 0

        while i < n:
            run_len = self._count_run_from(i)

            if run_len >= MIN_RUN_LENGTH:
                if run_len < MAX_COUNT and i + run_len == n:
                    break
                chunk_size = min(run_len, MAX_COUNT)
                self._output.append(ESC_BYTE)
                self._output.append(TYPE_RUN)
                self._output.append(chunk_size)
                self._output.append(self._buffer[i])
                i += chunk_size
            else:
                break

        if i > 0:
            self._buffer = self._buffer[i:]

    def _count_run_from(self, start: int) -> int:
        if start >= len(self._buffer):
            return 0
        value = self._buffer[start]
        count = 0
        while start + count < len(self._buffer) and self._buffer[start + count] == value:
            count += 1
            if count >= MAX_COUNT:
                break
        return count

    def finish(self) -> bytes:
        if self._finished:
            return bytes(self._output)

        while self._buffer:
            run_len = self._count_run_from(0)

            if run_len >= MIN_RUN_LENGTH:
                chunk_size = min(run_len, MAX_COUNT)
                self._output.append(ESC_BYTE)
                self._output.append(TYPE_RUN)
                self._output.append(chunk_size)
                self._output.append(self._buffer[0])
                self._buffer = self._buffer[chunk_size:]
            else:
                take = min(len(self._buffer), MAX_LITERAL_LENGTH)
                literal = self._buffer[:take]
                self._buffer = self._buffer[take:]

                if len(literal) == 1 and literal[0] == ESC_BYTE:
                    self._output.append(ESC_BYTE)
                    self._output.append(TYPE_ESC_ESCAPE)
                else:
                    self._output.append(ESC_BYTE)
                    self._output.append(TYPE_LITERAL)
                    self._output.append(len(literal))
                    self._output.extend(literal)

        self._finished = True
        return bytes(self._output)

    def reset(self) -> None:
        self._buffer.clear()
        self._output.clear()
        self._finished = False


class RLEDecoder:
    def __init__(self) -> None:
        self._buffer = bytearray()
        self._output = bytearray()
        self._finished = False

    def write(self, data: bytes) -> bytes:
        if self._finished:
            raise RuntimeError("Decoder has already been finished")
        self._buffer.extend(data)
        return self._process_buffer()

    def _process_buffer(self) -> bytes:
        result = bytearray()
        i = 0
        n = len(self._buffer)

        while i < n:
            if self._buffer[i] != ESC_BYTE:
                raise RLETruncatedDataError(
                    f"Expected escape byte at position {i}, got 0x{self._buffer[i]:02x}"
                )

            if i + 1 >= n:
                break

            seq_type = self._buffer[i + 1]

            if seq_type == TYPE_ESC_ESCAPE:
                if i + 2 > n:
                    break
                result.append(ESC_BYTE)
                i += 2

            elif seq_type == TYPE_RUN:
                if i + 3 >= n:
                    break
                count = self._buffer[i + 2]
                if count < MIN_RUN_LENGTH:
                    raise RLEInvalidCountError(
                        f"Invalid run count: {count}, must be >= {MIN_RUN_LENGTH}"
                    )
                value = self._buffer[i + 3]
                result.extend(bytes([value]) * count)
                i += 4

            elif seq_type == TYPE_LITERAL:
                if i + 2 >= n:
                    break
                length = self._buffer[i + 2]
                if length == 0:
                    raise RLEInvalidLengthError("Literal length cannot be zero")
                if i + 3 + length > n:
                    break
                result.extend(self._buffer[i + 3 : i + 3 + length])
                i += 3 + length

            else:
                if i + 2 > n:
                    break
                raise RLETruncatedDataError(
                    f"Unknown escape sequence type: 0x{seq_type:02x}"
                )

        if i > 0:
            self._buffer = self._buffer[i:]

        if result:
            self._output.extend(result)

        return bytes(result)

    def finish(self, expected_length: int | None = None) -> bytes:
        if self._finished:
            return bytes(self._output)

        if self._buffer:
            raise RLETruncatedDataError(
                f"Truncated data: {len(self._buffer)} bytes remaining in buffer"
            )

        if expected_length is not None and len(self._output) != expected_length:
            raise RLEOutputLengthMismatchError(
                f"Decoded output length {len(self._output)} does not match "
                f"expected length {expected_length}"
            )

        self._finished = True
        return bytes(self._output)

    def reset(self) -> None:
        self._buffer.clear()
        self._output.clear()
        self._finished = False
