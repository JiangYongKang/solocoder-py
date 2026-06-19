from __future__ import annotations

import io
from typing import Dict, List, Optional

from .exceptions import ValueOutOfRangeError
from .models import CompressionStats, LZ77Config, MatchResult


class LZ77Compressor:
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
        self._hash_table: Dict[int, List[int]] = {}
        self._literal_buffer: bytearray = bytearray()
        self._input_data: bytes = b""
        self._input_pos: int = 0
        self._window_start: int = 0
        self._next_cleanup_pos: int = 0
        self._total_input: int = 0
        self._match_count: int = 0
        self._literal_count: int = 0
        self._hash_chain_truncations: int = 0

    @property
    def config(self) -> LZ77Config:
        return self._config

    @property
    def total_input(self) -> int:
        return self._total_input

    @property
    def match_count(self) -> int:
        return self._match_count

    @property
    def literal_count(self) -> int:
        return self._literal_count

    def _hash_bytes(self, data: bytes, pos: int) -> int:
        n = self._config.min_match_length
        if pos + n > len(data):
            return 0
        h = 0
        for i in range(n):
            h = (h * 257 + data[pos + i]) & 0xFFFFFFFF
        return h

    def _update_hash_chain(self, pos: int) -> None:
        if pos + self._config.min_match_length > len(self._input_data):
            return
        h = self._hash_bytes(self._input_data, pos)
        if h not in self._hash_table:
            self._hash_table[h] = []
        chain = self._hash_table[h]
        chain.insert(0, pos)
        if len(chain) > self._config.hash_chain_limit:
            chain.pop()
            self._hash_chain_truncations += 1

    def _slide_window(self, new_pos: int) -> None:
        window_size = self._config.window_size
        new_window_start = max(0, new_pos - window_size)

        if new_window_start > self._window_start:
            self._clean_hash_table(new_window_start)
            self._window_start = new_window_start

    def _clean_hash_table(self, window_start: int) -> None:
        to_delete = []
        for h, positions in self._hash_table.items():
            new_positions = [p for p in positions if p >= window_start]
            if new_positions:
                self._hash_table[h] = new_positions
            else:
                to_delete.append(h)
        for h in to_delete:
            del self._hash_table[h]

    def _find_longest_match(self) -> MatchResult:
        min_len = self._config.min_match_length
        max_len = self._config.max_match_length
        input_data = self._input_data
        pos = self._input_pos
        remaining = len(input_data) - pos

        if remaining < min_len:
            return MatchResult(distance=0, length=0, found=False)

        h = self._hash_bytes(input_data, pos)
        if h not in self._hash_table:
            return MatchResult(distance=0, length=0, found=False)

        chain = self._hash_table[h]
        window_start = max(0, pos - self._config.window_size)

        best_len = 0
        best_dist = 0

        for match_pos in chain:
            if match_pos < window_start:
                continue
            if match_pos >= pos:
                continue

            dist = pos - match_pos
            if dist <= 0 or dist > self._config.window_size:
                continue

            max_possible = min(remaining, max_len, dist + remaining if False else remaining)
            max_possible = min(remaining, max_len)

            current_len = 0
            while (
                current_len < max_possible
                and input_data[match_pos + current_len] == input_data[pos + current_len]
            ):
                current_len += 1

            if current_len > best_len:
                best_len = current_len
                best_dist = dist
                if best_len >= max_len:
                    break

        if best_len >= min_len:
            return MatchResult(distance=best_dist, length=best_len, found=True)
        else:
            return MatchResult(distance=0, length=0, found=False)

    def _flush_literal_block(self) -> None:
        if not self._literal_buffer:
            return

        while len(self._literal_buffer) > 0:
            chunk_size = min(len(self._literal_buffer), self._config.literal_block_max)
            self._write_literal_block(bytes(self._literal_buffer[:chunk_size]))
            self._literal_buffer = self._literal_buffer[chunk_size:]

    def _write_literal_block(self, data: bytes) -> None:
        length = len(data)
        max_len = self._config.literal_block_max
        if length < 1 or length > max_len:
            raise ValueOutOfRangeError(
                f"Literal block length {length} out of range "
                f"[1, {max_len}]"
            )
        if length - 1 > 0x7F:
            raise ValueOutOfRangeError(
                f"Literal block length {length} exceeds encoding limit 128"
            )
        length_byte = length - 1
        self._output.write(bytes([length_byte]))
        self._output.write(data)
        self._literal_count += length

    def _write_match_pair(self, distance: int, length: int) -> None:
        min_len = self._config.min_match_length
        max_len = self._config.max_match_length
        max_dist = LZ77Config.MAX_DISTANCE
        max_length_offset = LZ77Config.MAX_LENGTH_OFFSET

        if distance < 1 or distance > self._config.window_size:
            raise ValueOutOfRangeError(
                f"Distance {distance} out of range [1, {self._config.window_size}]"
            )
        if distance > max_dist:
            raise ValueOutOfRangeError(
                f"Distance {distance} exceeds encoding limit {max_dist}"
            )
        if length < min_len or length > max_len:
            raise ValueOutOfRangeError(
                f"Length {length} out of range [{min_len}, {max_len}]"
            )

        length_offset = length - min_len
        if length_offset > max_length_offset:
            raise ValueOutOfRangeError(
                f"Length offset {length_offset} exceeds encoding limit {max_length_offset}"
            )

        flag_byte = 0x80
        dist_high = (distance >> 8) & 0xFF
        dist_low = distance & 0xFF

        self._output.write(bytes([flag_byte, length_offset, dist_high, dist_low]))
        self._match_count += 1

    def compress(self, data: bytes) -> bytes:
        self._input_data = data
        self._input_pos = 0
        self._window_start = 0
        self._next_cleanup_pos = 0
        self._total_input = len(data)
        self._hash_table = {}
        self._literal_buffer = bytearray()
        if self._output_owned:
            self._output = io.BytesIO()
        self._match_count = 0
        self._literal_count = 0
        self._hash_chain_truncations = 0

        self._process_all()
        self._flush_literal_block()

        return self._output.getvalue()

    def _process_all(self) -> None:
        data = self._input_data
        total_len = len(data)
        min_len = self._config.min_match_length
        cleanup_interval = max(self._config.window_size // 8, 256)

        while self._input_pos < total_len:
            if self._input_pos + min_len <= total_len:
                self._update_hash_chain(self._input_pos)

            if self._input_pos >= self._next_cleanup_pos:
                self._slide_window(self._input_pos)
                self._next_cleanup_pos = self._input_pos + cleanup_interval

            match = self._find_longest_match()

            if match.found:
                self._flush_literal_block()
                self._write_match_pair(match.distance, match.length)

                for i in range(1, match.length):
                    next_pos = self._input_pos + i
                    if next_pos + min_len <= total_len:
                        self._update_hash_chain(next_pos)

                self._input_pos += match.length
            else:
                self._literal_buffer.append(data[self._input_pos])
                if len(self._literal_buffer) >= self._config.literal_block_max:
                    self._flush_literal_block()
                self._input_pos += 1

    def get_compressed_data(self) -> bytes:
        return self._output.getvalue()

    def get_stats(self) -> CompressionStats:
        compressed_size = len(self._output.getvalue())
        return CompressionStats(
            original_size=self._total_input,
            compressed_size=compressed_size,
            literal_count=self._literal_count,
            match_count=self._match_count,
            hash_chain_truncations=self._hash_chain_truncations,
        )

    def reset(self) -> None:
        self._hash_table = {}
        self._literal_buffer = bytearray()
        self._input_data = b""
        self._input_pos = 0
        self._window_start = 0
        self._next_cleanup_pos = 0
        self._total_input = 0
        self._match_count = 0
        self._literal_count = 0
        self._hash_chain_truncations = 0
        if self._output_owned:
            self._output = io.BytesIO()

    def close(self) -> None:
        if hasattr(self._output, "close"):
            self._output.close()

    def __enter__(self) -> "LZ77Compressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
