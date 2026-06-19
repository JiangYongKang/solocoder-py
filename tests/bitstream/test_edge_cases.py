from __future__ import annotations

import pytest

from solocoder_py.bitstream import BitReader, BitWriter, InsufficientBitsError


class TestZeroBitsOperations:
    def test_write_zero_bits_noop(self):
        writer = BitWriter()
        writer.write_bits(0, 0)
        assert writer.total_bits_written == 0
        assert writer.to_bytes() == b""

    def test_write_zero_bits_with_existing_data(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(42, 0)
        assert writer.total_bits_written == 3

    def test_read_zero_bits_noop(self):
        writer = BitWriter()
        writer.write_bits(0b10101010, 8)
        reader = BitReader(writer.to_bytes())
        result = reader.read_bits(0)
        assert result == 0
        assert reader.total_bits_read == 0
        assert reader.remaining_bits == 8

    def test_peek_zero_bits_noop(self):
        writer = BitWriter()
        writer.write_bits(0b11110000, 8)
        reader = BitReader(writer.to_bytes())
        result = reader.peek_bits(0)
        assert result == 0
        assert reader.total_bits_read == 0


class TestFull64BitsOperations:
    def test_write_64_bits_all_ones(self):
        writer = BitWriter()
        writer.write_bits(0xFFFFFFFFFFFFFFFF, 64)
        data = writer.to_bytes()
        assert data == b"\xff\xff\xff\xff\xff\xff\xff\xff"
        assert writer.total_bits_written == 64
        assert writer.total_bytes_written == 8

    def test_write_64_bits_all_zeros(self):
        writer = BitWriter()
        writer.write_bits(0, 64)
        data = writer.to_bytes()
        assert data == b"\x00\x00\x00\x00\x00\x00\x00\x00"

    def test_write_64_bits_high_low(self):
        value = 0xA5A5A5A55A5A5A5A
        writer = BitWriter()
        writer.write_bits(value, 64)
        data = writer.to_bytes()
        expected = bytes([
            0xA5, 0xA5, 0xA5, 0xA5,
            0x5A, 0x5A, 0x5A, 0x5A,
        ])
        assert data == expected

    def test_read_64_bits_all_ones(self):
        data = b"\xff\xff\xff\xff\xff\xff\xff\xff"
        reader = BitReader(data)
        result = reader.read_bits(64)
        assert result == 0xFFFFFFFFFFFFFFFF
        assert reader.remaining_bits == 0
        assert reader.is_aligned

    def test_read_64_bits_high_low(self):
        data = bytes([
            0xA5, 0xA5, 0xA5, 0xA5,
            0x5A, 0x5A, 0x5A, 0x5A,
        ])
        reader = BitReader(data)
        assert reader.read_bits(64) == 0xA5A5A5A55A5A5A5A

    def test_roundtrip_64_bits(self):
        values = [
            0,
            1,
            0x7FFFFFFFFFFFFFFF,
            0x8000000000000000,
            0xDEADBEEFCAFEBABE,
            0xFFFFFFFFFFFFFFFF,
        ]
        for val in values:
            writer = BitWriter()
            writer.write_bits(val, 64)
            reader = BitReader(writer.to_bytes())
            assert reader.read_bits(64) == val, f"Failed for value {val:#x}"


class TestBufferBoundaryOperations:
    def test_write_exact_one_byte(self):
        writer = BitWriter()
        writer.write_bits(0xA5, 8)
        data = writer.to_bytes()
        assert data == bytes([0xA5])
        assert writer.total_bytes_written == 1

    def test_write_exact_three_bytes(self):
        writer = BitWriter()
        writer.write_bits(0xA5, 8)
        writer.write_bits(0x3C, 8)
        writer.write_bits(0x7E, 8)
        data = writer.to_bytes()
        assert data == bytes([0xA5, 0x3C, 0x7E])
        assert writer.total_bits_written == 24

    def test_last_bit_operation_exact(self):
        writer = BitWriter(capacity_bits=5)
        writer.write_bits(0b101, 3)
        writer.write_bits(0b11, 2)
        assert writer.total_bits_written == 5
        assert writer.remaining_capacity_bits == 0

    def test_read_last_bit_of_stream(self):
        data = bytes([0b10101010])
        reader = BitReader(data)
        reader.read_bits(7)
        assert reader.remaining_bits == 1
        last_bit = reader.read_bits(1)
        assert last_bit == 0
        assert reader.remaining_bits == 0

    def test_write_last_bit_then_read(self):
        writer = BitWriter()
        writer.write_bits(0b1111111, 7)
        writer.write_bits(0b1, 1)
        data = writer.to_bytes()
        assert data == bytes([0xFF])
        reader = BitReader(data)
        reader.read_bits(7)
        assert reader.read_bits(1) == 1

    def test_read_all_bits_exact(self):
        writer = BitWriter()
        for _ in range(4):
            writer.write_bits(0b1011, 4)
        data = writer.to_bytes()
        reader = BitReader(data)
        results = [reader.read_bits(4) for _ in range(4)]
        assert results == [0b1011, 0b1011, 0b1011, 0b1011]
        assert reader.remaining_bits == 0


class TestEmptyStreamOperations:
    def test_empty_stream_remaining_bits(self):
        reader = BitReader(b"")
        assert reader.total_bits_available == 0
        assert reader.remaining_bits == 0
        assert reader.total_bits_read == 0

    def test_empty_writer_to_bytes(self):
        writer = BitWriter()
        assert writer.to_bytes() == b""
        assert writer.total_bits_written == 0

    def test_empty_writer_reset(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.reset()
        assert writer.to_bytes() == b""
        assert writer.total_bits_written == 0

    def test_empty_reader_reset(self):
        reader = BitReader(bytes([0xA5]))
        reader.read_bits(8)
        reader.reset()
        assert reader.total_bits_read == 0
        assert reader.remaining_bits == 8

    def test_write_then_reset(self):
        writer = BitWriter()
        writer.write_bits(0xDEADBEEF, 32)
        writer.reset()
        writer.write_bits(0xCAFE, 16)
        data = writer.to_bytes()
        reader = BitReader(data)
        assert reader.read_bits(16) == 0xCAFE


class TestAlignOperations:
    def test_align_writer_from_bit_3(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        padding = writer.align_to_byte()
        assert padding == 5
        data = writer.to_bytes()
        assert data == bytes([0b10100000])
        assert writer.total_bits_written == 8

    def test_align_writer_from_bit_5_with_ones(self):
        writer = BitWriter()
        writer.write_bits(0b10110, 5)
        padding = writer.align_to_byte(fill_bit=1)
        assert padding == 3
        data = writer.to_bytes()
        assert data == bytes([0b10110111])

    def test_align_writer_already_aligned(self):
        writer = BitWriter()
        writer.write_bits(0xA5, 8)
        padding = writer.align_to_byte()
        assert padding == 0
        assert writer.total_bits_written == 8

    def test_align_reader_from_bit_3(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.align_to_byte()
        writer.write_bits(0b11001010, 8)
        writer.write_bits(0b10100011, 8)
        data = writer.to_bytes()
        reader = BitReader(data)
        assert reader.read_bits(3) == 0b101
        skip = reader.align_to_byte()
        assert skip == 5
        assert reader.is_aligned
        assert reader.read_bits(8) == 0b11001010
        assert reader.read_bits(8) == 0b10100011

    def test_align_reader_already_aligned(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        reader.read_bits(8)
        skip = reader.align_to_byte()
        assert skip == 0
        assert reader.is_aligned


class TestBitReaderTotalBitsParameter:
    def test_total_bits_default_equals_data_bytes(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        assert reader.total_bits_available == 16

    def test_total_bits_explicitly_set(self):
        reader = BitReader(bytes([0xA5, 0x3C, 0x7E, 0x00]), total_bits=24)
        assert reader.total_bits_available == 24
        assert reader.remaining_bits == 24

    def test_total_bits_non_aligned_length(self):
        reader = BitReader(bytes([0b10110000]), total_bits=4)
        assert reader.total_bits_available == 4
        assert reader.read_bits(4) == 0b1011
        assert reader.remaining_bits == 0

    def test_total_bits_align_success(self):
        data = bytes([0b10111000, 0b11001010])
        reader = BitReader(data, total_bits=11)
        reader.read_bits(3)
        assert reader.remaining_bits == 8
        skip = reader.align_to_byte()
        assert skip == 5
        assert reader.remaining_bits == 3
        assert reader.read_bits(3) == 0b110

    def test_total_bits_roundtrip_with_writer(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        writer.write_bits(0b1100101, 7)
        expected_bits = writer.total_bits_written
        data = writer.to_bytes()
        reader = BitReader(data, total_bits=expected_bits)
        assert reader.read_bits(3) == 0b101
        assert reader.read_bits(7) == 0b1100101
        assert reader.remaining_bits == 0

    def test_total_bits_zero(self):
        reader = BitReader(bytes([0x00]), total_bits=0)
        assert reader.total_bits_available == 0
        assert reader.remaining_bits == 0
        with pytest.raises(InsufficientBitsError):
            reader.read_bits(1)

    def test_total_bits_read_remaining_respects_limit(self):
        reader = BitReader(bytes([0xA5, 0x3C, 0x7E]), total_bits=16)
        result = reader.read_remaining()
        assert result == bytes([0xA5, 0x3C])
        assert reader.remaining_bits == 0
