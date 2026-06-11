import pytest

from solocoder_py.serializer import (
    Buffer,
    VarintDecodeError,
    decode_uvarint,
    decode_varint,
    encode_uvarint,
    encode_varint,
    write_uvarint,
    write_varint,
)
from .conftest import make_buffer


class TestUnsignedVarintNormal:
    def test_zero(self):
        encoded = encode_uvarint(0)
        assert encoded == b"\x00"
        buf = make_buffer(encoded)
        assert decode_uvarint(buf) == 0

    def test_single_byte_values(self):
        for val in range(0, 128):
            encoded = encode_uvarint(val)
            assert len(encoded) == 1
            buf = make_buffer(encoded)
            assert decode_uvarint(buf) == val

    def test_two_byte_boundary(self):
        val = 127
        encoded = encode_uvarint(val)
        assert len(encoded) == 1
        buf = make_buffer(encoded)
        assert decode_uvarint(buf) == 127

        val = 128
        encoded = encode_uvarint(val)
        assert len(encoded) == 2
        buf = make_buffer(encoded)
        assert decode_uvarint(buf) == 128

    def test_two_byte_values(self):
        for val in [128, 255, 256, 1000, 16383]:
            encoded = encode_uvarint(val)
            assert len(encoded) == 2
            buf = make_buffer(encoded)
            assert decode_uvarint(buf) == val

    def test_three_byte_boundary(self):
        val = 16383
        encoded = encode_uvarint(val)
        assert len(encoded) == 2
        buf = make_buffer(encoded)
        assert decode_uvarint(buf) == 16383

        val = 16384
        encoded = encode_uvarint(val)
        assert len(encoded) == 3
        buf = make_buffer(encoded)
        assert decode_uvarint(buf) == 16384

    def test_large_values(self):
        test_vals = [
            2 ** 21 - 1,
            2 ** 21,
            2 ** 28 - 1,
            2 ** 28,
            2 ** 32 - 1,
            2 ** 40,
            2 ** 56,
            2 ** 64 - 1,
        ]
        for val in test_vals:
            encoded = encode_uvarint(val)
            buf = make_buffer(encoded)
            assert decode_uvarint(buf) == val

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            encode_uvarint(-1)


class TestUnsignedVarintBoundary:
    def test_max_single_byte(self):
        assert encode_uvarint(127) == b"\x7f"

    def test_min_two_byte(self):
        assert encode_uvarint(128) == b"\x80\x01"

    def test_max_two_byte(self):
        assert encode_uvarint(16383) == b"\xff\x7f"

    def test_min_three_byte(self):
        assert encode_uvarint(16384) == b"\x80\x80\x01"


class TestUnsignedVarintErrors:
    def test_truncated_single_byte(self):
        buf = make_buffer(b"\x80")
        with pytest.raises(VarintDecodeError, match="truncated"):
            decode_uvarint(buf)

    def test_truncated_multi_byte(self):
        buf = make_buffer(b"\x80\x80\x80")
        with pytest.raises(VarintDecodeError, match="truncated"):
            decode_uvarint(buf)

    def test_too_many_bytes(self):
        data = b"\x80" * 10 + b"\x01"
        buf = make_buffer(data)
        with pytest.raises(VarintDecodeError, match="too long"):
            decode_uvarint(buf)


class TestUnsignedVarintBufferIO:
    def test_write_then_read(self):
        buf = make_buffer()
        values = [0, 1, 127, 128, 16383, 16384, 1000000, 2**32 - 1]
        for v in values:
            write_uvarint(buf, v)
        buf.reset_read()
        for v in values:
            assert decode_uvarint(buf) == v

    def test_encoding_efficiency_small_values(self):
        assert len(encode_uvarint(0)) == 1
        assert len(encode_uvarint(1)) == 1
        assert len(encode_uvarint(100)) == 1
        assert len(encode_uvarint(127)) == 1
        assert len(encode_uvarint(128)) == 2


class TestSignedVarintNormal:
    def test_zero(self):
        encoded = encode_varint(0, 64)
        buf = make_buffer(encoded)
        assert decode_varint(buf, 64) == 0

    def test_positive_small(self):
        for val in [1, 2, 10, 50, 100]:
            encoded = encode_varint(val, 64)
            buf = make_buffer(encoded)
            assert decode_varint(buf, 64) == val

    def test_negative_small(self):
        for val in [-1, -2, -10, -50, -100]:
            encoded = encode_varint(val, 64)
            buf = make_buffer(encoded)
            assert decode_varint(buf, 64) == val

    def test_positive_large(self):
        for val in [2**30, 2**31 - 1, 2**60, 2**62]:
            encoded = encode_varint(val, 64)
            buf = make_buffer(encoded)
            assert decode_varint(buf, 64) == val

    def test_negative_large(self):
        for val in [-(2**30), -(2**31), -(2**60), -(2**62)]:
            encoded = encode_varint(val, 64)
            buf = make_buffer(encoded)
            assert decode_varint(buf, 64) == val

    def test_int32_range(self):
        int32_min = -(2**31)
        int32_max = 2**31 - 1
        for val in [int32_min, int32_min + 1, -1, 0, 1, int32_max - 1, int32_max]:
            encoded = encode_varint(val, 32)
            buf = make_buffer(encoded)
            assert decode_varint(buf, 32) == val

    def test_small_negative_uses_few_bytes(self):
        encoded_minus_one = encode_varint(-1, 64)
        encoded_one = encode_varint(1, 64)
        encoded_big = encode_varint(1000000, 64)
        assert len(encoded_minus_one) == len(encoded_one)
        assert len(encoded_minus_one) < len(encoded_big)
