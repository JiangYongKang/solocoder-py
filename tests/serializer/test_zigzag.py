import pytest

from solocoder_py.serializer import ZigZagOverflowError, decode_zigzag, encode_zigzag


class TestZigZagNormal:
    def test_zero(self):
        assert encode_zigzag(0, 64) == 0
        assert decode_zigzag(0, 64) == 0

    def test_positive_one(self):
        assert encode_zigzag(1, 64) == 2
        assert decode_zigzag(2, 64) == 1

    def test_negative_one(self):
        assert encode_zigzag(-1, 64) == 1
        assert decode_zigzag(1, 64) == -1

    def test_positive_two(self):
        assert encode_zigzag(2, 64) == 4
        assert decode_zigzag(4, 64) == 2

    def test_negative_two(self):
        assert encode_zigzag(-2, 64) == 3
        assert decode_zigzag(3, 64) == -2

    def test_interleaved_order(self):
        assert encode_zigzag(0, 64) == 0
        assert encode_zigzag(-1, 64) == 1
        assert encode_zigzag(1, 64) == 2
        assert encode_zigzag(-2, 64) == 3
        assert encode_zigzag(2, 64) == 4
        assert encode_zigzag(-3, 64) == 5
        assert encode_zigzag(3, 64) == 6

    def test_roundtrip_small_range(self):
        for val in range(-100, 101):
            encoded = encode_zigzag(val, 64)
            decoded = decode_zigzag(encoded, 64)
            assert decoded == val

    def test_roundtrip_large_positive(self):
        for val in [2**10, 2**20, 2**30, 2**40, 2**50, 2**60, 2**62]:
            encoded = encode_zigzag(val, 64)
            decoded = decode_zigzag(encoded, 64)
            assert decoded == val

    def test_roundtrip_large_negative(self):
        for val in [-(2**10), -(2**20), -(2**30), -(2**40), -(2**50), -(2**60), -(2**62)]:
            encoded = encode_zigzag(val, 64)
            decoded = decode_zigzag(encoded, 64)
            assert decoded == val


class TestZigZagBits:
    def test_int8_range(self):
        int8_min = -128
        int8_max = 127
        assert encode_zigzag(int8_min, 8) == 255
        assert decode_zigzag(255, 8) == int8_min
        assert encode_zigzag(int8_max, 8) == 254
        assert decode_zigzag(254, 8) == int8_max

    def test_int16_range(self):
        int16_min = -(2**15)
        int16_max = 2**15 - 1
        encoded = encode_zigzag(int16_min, 16)
        assert decode_zigzag(encoded, 16) == int16_min
        encoded = encode_zigzag(int16_max, 16)
        assert decode_zigzag(encoded, 16) == int16_max

    def test_int32_range(self):
        int32_min = -(2**31)
        int32_max = 2**31 - 1
        encoded = encode_zigzag(int32_min, 32)
        assert decode_zigzag(encoded, 32) == int32_min
        encoded = encode_zigzag(int32_max, 32)
        assert decode_zigzag(encoded, 32) == int32_max

    def test_int64_range(self):
        int64_min = -(2**63)
        int64_max = 2**63 - 1
        encoded = encode_zigzag(int64_min, 64)
        assert decode_zigzag(encoded, 64) == int64_min
        encoded = encode_zigzag(int64_max, 64)
        assert decode_zigzag(encoded, 64) == int64_max

    def test_invalid_bits_raises(self):
        with pytest.raises(ValueError, match="unsupported bit width"):
            encode_zigzag(0, 10)
        with pytest.raises(ValueError, match="unsupported bit width"):
            decode_zigzag(0, 10)


class TestZigZagOverflow:
    def test_encode_int32_too_large_positive(self):
        with pytest.raises(ZigZagOverflowError):
            encode_zigzag(2**31, 32)

    def test_encode_int32_too_large_negative(self):
        with pytest.raises(ZigZagOverflowError):
            encode_zigzag(-(2**31) - 1, 32)

    def test_encode_int8_too_large(self):
        with pytest.raises(ZigZagOverflowError):
            encode_zigzag(128, 8)
        with pytest.raises(ZigZagOverflowError):
            encode_zigzag(-129, 8)

    def test_decode_uint32_too_large(self):
        with pytest.raises(ZigZagOverflowError):
            decode_zigzag(2**32, 32)

    def test_decode_negative_unsigned(self):
        with pytest.raises(ZigZagOverflowError):
            decode_zigzag(-1, 32)


class TestZigZagEncodingEfficiency:
    def test_small_abs_values_encode_small(self):
        for val in [0, -1, 1, -2, 2, -50, 50, -100, 100]:
            encoded = encode_zigzag(val, 64)
            assert encoded < 256

    def test_negative_one_vs_large_positive(self):
        encoded_neg1 = encode_zigzag(-1, 64)
        encoded_big = encode_zigzag(1000000, 64)
        assert encoded_neg1 < encoded_big
