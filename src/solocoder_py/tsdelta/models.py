from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class DeltaResult:
    first_order_deltas: List[int]
    second_order_deltas: List[int]
    base_timestamp: int
    first_delta: Optional[int] = None

    @property
    def count(self) -> int:
        return len(self.second_order_deltas)


@dataclass
class CompressionStats:
    original_count: int
    compressed_bytes: int
    original_bytes: int
    first_order_count: int
    second_order_count: int
    simple8b_blocks: int

    @property
    def compression_ratio(self) -> float:
        if self.original_bytes == 0:
            return 0.0
        return self.compressed_bytes / self.original_bytes

    @property
    def bits_per_value(self) -> float:
        if self.original_count == 0:
            return 0.0
        return (self.compressed_bytes * 8) / self.original_count


@dataclass
class Simple8bMode:
    selector: int
    bit_width: int
    max_value: int
    count: int

    @property
    def total_bits(self) -> int:
        return 4 + self.bit_width * self.count


SIMPLE8B_MODES: List[Simple8bMode] = [
    Simple8bMode(selector=0, bit_width=60, max_value=(1 << 60) - 1, count=1),
    Simple8bMode(selector=1, bit_width=30, max_value=(1 << 30) - 1, count=2),
    Simple8bMode(selector=2, bit_width=20, max_value=(1 << 20) - 1, count=3),
    Simple8bMode(selector=3, bit_width=15, max_value=(1 << 15) - 1, count=4),
    Simple8bMode(selector=4, bit_width=12, max_value=(1 << 12) - 1, count=5),
    Simple8bMode(selector=5, bit_width=10, max_value=(1 << 10) - 1, count=6),
    Simple8bMode(selector=6, bit_width=8, max_value=(1 << 8) - 1, count=7),
    Simple8bMode(selector=7, bit_width=7, max_value=(1 << 7) - 1, count=8),
    Simple8bMode(selector=8, bit_width=6, max_value=(1 << 6) - 1, count=10),
    Simple8bMode(selector=9, bit_width=5, max_value=(1 << 5) - 1, count=12),
    Simple8bMode(selector=10, bit_width=4, max_value=(1 << 4) - 1, count=15),
    Simple8bMode(selector=11, bit_width=3, max_value=(1 << 3) - 1, count=20),
    Simple8bMode(selector=12, bit_width=2, max_value=(1 << 2) - 1, count=30),
    Simple8bMode(selector=13, bit_width=1, max_value=(1 << 1) - 1, count=60),
    Simple8bMode(selector=14, bit_width=0, max_value=0, count=120),
]


@dataclass
class CompressedBlock:
    data: bytes
    value_count: int
    base_timestamp: int
    first_delta: Optional[int]

    def to_tuple(self) -> Tuple[bytes, int, int, Optional[int]]:
        return (self.data, self.value_count, self.base_timestamp, self.first_delta)


@dataclass
class TsDeltaConfig:
    validate_strictly_increasing: bool = True
    max_second_order_delta: int = (1 << 60) - 1

    def __post_init__(self) -> None:
        if self.max_second_order_delta < 0:
            from .exceptions import ValueOutOfRangeError
            raise ValueOutOfRangeError(
                f"max_second_order_delta must be >= 0, got {self.max_second_order_delta}"
            )
        if self.max_second_order_delta > (1 << 60) - 1:
            from .exceptions import ValueOutOfRangeError
            raise ValueOutOfRangeError(
                f"max_second_order_delta must be <= 2^60 - 1, got {self.max_second_order_delta}"
            )
