from __future__ import annotations

import struct
from typing import List, Optional

from .delta import compute_deltas
from .exceptions import (
    TsDeltaCompressionError,
    ValueOutOfRangeError,
)
from .models import CompressedBlock, CompressionStats, DeltaResult, TsDeltaConfig
from .simple8b import count_blocks, simple8b_pack
from .zigzag import zigzag_encode_list


HEADER_FORMAT = "<q q I I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class TsDeltaCompressor:
    def __init__(self, config: Optional[TsDeltaConfig] = None) -> None:
        self._config = config or TsDeltaConfig()
        self._timestamps: List[int] = []
        self._stats: Optional[CompressionStats] = None

    def write(self, timestamp: int) -> None:
        if not isinstance(timestamp, int):
            raise TsDeltaCompressionError(
                f"Timestamp must be integer, got {type(timestamp).__name__}"
            )
        self._timestamps.append(timestamp)

    def write_all(self, timestamps: List[int]) -> None:
        for ts in timestamps:
            self.write(ts)

    def compress(self) -> bytes:
        if not self._timestamps:
            return self._compress_empty()

        delta_result = compute_deltas(
            self._timestamps,
            validate=self._config.validate_strictly_increasing,
        )

        return self._compress_from_deltas(delta_result)

    def _compress_empty(self) -> bytes:
        self._stats = CompressionStats(
            original_count=0,
            compressed_bytes=HEADER_SIZE,
            original_bytes=0,
            first_order_count=0,
            second_order_count=0,
            simple8b_blocks=0,
        )

        header = struct.pack(HEADER_FORMAT, 0, 0, 0, 0)
        return header

    def _compress_from_deltas(self, delta_result: DeltaResult) -> bytes:
        second_order = delta_result.second_order_deltas
        zigzag_encoded = zigzag_encode_list(second_order, max_bits=60)
        simple8b_data = simple8b_pack(zigzag_encoded)

        base_timestamp = delta_result.base_timestamp
        first_delta = delta_result.first_delta if delta_result.first_delta is not None else 0
        value_count = len(self._timestamps)
        simple8b_length = len(simple8b_data)

        for val in second_order:
            max_abs = max(abs(val), 1)
            if max_abs > self._config.max_second_order_delta:
                raise ValueOutOfRangeError(
                    f"Second order delta {val} exceeds max allowed "
                    f"{self._config.max_second_order_delta}"
                )

        header = struct.pack(
            HEADER_FORMAT,
            base_timestamp,
            first_delta,
            value_count,
            simple8b_length,
        )

        compressed_data = header + simple8b_data

        self._stats = CompressionStats(
            original_count=value_count,
            compressed_bytes=len(compressed_data),
            original_bytes=value_count * 8,
            first_order_count=len(delta_result.first_order_deltas),
            second_order_count=len(second_order),
            simple8b_blocks=count_blocks(simple8b_data) if simple8b_data else 0,
        )

        return compressed_data

    def get_compressed_data(self) -> bytes:
        return self.compress()

    def get_stats(self) -> CompressionStats:
        if self._stats is None:
            self.compress()
        assert self._stats is not None
        return self._stats

    def reset(self) -> None:
        self._timestamps = []
        self._stats = None

    @property
    def total_timestamps(self) -> int:
        return len(self._timestamps)

    def __enter__(self) -> "TsDeltaCompressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.reset()


def compress_timestamps(
    timestamps: List[int],
    config: Optional[TsDeltaConfig] = None,
) -> CompressedBlock:
    compressor = TsDeltaCompressor(config=config)
    compressor.write_all(timestamps)
    data = compressor.get_compressed_data()
    stats = compressor.get_stats()

    if len(timestamps) == 0:
        return CompressedBlock(data=data, value_count=0, base_timestamp=0, first_delta=None)
    if len(timestamps) == 1:
        return CompressedBlock(data=data, value_count=1, base_timestamp=timestamps[0], first_delta=None)

    delta_result = compute_deltas(timestamps, validate=config.validate_strictly_increasing if config else True)
    return CompressedBlock(
        data=data,
        value_count=stats.original_count,
        base_timestamp=delta_result.base_timestamp,
        first_delta=delta_result.first_delta,
    )
