from __future__ import annotations

import io
from typing import List, Optional

from .exceptions import (
    CorruptedDataError,
    DataLengthMismatchError,
    DeltaDecompressionError,
    TruncatedDataError,
)
from .models import CompressionStats, DeltaEncodingConfig
from .varint import decode_anchor, decode_int


class DeltaDecompressor:
    def __init__(
        self,
        config: Optional[DeltaEncodingConfig] = None,
        input_stream: Optional[io.BytesIO] = None,
    ) -> None:
        self._config = config or DeltaEncodingConfig()
        self._input = input_stream or io.BytesIO()
        self._anchor: Optional[int] = None
        self._values_since_anchor: int = 0
        self._total_values: int = 0
        self._anchor_count: int = 0
        self._offset: int = 0
        self._decoded_values: List[int] = []

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

    def set_input_data(self, data: bytes) -> None:
        self._input = io.BytesIO(data)
        self._offset = 0
        self._anchor = None
        self._values_since_anchor = 0
        self._total_values = 0
        self._anchor_count = 0
        self._decoded_values = []

    def read(self) -> int:
        data = self._input.getvalue() if hasattr(self._input, "getvalue") else None
        if data is None:
            raise DeltaDecompressionError("Input stream does not support random access")

        if self._offset >= len(data):
            raise EOFError("No more data to decompress")

        try:
            value, consumed, is_anchor = decode_int(
                data, self._offset, self._config.signed
            )

            if is_anchor:
                self._anchor = value
                self._values_since_anchor = 0
                self._anchor_count += 1
                result = value
            else:
                if self._anchor is None:
                    raise CorruptedDataError(
                        "Delta value encountered before anchor"
                    )
                result = self._anchor + value
        except TruncatedDataError:
            raise
        except CorruptedDataError:
            raise
        except Exception as e:
            raise CorruptedDataError(f"Failed to decode value at offset {self._offset}: {e}")

        self._offset += consumed
        self._values_since_anchor += 1
        self._total_values += 1
        self._decoded_values.append(result)
        return result

    def read_all(self, expected_count: Optional[int] = None) -> List[int]:
        values: List[int] = []
        try:
            while True:
                values.append(self.read())
        except EOFError:
            pass

        if expected_count is not None and len(values) != expected_count:
            raise DataLengthMismatchError(
                f"Expected {expected_count} values, but decoded {len(values)}"
            )

        return values

    def has_more_data(self) -> bool:
        data = self._input.getvalue() if hasattr(self._input, "getvalue") else b""
        return self._offset < len(data)

    def get_stats(self) -> CompressionStats:
        data = self._input.getvalue() if hasattr(self._input, "getvalue") else b""
        compressed_size = len(data)
        return CompressionStats(
            original_size=self._total_values * 8,
            compressed_size=compressed_size,
            anchor_count=self._anchor_count,
            total_values=self._total_values,
        )

    def reset(self) -> None:
        self._anchor = None
        self._values_since_anchor = 0
        self._total_values = 0
        self._anchor_count = 0
        self._offset = 0
        self._decoded_values = []
        if hasattr(self._input, "seek"):
            self._input.seek(0)

    def close(self) -> None:
        if hasattr(self._input, "close"):
            self._input.close()

    def __enter__(self) -> "DeltaDecompressor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
