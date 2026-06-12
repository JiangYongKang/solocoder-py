from __future__ import annotations

from typing import List, Optional

from .crc import CrcCalculator
from .exceptions import (
    CrcCheckError,
    FrameTooLargeError,
    IncompleteFrameError,
    VersionIncompatibleError,
)
from .models import DecodeResult, Frame, FrameConfig


class FrameDecoder:
    def __init__(self, config: Optional[FrameConfig] = None) -> None:
        self._config = config or FrameConfig()
        self._buffer = bytearray()

    @property
    def config(self) -> FrameConfig:
        return self._config

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def feed(self, data: bytes) -> None:
        self._buffer.extend(data)

    def clear(self) -> None:
        self._buffer.clear()

    def decode_one(self) -> DecodeResult:
        try:
            frame, consumed = self._try_decode_frame()
            return DecodeResult(frame=frame, consumed=consumed, waiting_for_more=False)
        except IncompleteFrameError:
            return DecodeResult(waiting_for_more=True)

    def decode_all(self) -> List[Frame]:
        frames: List[Frame] = []
        while True:
            result = self.decode_one()
            if result.frame is not None:
                frames.append(result.frame)
            else:
                break
        return frames

    def _try_decode_frame(self) -> tuple[Frame, int]:
        header_size = self._config.header_size
        crc_size = self._config.crc_size
        overhead = self._config.overhead_size

        if len(self._buffer) < header_size:
            raise IncompleteFrameError("Incomplete header")

        version = int.from_bytes(
            self._buffer[: self._config.version_size],
            byteorder=self._config.byte_order,
            signed=False,
        )

        length_offset = self._config.version_size
        payload_length = int.from_bytes(
            self._buffer[length_offset : length_offset + self._config.length_prefix_size],
            byteorder=self._config.byte_order,
            signed=False,
        )

        if payload_length > self._config.max_payload_size:
            self._consume_bytes(header_size)
            raise FrameTooLargeError(
                f"Payload length {payload_length} exceeds max {self._config.max_payload_size}"
            )

        total_frame_size = overhead + payload_length

        if len(self._buffer) < total_frame_size:
            raise IncompleteFrameError(
                f"Need {total_frame_size} bytes, have {len(self._buffer)}"
            )

        frame_bytes = bytes(self._buffer[:total_frame_size])
        payload_start = header_size
        payload_end = payload_start + payload_length
        payload = frame_bytes[payload_start:payload_end]

        crc_start = payload_end
        crc_bytes = frame_bytes[crc_start : crc_start + crc_size]
        received_crc = int.from_bytes(
            crc_bytes,
            byteorder=self._config.byte_order,
            signed=False,
        )

        if not self._is_version_supported(version):
            self._consume_bytes(total_frame_size)
            raise VersionIncompatibleError(
                f"Version {version} not supported. "
                f"Supported range: [{self._config.min_supported_version}, {self._config.max_supported_version}]"
            )

        frame_without_crc = frame_bytes[: header_size + payload_length]
        calculated_crc = CrcCalculator.calculate(frame_without_crc, crc_size)

        if calculated_crc != received_crc:
            self._consume_bytes(total_frame_size)
            raise CrcCheckError(
                f"CRC mismatch: expected {calculated_crc:#0{2 + 2 * crc_size}x}, "
                f"got {received_crc:#0{2 + 2 * crc_size}x}"
            )

        self._consume_bytes(total_frame_size)

        frame = Frame(version=version, payload=payload, crc=received_crc)
        return frame, total_frame_size

    def _is_version_supported(self, version: int) -> bool:
        return (
            self._config.min_supported_version <= version
            <= self._config.max_supported_version
        )

    def _consume_bytes(self, count: int) -> bytes:
        data = bytes(self._buffer[:count])
        self._buffer = self._buffer[count:]
        return data
