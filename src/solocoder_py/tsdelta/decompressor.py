from __future__ import annotations

import struct
from typing import List, Optional

from .delta import reconstruct_timestamps
from .exceptions import (
    CorruptedDataError,
    TsDeltaDecompressionError,
    TruncatedDataError,
)
from .models import CompressionStats, TsDeltaConfig
from .simple8b import simple8b_unpack
from .zigzag import zigzag_decode_list


HEADER_FORMAT = "<q q I I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class TsDeltaDecompressor:
    def __init__(self, config: Optional[TsDeltaConfig] = None) -> None:
        self._config = config or TsDeltaConfig()
        self._input_data: Optional[bytes] = None
        self._read_pos: int = 0
        self._timestamps: List[int] = []
        self._stats: Optional[CompressionStats] = None
        self._header_parsed: bool = False
        self._base_timestamp: int = 0
        self._first_delta: Optional[int] = None
        self._value_count: int = 0
        self._simple8b_length: int = 0
        self._simple8b_data: bytes = b""
        self._decoded_second_order: Optional[List[int]] = None

    def set_input_data(self, data: bytes) -> None:
        self._input_data = data
        self._read_pos = 0
        self._timestamps = []
        self._stats = None
        self._header_parsed = False
        self._decoded_second_order = None

    def decompress(self) -> List[int]:
        if self._input_data is None:
            raise TsDeltaDecompressionError("No input data set")

        if not self._header_parsed:
            self._parse_header()

        if self._value_count == 0:
            self._stats = CompressionStats(
                original_count=0,
                compressed_bytes=len(self._input_data),
                original_bytes=0,
                first_order_count=0,
                second_order_count=0,
                simple8b_blocks=0,
            )
            return []

        if self._decoded_second_order is None:
            self._decode_simple8b()

        assert self._decoded_second_order is not None

        timestamps = reconstruct_timestamps(
            base_timestamp=self._base_timestamp,
            first_delta=self._first_delta,
            second_order_deltas=self._decoded_second_order,
            expected_count=self._value_count,
        )

        self._timestamps = timestamps

        self._stats = CompressionStats(
            original_count=self._value_count,
            compressed_bytes=len(self._input_data),
            original_bytes=self._value_count * 8,
            first_order_count=max(self._value_count - 1, 0),
            second_order_count=len(self._decoded_second_order),
            simple8b_blocks=(self._simple8b_length // 8) if self._simple8b_length > 0 else 0,
        )

        return timestamps

    def _parse_header(self) -> None:
        assert self._input_data is not None

        if len(self._input_data) < HEADER_SIZE:
            raise TruncatedDataError(
                f"Compressed data too short: expected at least {HEADER_SIZE} bytes, "
                f"got {len(self._input_data)}"
            )

        header = self._input_data[:HEADER_SIZE]
        self._base_timestamp, first_delta_raw, self._value_count, self._simple8b_length = struct.unpack(
            HEADER_FORMAT, header
        )

        if self._value_count == 0:
            self._first_delta = None
        elif self._value_count == 1:
            self._first_delta = None
        else:
            self._first_delta = first_delta_raw

        self._read_pos = HEADER_SIZE

        if self._simple8b_length > 0 and self._simple8b_length % 8 != 0:
            raise CorruptedDataError(
                f"Invalid Simple-8b length: {self._simple8b_length} is not a multiple of 8"
            )

        expected_total = HEADER_SIZE + self._simple8b_length
        if len(self._input_data) < expected_total:
            raise TruncatedDataError(
                f"Truncated compressed data: expected {expected_total} bytes, "
                f"got {len(self._input_data)}"
            )

        if len(self._input_data) > expected_total:
            raise CorruptedDataError(
                f"Corrupted compressed data: expected {expected_total} bytes, "
                f"got {len(self._input_data)} (extra data after Simple-8b block)"
            )

        self._simple8b_data = self._input_data[HEADER_SIZE:expected_total]
        self._header_parsed = True

    def _decode_simple8b(self) -> None:
        if self._simple8b_length == 0 or self._value_count <= 2:
            self._decoded_second_order = []
            return

        expected_second_order_count = self._value_count - 2

        zigzag_encoded = simple8b_unpack(
            self._simple8b_data,
            expected_count=expected_second_order_count,
        )

        if len(zigzag_encoded) < expected_second_order_count:
            raise TruncatedDataError(
                f"Expected {expected_second_order_count} second order deltas, "
                f"got {len(zigzag_encoded)}"
            )

        if len(zigzag_encoded) > expected_second_order_count:
            zigzag_encoded = zigzag_encoded[:expected_second_order_count]

        self._decoded_second_order = zigzag_decode_list(zigzag_encoded, max_bits=60)

    def read_all(self) -> List[int]:
        return self.decompress()

    def get_stats(self) -> CompressionStats:
        if self._stats is None:
            self.decompress()
        assert self._stats is not None
        return self._stats

    def reset(self) -> None:
        self._input_data = None
        self._read_pos = 0
        self._timestamps = []
        self._stats = None
        self._header_parsed = False
        self._base_timestamp = 0
        self._first_delta = None
        self._value_count = 0
        self._simple8b_length = 0
        self._simple8b_data = b""
        self._decoded_second_order = None

    @property
    def value_count(self) -> int:
        if not self._header_parsed and self._input_data is not None:
            self._parse_header()
        return self._value_count

    def __enter__(self) -> "TsDeltaDecompressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.reset()


def decompress_timestamps(
    data: bytes,
    config: Optional[TsDeltaConfig] = None,
) -> List[int]:
    decompressor = TsDeltaDecompressor(config=config)
    decompressor.set_input_data(data)
    return decompressor.read_all()
