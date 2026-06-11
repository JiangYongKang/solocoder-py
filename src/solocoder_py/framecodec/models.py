from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FrameConfig:
    version: int = 1
    min_supported_version: int = 1
    max_supported_version: int = 2
    length_prefix_size: int = 2
    crc_size: int = 2
    version_size: int = 1
    max_payload_size: int = 65535
    byte_order: str = "big"

    def __post_init__(self) -> None:
        if self.version_size < 1:
            raise ValueError("version_size must be at least 1")
        if self.length_prefix_size < 1:
            raise ValueError("length_prefix_size must be at least 1")
        if self.crc_size < 1:
            raise ValueError("crc_size must be at least 1")
        if self.min_supported_version > self.max_supported_version:
            raise ValueError("min_supported_version must be <= max_supported_version")
        if self.version < self.min_supported_version:
            raise ValueError("version must be >= min_supported_version")
        if self.version > self.max_supported_version:
            raise ValueError("version must be <= max_supported_version")
        if self.max_payload_size < 0:
            raise ValueError("max_payload_size must be non-negative")

    @property
    def header_size(self) -> int:
        return self.version_size + self.length_prefix_size

    @property
    def overhead_size(self) -> int:
        return self.header_size + self.crc_size

    def max_frame_size(self) -> int:
        return self.overhead_size + self.max_payload_size


@dataclass
class Frame:
    version: int
    payload: bytes
    crc: int = 0

    @property
    def payload_size(self) -> int:
        return len(self.payload)


@dataclass
class DecodeResult:
    frame: Optional[Frame] = None
    consumed: int = 0
    waiting_for_more: bool = False
