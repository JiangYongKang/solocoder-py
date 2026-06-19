from __future__ import annotations

import pytest

from solocoder_py.bitstream import BitReader, BitWriter


class TestSingleByteUnalignedWriteRead:
    def test_write_3_bits_in_single_byte(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        data = writer.to_bytes()
        assert data == bytes([0b10100000])
        assert writer.total_bits_written == 3

    def test_write_5_bits_in_single_byte(self):
        writer = BitWriter()
        writer.write_bits(0b11001, 5)
        data = writer.to_bytes()
        assert data == bytes([0b11001000])
        assert writer.total_bits_written == 5

    def test_read_3_bits_from_single_byte(self):
        reader = BitReader(bytes([0b10100000]))
        result = reader.read_bits(3)
        assert result == 0b101
        assert reader.total_bits_read == 3
        assert reader.remaining_bits == 5

    def test_write_and_read_7_bits_within_byte(self):
        writer = BitWriter()
        writer.write_bits(0b1010110, 7)
        data = writer.to_bytes()
        reader = BitReader(data)
        assert reader.read_bits(7) == 0b1010110
        assert reader.bit_offset == 7
        assert reader.byte_position == 0

    def test_multiple_small_writes_in_one_byte(self):
        writer = BitWriter()
        writer.write_bits(0b1, 1)
        writer.write_bits(0b01, 2)
        writer.write_bits(0b110, 3)
        writer.write_bits(0b01, 2)
        data = writer.to_bytes()
        assert data == bytes([0b10111001])
        reader = BitReader(data)
        assert reader.read_bits(1) == 0b1
        assert reader.read_bits(2) == 0b01
        assert reader.read_bits(3) == 0b110
        assert reader.read_bits(2) == 0b01


class TestCrossByteBoundary:
    def test_write_10_bits_crosses_boundary(self):
        writer = BitWriter()
        writer.write_bits(0b1011010011, 10)
        data = writer.to_bytes()
        assert data == bytes([0b10110100, 0b11000000])
        assert writer.total_bits_written == 10
        assert writer.total_bytes_written == 2

    def test_read_10_bits_crosses_boundary(self):
        data = bytes([0b10110100, 0b11000000])
        reader = BitReader(data)
        result = reader.read_bits(10)
        assert result == 0b1011010011
        assert reader.bit_offset == 2
        assert reader.byte_position == 1

    def test_write_3_then_6_crosses_boundary(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(0b110010, 6)
        data = writer.to_bytes()
        assert data == bytes([0b10111001, 0b00000000])
        reader = BitReader(data)
        assert reader.read_bits(3) == 0b101
        assert reader.read_bits(6) == 0b110010

    def test_write_13_bits(self):
        writer = BitWriter()
        writer.write_bits(0b1011010111001, 13)
        data = writer.to_bytes()
        assert len(data) == 2
        reader = BitReader(data)
        result = reader.read_bits(13)
        assert result == 0b1011010111001

    def test_multiple_cross_byte_writes(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(0b110011, 6)
        writer.write_bits(0b101010, 6)
        writer.write_bits(0b111, 3)
        data = writer.to_bytes()
        reader = BitReader(data)
        assert reader.read_bits(3) == 0b101
        assert reader.read_bits(6) == 0b110011
        assert reader.read_bits(6) == 0b101010
        assert reader.read_bits(3) == 0b111


class TestVariableLengthIntegerEncoding:
    def test_encode_decode_1_bit(self):
        for val in [0, 1]:
            writer = BitWriter()
            writer.write_bits(val, 1)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(1) == val

    def test_encode_decode_8_bits(self):
        values = [0, 1, 127, 128, 255]
        for val in values:
            writer = BitWriter()
            writer.write_bits(val, 8)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(8) == val

    def test_encode_decode_16_bits(self):
        values = [0, 1, 0x7FFF, 0x8000, 0xFFFF]
        for val in values:
            writer = BitWriter()
            writer.write_bits(val, 16)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(16) == val

    def test_encode_decode_32_bits(self):
        values = [0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]
        for val in values:
            writer = BitWriter()
            writer.write_bits(val, 32)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(32) == val

    def test_encode_decode_64_bits(self):
        values = [0, 1, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000, 0xFFFFFFFFFFFFFFFF]
        for val in values:
            writer = BitWriter()
            writer.write_bits(val, 64)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(64) == val

    def test_big_endian_bit_order_10_bits(self):
        writer = BitWriter()
        writer.write_bits(0b1101011010, 10)
        data = writer.to_bytes()
        assert data[0] == 0b11010110
        assert (data[1] >> 6) == 0b10
        reader = BitReader(data)
        assert reader.read_bits(10) == 0b1101011010

    def test_high_low_bits_correctness_24_bits(self):
        value = 0xA53C7E
        writer = BitWriter()
        writer.write_bits(value, 24)
        data = writer.to_bytes()
        assert data[0] == 0xA5
        assert data[1] == 0x3C
        assert data[2] == 0x7E
        reader = BitReader(data)
        assert reader.read_bits(24) == value


class TestPeekProbe:
    def test_peek_does_not_advance_position(self):
        writer = BitWriter()
        writer.write_bits(0b10110100, 8)
        writer.write_bits(0b11001101, 8)
        data = writer.to_bytes()
        reader = BitReader(data)

        initial_pos = reader.byte_position
        initial_offset = reader.bit_offset
        initial_read = reader.total_bits_read

        peeked = reader.peek_bits(5)

        assert reader.byte_position == initial_pos
        assert reader.bit_offset == initial_offset
        assert reader.total_bits_read == initial_read
        assert peeked == 0b10110

    def test_peek_then_read_same_value(self):
        writer = BitWriter()
        writer.write_bits(0b101100111010, 12)
        data = writer.to_bytes()
        reader = BitReader(data)

        peeked = reader.peek_bits(7)
        actual = reader.read_bits(7)

        assert peeked == actual
        assert peeked == 0b1011001
        assert reader.total_bits_read == 7

    def test_peek_multiple_times(self):
        writer = BitWriter()
        writer.write_bits(0xA5, 8)
        data = writer.to_bytes()
        reader = BitReader(data)

        assert reader.peek_bits(3) == 0b101
        assert reader.peek_bits(3) == 0b101
        assert reader.peek_bits(5) == 0b10100
        assert reader.read_bits(3) == 0b101

    def test_peek_cross_byte_boundary(self):
        writer = BitWriter()
        writer.write_bits(0b110, 3)
        writer.write_bits(0b10111001101, 11)
        data = writer.to_bytes()
        reader = BitReader(data)

        reader.read_bits(3)
        peeked = reader.peek_bits(11)
        assert peeked == 0b10111001101
        assert reader.total_bits_read == 3

    def test_peek_then_read_following_data(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(0b11001, 5)
        writer.write_bits(0b1010, 4)
        data = writer.to_bytes()
        reader = BitReader(data)

        reader.read_bits(3)
        assert reader.peek_bits(5) == 0b11001
        assert reader.read_bits(5) == 0b11001
        assert reader.read_bits(4) == 0b1010


class TestBitOffsetRecovery:
    def test_consecutive_unaligned_operations_3_5(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(0b11001, 5)
        assert writer.total_bits_written == 8
        data = writer.to_bytes()
        assert len(data) == 1
        reader = BitReader(data)
        assert reader.read_bits(3) == 0b101
        assert reader.read_bits(5) == 0b11001
        assert reader.bit_offset == 0
        assert reader.byte_position == 1

    def test_consecutive_unaligned_operations_1_2_3(self):
        writer = BitWriter()
        writer.write_bits(0b1, 1)
        writer.write_bits(0b01, 2)
        writer.write_bits(0b110, 3)
        assert writer.total_bits_written == 6
        data = writer.to_bytes()
        reader = BitReader(data)
        assert reader.read_bits(1) == 0b1
        assert reader.read_bits(2) == 0b01
        assert reader.read_bits(3) == 0b110
        assert reader.bit_offset == 6

    def test_complex_sequence(self):
        writer = BitWriter()
        values = [
            (0b1, 1),
            (0b01, 2),
            (0b101, 3),
            (0b1010, 4),
            (0b11001, 5),
            (0b101010, 6),
        ]
        for val, n in values:
            writer.write_bits(val, n)

        total_bits = sum(n for _, n in values)
        assert writer.total_bits_written == total_bits

        data = writer.to_bytes()
        reader = BitReader(data)
        for val, n in values:
            assert reader.read_bits(n) == val, f"Failed for value {val:#b} with {n} bits"
        assert reader.total_bits_read == total_bits

    def test_bit_offset_correct_after_17_bits(self):
        writer = BitWriter()
        writer.write_bits(0b10101010101010101, 17)
        data = writer.to_bytes()
        reader = BitReader(data)
        result = reader.read_bits(17)
        assert result == 0b10101010101010101
        assert reader.bit_offset == 1
        assert reader.byte_position == 2

    def test_roundtrip_various_bit_lengths(self):
        test_cases = [
            (n, (1 << n) - 1 if n < 64 else 0xFFFFFFFFFFFFFFFF)
            for n in range(1, 65)
        ]
        for n, max_val in test_cases:
            writer = BitWriter()
            for val in [0, 1, max_val]:
                writer.reset()
                writer.write_bits(val, n)
                reader = BitReader(writer.to_bytes())
                assert reader.read_bits(n) == val, (
                    f"Failed for {n} bits, value {val}"
                )
