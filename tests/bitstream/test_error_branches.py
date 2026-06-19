from __future__ import annotations

import pytest

from solocoder_py.bitstream import (
    BitCapacityExceededError,
    BitReader,
    BitWriter,
    InsufficientBitsError,
    InvalidBitCountError,
    ValueOutOfRangeError,
)


class TestBitCountValidation:
    def test_write_negative_bits_raises(self):
        writer = BitWriter()
        with pytest.raises(InvalidBitCountError) as excinfo:
            writer.write_bits(1, -1)
        assert "between 1 and 64" in str(excinfo.value)

    def test_write_65_bits_raises(self):
        writer = BitWriter()
        with pytest.raises(InvalidBitCountError) as excinfo:
            writer.write_bits(1, 65)
        assert "between 1 and 64" in str(excinfo.value)

    def test_read_negative_bits_raises(self):
        reader = BitReader(bytes([0xFF]))
        with pytest.raises(InvalidBitCountError) as excinfo:
            reader.read_bits(-5)
        assert "between 1 and 64" in str(excinfo.value)

    def test_read_65_bits_raises(self):
        reader = BitReader(bytes([0xFF] * 9))
        with pytest.raises(InvalidBitCountError) as excinfo:
            reader.read_bits(65)
        assert "between 1 and 64" in str(excinfo.value)

    def test_peek_negative_bits_raises(self):
        reader = BitReader(bytes([0xFF]))
        with pytest.raises(InvalidBitCountError) as excinfo:
            reader.peek_bits(-3)
        assert "between 1 and 64" in str(excinfo.value)

    def test_peek_65_bits_raises(self):
        reader = BitReader(bytes([0xFF] * 9))
        with pytest.raises(InvalidBitCountError) as excinfo:
            reader.peek_bits(65)
        assert "between 1 and 64" in str(excinfo.value)


class TestWriterCapacityExceeded:
    def test_write_exceeds_capacity_single_op(self):
        writer = BitWriter(capacity_bits=5)
        with pytest.raises(BitCapacityExceededError) as excinfo:
            writer.write_bits(0b111111, 6)
        assert "exceeded" in str(excinfo.value)

    def test_write_exceeds_capacity_cumulative(self):
        writer = BitWriter(capacity_bits=10)
        writer.write_bits(0b10101, 5)
        writer.write_bits(0b1010, 4)
        assert writer.remaining_capacity_bits == 1
        with pytest.raises(BitCapacityExceededError):
            writer.write_bits(0b11, 2)

    def test_write_at_exact_capacity_ok(self):
        writer = BitWriter(capacity_bits=8)
        writer.write_bits(0xA5, 8)
        assert writer.total_bits_written == 8
        assert writer.remaining_capacity_bits == 0

    def test_align_exceeds_capacity(self):
        writer = BitWriter(capacity_bits=6)
        writer.write_bits(0b101, 3)
        with pytest.raises(BitCapacityExceededError):
            writer.align_to_byte()

    def test_unlimited_capacity_writer(self):
        writer = BitWriter()
        for i in range(100):
            writer.write_bits(0xFF, 8)
        assert writer.total_bits_written == 800
        assert writer.remaining_capacity_bits is None


class TestWriterValueOutOfRange:
    def test_write_negative_value(self):
        writer = BitWriter()
        with pytest.raises(ValueOutOfRangeError) as excinfo:
            writer.write_bits(-1, 8)
        assert "non-negative" in str(excinfo.value)

    def test_write_value_exceeds_8_bits(self):
        writer = BitWriter()
        with pytest.raises(ValueOutOfRangeError) as excinfo:
            writer.write_bits(256, 8)
        assert "exceeds maximum 255" in str(excinfo.value)

    def test_write_value_exceeds_4_bits(self):
        writer = BitWriter()
        with pytest.raises(ValueOutOfRangeError):
            writer.write_bits(0x10, 4)

    def test_write_max_value_for_bits_ok(self):
        writer = BitWriter()
        writer.write_bits(0xF, 4)
        writer.write_bits(0xFF, 8)
        writer.write_bits(0xFFFF, 16)
        assert writer.total_bits_written == 28

    def test_write_zero_value_ok(self):
        writer = BitWriter()
        writer.write_bits(0, 16)
        assert writer.total_bits_written == 16
        assert writer.to_bytes() == bytes([0, 0])


class TestReaderInsufficientBits:
    def test_read_more_than_available(self):
        reader = BitReader(bytes([0xA5]))
        with pytest.raises(InsufficientBitsError) as excinfo:
            reader.read_bits(16)
        assert "only 8 bits remaining" in str(excinfo.value)

    def test_read_more_than_remaining_partial(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        reader.read_bits(12)
        assert reader.remaining_bits == 4
        with pytest.raises(InsufficientBitsError):
            reader.read_bits(5)

    def test_read_exact_remaining_ok(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        reader.read_bits(12)
        assert reader.read_bits(4) == 0xC

    def test_peek_more_than_available(self):
        reader = BitReader(bytes([0xA5]))
        with pytest.raises(InsufficientBitsError):
            reader.peek_bits(9)

    def test_peek_more_than_remaining_partial(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        reader.read_bits(10)
        assert reader.remaining_bits == 6
        with pytest.raises(InsufficientBitsError):
            reader.peek_bits(7)

    def test_peek_exact_remaining_ok(self):
        reader = BitReader(bytes([0xA5, 0x3C]))
        reader.read_bits(10)
        assert reader.peek_bits(6) == 0x3C

    def test_read_from_empty_stream(self):
        reader = BitReader(b"")
        with pytest.raises(InsufficientBitsError):
            reader.read_bits(1)

    def test_peek_from_empty_stream(self):
        reader = BitReader(b"")
        with pytest.raises(InsufficientBitsError):
            reader.peek_bits(1)

    def test_read_after_exhausting(self):
        reader = BitReader(bytes([0xA5]))
        reader.read_bits(8)
        with pytest.raises(InsufficientBitsError):
            reader.read_bits(1)

    def test_align_reader_insufficient_bits(self):
        data = bytes([0b10100000])
        reader = BitReader(data, total_bits=3)
        assert reader.total_bits_available == 3
        assert reader.remaining_bits == 3
        reader.read_bits(3)
        assert reader.bit_offset == 3
        assert reader.remaining_bits == 0
        with pytest.raises(InsufficientBitsError) as excinfo:
            reader.align_to_byte()
        assert "Cannot align" in str(excinfo.value)
        assert "need 5 bits but only 0 remaining" in str(excinfo.value)


class TestWriterAlignValidation:
    def test_align_invalid_fill_bit(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        with pytest.raises(ValueError):
            writer.align_to_byte(fill_bit=2)

    def test_align_invalid_negative_fill_bit(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        with pytest.raises(ValueError):
            writer.align_to_byte(fill_bit=-1)


class TestBitReaderTotalBitsValidation:
    def test_total_bits_negative_raises(self):
        with pytest.raises(ValueError) as excinfo:
            BitReader(bytes([0x00]), total_bits=-1)
        assert "non-negative" in str(excinfo.value)

    def test_total_bits_exceeds_data_length_raises(self):
        with pytest.raises(ValueError) as excinfo:
            BitReader(bytes([0x00, 0x00]), total_bits=17)
        assert "exceeds maximum possible" in str(excinfo.value)
        assert "16" in str(excinfo.value)

    def test_total_bits_at_max_boundary_ok(self):
        reader = BitReader(bytes([0xA5]), total_bits=8)
        assert reader.total_bits_available == 8
        assert reader.read_bits(8) == 0xA5

    def test_total_bits_peek_respects_limit(self):
        reader = BitReader(bytes([0b10110000, 0xFF]), total_bits=4)
        assert reader.peek_bits(4) == 0b1011
        with pytest.raises(InsufficientBitsError):
            reader.peek_bits(5)

    def test_total_bits_read_exceeding_limit_raises(self):
        reader = BitReader(bytes([0xA5, 0x3C]), total_bits=12)
        reader.read_bits(10)
        assert reader.remaining_bits == 2
        with pytest.raises(InsufficientBitsError):
            reader.read_bits(3)


class TestReaderPositionProtection:
    def test_read_position_does_not_go_backward(self):
        reader = BitReader(bytes([0xA5, 0x3C, 0x7E]))
        reader.read_bits(8)
        pos_after_8 = reader.total_bits_read
        reader.read_bits(8)
        assert reader.total_bits_read > pos_after_8

    def test_reset_reader_restores_position(self):
        reader = BitReader(bytes([0xA5, 0x3C, 0x7E]))
        reader.read_bits(16)
        assert reader.total_bits_read == 16
        reader.reset()
        assert reader.total_bits_read == 0
        assert reader.byte_position == 0
        assert reader.bit_offset == 0
        assert reader.read_bits(16) == 0xA53C

    def test_peek_does_not_affect_future_reads(self):
        writer = BitWriter()
        writer.write_bits(0xA5, 8)
        writer.write_bits(0x3C, 8)
        data = writer.to_bytes()
        reader = BitReader(data)

        first_peek = reader.peek_bits(4)
        second_peek = reader.peek_bits(8)
        actual_read = reader.read_bits(8)

        assert first_peek == 0xA
        assert second_peek == 0xA5
        assert actual_read == 0xA5
