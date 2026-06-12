from __future__ import annotations

from typing import Optional

from .crc import CrcCalculator
from .exceptions import FrameTooLargeError, VersionIncompatibleError
from .models import Frame, FrameConfig


class FrameEncoder:
    def __init__(self, config: Optional[FrameConfig] = None) -> None:
        self._config = config or FrameConfig()

    @property
    def config(self) -> FrameConfig:
        return self._config

    def encode(self, payload: bytes, version: Optional[int] = None) -> bytes:
        if version is None:
            version = self._config.version

        if not (
            self._config.min_supported_version
            <= version
            <= self._config.max_supported_version
        ):
            raise VersionIncompatibleError(
                f"Version {version} not in supported range "
                f"[{self._config.min_supported_version}, {self._config.max_supported_version}]"
            )

        if len(payload) > self._config.max_payload_size:
            raise FrameTooLargeError(
                f"Payload size {len(payload)} exceeds maximum {self._config.max_payload_size}"
            )

        version_bytes = version.to_bytes(
            self._config.version_size,
            byteorder=self._config.byte_order,
            signed=False,
        )

        length_bytes = len(payload).to_bytes(
            self._config.length_prefix_size,
            byteorder=self._config.byte_order,
            signed=False,
        )

        frame_without_crc = version_bytes + length_bytes + payload

        crc_value = CrcCalculator.calculate(frame_without_crc, self._config.crc_size)
        crc_bytes = crc_value.to_bytes(
            self._config.crc_size,
            byteorder=self._config.byte_order,
            signed=False,
        )

        return frame_without_crc + crc_bytes

    def encode_frame(self, frame: Frame) -> bytes:
        return self.encode(frame.payload, version=frame.version)

    def calculate_frame_size(self, payload_size: int) -> int:
        return self._config.overhead_size + payload_size
