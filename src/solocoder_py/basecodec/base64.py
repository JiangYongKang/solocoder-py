from __future__ import annotations

from .base import _BaseDecoder, _BaseEncoder


class Base64Encoder(_BaseEncoder):
    _ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    _BITS_PER_CHAR = 6

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


class Base64Decoder(_BaseDecoder):
    _ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    _BITS_PER_CHAR = 6

    @property
    def _bits_per_char(self) -> int:
        return self._BITS_PER_CHAR

    @property
    def _alphabet(self) -> str:
        return self._ALPHABET


def b64encode(data: bytes, pad: bool = True, line_width: int = 0, newline: str = "\n") -> str:
    encoder = Base64Encoder(pad=pad, line_width=line_width, newline=newline)
    return encoder.encode(data)


def b64decode(data: str, pad: bool = True) -> bytes:
    decoder = Base64Decoder(pad=pad)
    return decoder.decode(data)
