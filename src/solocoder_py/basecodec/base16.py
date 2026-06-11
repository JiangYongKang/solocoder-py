from __future__ import annotations

from .base import _BaseDecoder, _BaseEncoder


class Base16Encoder(_BaseEncoder):
    _ALPHABET = "0123456789ABCDEF"
    _BITS_PER_CHAR = 4

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


class Base16Decoder(_BaseDecoder):
    _ALPHABET = "0123456789ABCDEF"
    _BITS_PER_CHAR = 4

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


def b16encode(data: bytes, pad: bool = True, line_width: int = 0, newline: str = "\n") -> str:
    encoder = Base16Encoder(pad=pad, line_width=line_width, newline=newline)
    return encoder.encode(data)


def b16decode(data: str, pad: bool = True) -> bytes:
    decoder = Base16Decoder(pad=pad)
    return decoder.decode(data)
