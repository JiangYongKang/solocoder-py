from __future__ import annotations

from .base import _BaseDecoder, _BaseEncoder


class Base32Encoder(_BaseEncoder):
    _ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    _BITS_PER_CHAR = 5

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


class Base32Decoder(_BaseDecoder):
    _ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    _BITS_PER_CHAR = 5

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


def b32encode(data: bytes, pad: bool = True, line_width: int = 0, newline: str = "\n") -> str:
    encoder = Base32Encoder(pad=pad, line_width=line_width, newline=newline)
    return encoder.encode(data)


def b32decode(data: str, pad: bool = True) -> bytes:
    decoder = Base32Decoder(pad=pad)
    return decoder.decode(data)
