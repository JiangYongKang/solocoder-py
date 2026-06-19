import pytest

from solocoder_py.tsdelta import (
    MAX_SIGNED_60BIT,
    MIN_SIGNED_60BIT,
    ZigZagOverflowError,
    zigzag_decode,
    zigzag_decode_list,
    zigzag_encode,
    zigzag_encode_list,
)


class TestZigZagEncode:
    def test_zero(self):
        assert zigzag_encode(0) == 0

    def test_positive_one(self):
        assert zigzag_encode(1) == 2

    def test_negative_one(self):
        assert zigzag_encode(-1) == 1

    def test_positive_two(self):
        assert zigzag_encode(2) == 4

    def test_negative_two(self):
        assert zigzag_encode(-2) == 3

    def test_positive_three(self):
        assert zigzag_encode(3) == 6

    def test_negative_three(self):
        assert zigzag_encode(-3) == 5

    def test_small_positive_values(self):
        for i in range(1, 20):
            assert zigzag_encode(i) == i * 2

    def test_small_negative_values(self):
        for i in range(1, 20):
            assert zigzag_encode(-i) == i * 2 - 1

    def test_max_signed_60bit(self):
        encoded = zigzag_encode(MAX_SIGNED_60BIT)
        assert encoded == (MAX_SIGNED_60BIT << 1)

    def test_min_signed_60bit(self):
        encoded = zigzag_encode(MIN_SIGNED_60BIT)
        assert encoded == ((-MIN_SIGNED_60BIT) << 1) - 1

    def test_exceeds_max_signed(self):
        with pytest.raises(ZigZagOverflowError, match="out of range"):
            zigzag_encode(MAX_SIGNED_60BIT + 1)

    def test_below_min_signed(self):
        with pytest.raises(ZigZagOverflowError, match="out of range"):
            zigzag_encode(MIN_SIGNED_60BIT - 1)

    def test_custom_bit_width_small(self):
        assert zigzag_encode(1, max_bits=8) == 2
        assert zigzag_encode(-1, max_bits=8) == 1
        assert zigzag_encode(127, max_bits=8) == 254
        assert zigzag_encode(-128, max_bits=8) == 255

    def test_custom_bit_width_overflow(self):
        with pytest.raises(ZigZagOverflowError):
            zigzag_encode(128, max_bits=8)
        with pytest.raises(ZigZagOverflowError):
            zigzag_encode(-129, max_bits=8)


class TestZigZagDecode:
    def test_zero(self):
        assert zigzag_decode(0) == 0

    def test_negative_one(self):
        assert zigzag_decode(1) == -1

    def test_positive_one(self):
        assert zigzag_decode(2) == 1

    def test_negative_two(self):
        assert zigzag_decode(3) == -2

    def test_positive_two(self):
        assert zigzag_decode(4) == 2

    def test_small_values(self):
        test_cases = [
            (0, 0),
            (1, -1),
            (2, 1),
            (3, -2),
            (4, 2),
            (5, -3),
            (6, 3),
        ]
        for encoded, expected in test_cases:
            assert zigzag_decode(encoded) == expected

    def test_max_unsigned_60bit(self):
        max_unsigned = (1 << 60) - 1
        decoded = zigzag_decode(max_unsigned)
        assert decoded == MIN_SIGNED_60BIT

    def test_negative_input_rejected(self):
        with pytest.raises(ZigZagOverflowError, match="out of range"):
            zigzag_decode(-1)

    def test_exceeds_max_unsigned(self):
        with pytest.raises(ZigZagOverflowError, match="out of range"):
            zigzag_decode(1 << 60)

    def test_custom_bit_width(self):
        assert zigzag_decode(254, max_bits=8) == 127
        assert zigzag_decode(255, max_bits=8) == -128


class TestZigZagRoundtrip:
    def test_roundtrip_small_values(self):
        for value in range(-100, 100):
            encoded = zigzag_encode(value)
            decoded = zigzag_decode(encoded)
            assert decoded == value, f"Failed for value {value}"

    def test_roundtrip_large_values(self):
        test_values = [
            MAX_SIGNED_60BIT,
            MIN_SIGNED_60BIT,
            MAX_SIGNED_60BIT - 1,
            MIN_SIGNED_60BIT + 1,
            1 << 30,
            -(1 << 30),
            1 << 40,
            -(1 << 40),
        ]
        for value in test_values:
            encoded = zigzag_encode(value)
            decoded = zigzag_decode(encoded)
            assert decoded == value, f"Failed for value {value}"

    def test_roundtrip_custom_bit_width(self):
        for max_bits in [8, 16, 32, 60]:
            max_signed = (1 << (max_bits - 1)) - 1
            min_signed = -(1 << (max_bits - 1))

            for value in [min_signed, -100, -1, 0, 1, 100, max_signed]:
                encoded = zigzag_encode(value, max_bits=max_bits)
                decoded = zigzag_decode(encoded, max_bits=max_bits)
                assert decoded == value, f"Failed for value {value} with {max_bits} bits"


class TestZigZagList:
    def test_encode_empty_list(self):
        assert zigzag_encode_list([]) == []

    def test_decode_empty_list(self):
        assert zigzag_decode_list([]) == []

    def test_encode_list(self):
        values = [0, 1, -1, 2, -2, 3, -3]
        expected = [0, 2, 1, 4, 3, 6, 5]
        assert zigzag_encode_list(values) == expected

    def test_decode_list(self):
        encoded = [0, 2, 1, 4, 3, 6, 5]
        expected = [0, 1, -1, 2, -2, 3, -3]
        assert zigzag_decode_list(encoded) == expected

    def test_list_roundtrip(self):
        values = list(range(-50, 50))
        encoded = zigzag_encode_list(values)
        decoded = zigzag_decode_list(encoded)
        assert decoded == values

    def test_typical_second_order_deltas(self):
        deltas = [0, 0, 0, 1, -1, 2, -2, 0, 0, 0]
        encoded = zigzag_encode_list(deltas)
        assert max(encoded) <= 5
        decoded = zigzag_decode_list(encoded)
        assert decoded == deltas
