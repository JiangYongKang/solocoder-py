from __future__ import annotations

import io
from typing import List, Optional

from .exceptions import ValueOutOfRangeError
from .models import CompressionStats, DeltaEncodingConfig
from .varint import determine_width, encode_anchor, encode_int


class DeltaCompressor:
    def __init__(
        self,
        config: Optional[DeltaEncodingConfig] = None,
        output_stream: Optional[io.BytesIO] = None,
    ) -> None:
        self._config = config or DeltaEncodingConfig()
        self._output = output_stream or io.BytesIO()
        self._anchor: Optional[int] = None
        self._values_since_anchor: int = 0
        self._total_values: int = 0
        self._anchor_count: int = 0
        self._original_size: int = 0

    @property
    def config(self) -> DeltaEncodingConfig:
        return self._config

    @property
    def anchor(self) -> Optional[int]:
        return self._anchor

    @property
    def total_values(self) -> int:
        return self._total_values

    @property
    def anchor_count(self) -> int:
        return self._anchor_count

    def write(self, value: int) -> None:
        if self._config.signed:
            if value > self._config.max_value or value < self._config.min_value:
                raise ValueOutOfRangeError(
                    f"Value {value} is out of range "
                    f"[{self._config.min_value}, {self._config.max_value}]"
                )
        else:
            if value < 0 or value > self._config.max_value * 2 + 1:
                raise ValueOutOfRangeError(
                    f"Unsigned value {value} is out of range "
                    f"[0, {self._config.max_value * 2 + 1}]"
                )

        self._original_size += 8

        anchor_interval = self._config.anchor_interval

        should_reset_anchor = (
            self._anchor is None
            or (anchor_interval > 0 and self._values_since_anchor >= anchor_interval)
            or anchor_interval == 0
        )

        if not should_reset_anchor and self._anchor is not None:
            delta = value - self._anchor
            try:
                determine_width(delta, self._config.signed)
            except ValueOutOfRangeError:
                should_reset_anchor = True

        if should_reset_anchor:
            anchor_bytes = encode_anchor(value, self._config.signed)
            self._output.write(anchor_bytes)
            self._anchor = value
            self._values_since_anchor = 0
            self._anchor_count += 1
        else:
            delta = value - self._anchor
            delta_bytes = encode_int(delta, self._config.signed, is_anchor=False)
            self._output.write(delta_bytes)

        self._values_since_anchor += 1
        self._total_values += 1

    def write_all(self, values: List[int]) -> None:
        for value in values:
            self.write(value)

    def reset(self) -> None:
        self._anchor = None
        self._values_since_anchor = 0
        self._total_values = 0
        self._anchor_count = 0
        self._original_size = 0
        self._output = io.BytesIO()

    def get_compressed_data(self) -> bytes:
        return self._output.getvalue()

    def get_stats(self) -> CompressionStats:
        compressed_size = len(self._output.getvalue())
        return CompressionStats(
            original_size=self._original_size,
            compressed_size=compressed_size,
            anchor_count=self._anchor_count,
            total_values=self._total_values,
        )

    def close(self) -> None:
        if hasattr(self._output, "close"):
            self._output.close()

    def __enter__(self) -> "DeltaCompressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
