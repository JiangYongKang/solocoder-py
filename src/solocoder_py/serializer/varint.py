from __future__ import annotations

from .buffer import Buffer
from .exceptions import VarintDecodeError

MAX_VARINT_BYTES = 10


def encode_uvarint(value: int) -> bytes:
    if value < 0:
        raise ValueError("uvarint value must be non-negative")
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def decode_uvarint(buf: Buffer) -> int:
    result = 0
    shift = 0
    bytes_read = 0
    while True:
        if bytes_read >= MAX_VARINT_BYTES:
            raise VarintDecodeError("varint too long, exceeds 10 bytes")
        try:
            b = buf.read_byte()
        except Exception as e:
            raise VarintDecodeError(f"truncated varint: {e}") from e
        bytes_read += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result


def write_uvarint(buf: Buffer, value: int) -> None:
    buf.write_bytes(encode_uvarint(value))


def encode_varint(value: int, bits: int = 64) -> bytes:
    from .zigzag import encode_zigzag

    unsigned = encode_zigzag(value, bits)
    return encode_uvarint(unsigned)


def decode_varint(buf: Buffer, bits: int = 64) -> int:
    from .zigzag import decode_zigzag

    unsigned = decode_uvarint(buf)
    return decode_zigzag(unsigned, bits)


def write_varint(buf: Buffer, value: int, bits: int = 64) -> None:
    buf.write_bytes(encode_varint(value, bits))
