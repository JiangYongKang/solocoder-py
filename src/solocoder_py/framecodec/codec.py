from __future__ import annotations

from typing import List, Optional

from .decoder import FrameDecoder
from .encoder import FrameEncoder
from .exceptions import FrameCodecError
from .models import DecodeResult, Frame, FrameConfig


class FrameCodec:
    def __init__(self, config: Optional[FrameConfig] = None) -> None:
        self._config = config or FrameConfig()
        self._encoder = FrameEncoder(self._config)
        self._decoder = FrameDecoder(self._config)

    @property
    def config(self) -> FrameConfig:
        return self._config

    @property
    def encoder(self) -> FrameEncoder:
        return self._encoder

    @property
    def decoder(self) -> FrameDecoder:
        return self._decoder

    def encode(self, payload: bytes, version: Optional[int] = None) -> bytes:
        return self._encoder.encode(payload, version=version)

    def encode_frame(self, frame: Frame) -> bytes:
        return self._encoder.encode_frame(frame)

    def feed(self, data: bytes) -> None:
        self._decoder.feed(data)

    def decode_one(self) -> DecodeResult:
        return self._decoder.decode_one()

    def decode_all(self) -> List[Frame]:
        return self._decoder.decode_all()

    def clear_buffer(self) -> None:
        self._decoder.clear()

    @property
    def buffer_size(self) -> int:
        return self._decoder.buffer_size
