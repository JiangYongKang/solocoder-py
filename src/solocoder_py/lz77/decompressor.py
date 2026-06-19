from __future__ import annotations

import io
from typing import Optional

from .exceptions import (
    CorruptedDataError,
    DistanceOutOfRangeError,
    LengthOutOfRangeError,
    TruncatedDataError,
)
from .models import CompressionStats, LZ77Config


class LZ77Decompressor:
    def __init__(
        self,
        config: Optional[LZ77Config] = None,
        output_stream: Optional[io.BytesIO] = None,
    ) -> None:
        self._config = config or LZ77Config()
        self._output = output_stream
        self._output_owned = output_stream is None
        if self._output_owned:
            self._output = io.BytesIO()
        self._input_data: bytes = b""
        self._input_pos: int = 0
        self._output_buffer: bytearray = bytearray()
        self._total_output: int = 0
        self._match_count: int = 0
        self._literal_count: int = 0

    @property
    def config(self) -> LZ77Config:
        return self._config

    @property
    def total_output(self) -> int:
        return self._total_output

    @property
    def match_count(self) -> int:
        return self._match_count

    @property
    def literal_count(self) -> int:
        return self._literal_count

    def set_input_data(self, data: bytes) -> None:
        self._input_data = data
        self._input_pos = 0
        self._output_buffer = bytearray()
        self._total_output = 0
        self._match_count = 0
        self._literal_count = 0
        if self._output_owned:
            self._output = io.BytesIO()

    def decompress(self, data: bytes) -> bytes:
        self.set_input_data(data)
        self._process_all()
        self._flush_output()
        return bytes(self._output_buffer)

    def _flush_output(self) -> None:
        if self._output is not None and self._output_buffer:
            self._output.write(bytes(self._output_buffer))

    def _process_all(self) -> None:
        while self._input_pos < len(self._input_data):
            self._process_one_element()

    def _process_one_element(self) -> None:
        if self._input_pos >= len(self._input_data):
            raise TruncatedDataError("Unexpected end of compressed data")

        flag_byte = self._input_data[self._input_pos]
        self._input_pos += 1

        if flag_byte & 0x80 == 0:
            self._process_literal_block(flag_byte)
        else:
            self._process_match_pair(flag_byte)

    def _process_literal_block(self, flag_byte: int) -> None:
        length = (flag_byte & 0x7F) + 1

        if length < 1 or length > self._config.literal_block_max:
            raise CorruptedDataError(
                f"Invalid literal block length: {length}"
            )

        if self._input_pos + length > len(self._input_data):
            raise TruncatedDataError(
                f"Truncated literal block: expected {length} bytes, "
                f"got {len(self._input_data) - self._input_pos}"
            )

        literal_data = self._input_data[self._input_pos : self._input_pos + length]
        self._input_pos += length

        self._output_buffer.extend(literal_data)
        self._literal_count += length
        self._total_output += length

    def _process_match_pair(self, flag_byte: int) -> None:
        if self._input_pos + 3 > len(self._input_data):
            raise TruncatedDataError(
                "Truncated match pair: not enough bytes"
            )

        length_offset = self._input_data[self._input_pos]
        self._input_pos += 1
        length = length_offset + self._config.min_match_length

        if length > self._config.max_match_length:
            raise LengthOutOfRangeError(
                f"Match length {length} exceeds maximum {self._config.max_match_length}"
            )

        dist_high = self._input_data[self._input_pos]
        dist_low = self._input_data[self._input_pos + 1]
        self._input_pos += 2

        distance = (dist_high << 8) | dist_low

        if distance < 1:
            raise DistanceOutOfRangeError(
                f"Invalid distance: {distance}"
            )
        if distance > len(self._output_buffer):
            raise DistanceOutOfRangeError(
                f"Distance {distance} exceeds current output size {len(self._output_buffer)}"
            )
        if distance > self._config.window_size:
            raise DistanceOutOfRangeError(
                f"Distance {distance} exceeds window size {self._config.window_size}"
            )

        start_pos = len(self._output_buffer) - distance
        for i in range(length):
            self._output_buffer.append(self._output_buffer[start_pos + i])

        self._match_count += 1
        self._total_output += length

    def get_decompressed_data(self) -> bytes:
        return bytes(self._output_buffer)

    def get_stats(self) -> CompressionStats:
        compressed_size = len(self._input_data)
        return CompressionStats(
            original_size=self._total_output,
            compressed_size=compressed_size,
            literal_count=self._literal_count,
            match_count=self._match_count,
            hash_chain_truncations=0,
        )

    def reset(self) -> None:
        self._input_data = b""
        self._input_pos = 0
        self._output_buffer = bytearray()
        self._total_output = 0
        self._match_count = 0
        self._literal_count = 0
        if self._output_owned:
            self._output = io.BytesIO()

    def close(self) -> None:
        if hasattr(self._output, "close"):
            self._output.close()

    def __enter__(self) -> "LZ77Decompressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
