from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class WidthMarker(int, Enum):
    WIDTH_1 = 0
    WIDTH_2 = 1
    WIDTH_4 = 2
    WIDTH_8 = 3


@dataclass
class CompressionStats:
    original_size: int
    compressed_size: int
    anchor_count: int
    total_values: int

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return self.compressed_size / self.original_size


@dataclass
class EncodedBlock:
    data: bytes
    value_count: int
    has_anchor: bool
    anchor_value: Optional[int] = None


class DeltaEncodingConfig:
    def __init__(
        self,
        anchor_interval: int = 100,
        max_width: WidthMarker = WidthMarker.WIDTH_8,
        signed: bool = True,
    ) -> None:
        if anchor_interval < 0:
            from .exceptions import InvalidAnchorIntervalError
            raise InvalidAnchorIntervalError(
                f"anchor_interval must be >= 0, got {anchor_interval}"
            )
        self._anchor_interval = anchor_interval
        self._max_width = max_width
        self._signed = signed

    @property
    def anchor_interval(self) -> int:
        return self._anchor_interval

    @property
    def max_width(self) -> WidthMarker:
        return self._max_width

    @property
    def signed(self) -> bool:
        return self._signed

    @property
    def max_value(self) -> int:
        width_map = {
            WidthMarker.WIDTH_1: 127,
            WidthMarker.WIDTH_2: 32767,
            WidthMarker.WIDTH_4: 2147483647,
            WidthMarker.WIDTH_8: 9223372036854775807,
        }
        return width_map[self._max_width]

    @property
    def min_value(self) -> int:
        width_map = {
            WidthMarker.WIDTH_1: -128,
            WidthMarker.WIDTH_2: -32768,
            WidthMarker.WIDTH_4: -2147483648,
            WidthMarker.WIDTH_8: -9223372036854775808,
        }
        return width_map[self._max_width]
