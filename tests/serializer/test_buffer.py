import pytest

from solocoder_py.serializer import Buffer, BufferOverflowError
from .conftest import make_buffer


class TestBufferBasic:
    def test_empty_buffer(self):
        buf = make_buffer()
        assert buf.read_position == 0
        assert buf.write_position == 0
        assert buf.remaining == 0
        assert buf.data == b""

    def test_initial_data(self):
        buf = make_buffer(b"\x01\x02\x03")
        assert buf.write_position == 3
        assert buf.remaining == 3
        assert buf.data == b"\x01\x02\x03"

    def test_write_single_byte(self):
        buf = make_buffer()
        buf.write_byte(0xAB)
        assert buf.write_position == 1
        assert buf.data == b"\xab"

    def test_write_invalid_byte_raises(self):
        buf = make_buffer()
        with pytest.raises(ValueError):
            buf.write_byte(256)
        with pytest.raises(ValueError):
            buf.write_byte(-1)

    def test_write_multiple_bytes(self):
        buf = make_buffer()
        buf.write_bytes(b"\x01\x02\x03")
        buf.write_byte(0x04)
        assert buf.data == b"\x01\x02\x03\x04"

    def test_read_byte(self):
        buf = make_buffer(b"\x0a\x0b")
        assert buf.read_byte() == 0x0A
        assert buf.read_position == 1
        assert buf.read_byte() == 0x0B
        assert buf.read_position == 2

    def test_read_beyond_end_raises(self):
        buf = make_buffer(b"\x01")
        buf.read_byte()
        with pytest.raises(BufferOverflowError):
            buf.read_byte()

    def test_read_bytes(self):
        buf = make_buffer(b"\x01\x02\x03\x04")
        assert buf.read_bytes(2) == b"\x01\x02"
        assert buf.read_position == 2
        assert buf.read_bytes(2) == b"\x03\x04"

    def test_read_bytes_negative_count_raises(self):
        buf = make_buffer(b"\x01")
        with pytest.raises(ValueError):
            buf.read_bytes(-1)

    def test_read_bytes_too_many_raises(self):
        buf = make_buffer(b"\x01\x02")
        with pytest.raises(BufferOverflowError):
            buf.read_bytes(5)

    def test_peek_byte(self):
        buf = make_buffer(b"\x10\x20\x30")
        assert buf.peek_byte(0) == 0x10
        assert buf.peek_byte(1) == 0x20
        assert buf.read_position == 0

    def test_peek_beyond_end_raises(self):
        buf = make_buffer(b"\x01")
        with pytest.raises(BufferOverflowError):
            buf.peek_byte(10)

    def test_skip(self):
        buf = make_buffer(b"\x01\x02\x03\x04\x05")
        buf.skip(2)
        assert buf.read_position == 2
        assert buf.read_byte() == 0x03

    def test_skip_negative_raises(self):
        buf = make_buffer(b"\x01")
        with pytest.raises(ValueError):
            buf.skip(-1)

    def test_skip_beyond_end_raises(self):
        buf = make_buffer(b"\x01\x02")
        with pytest.raises(BufferOverflowError):
            buf.skip(10)

    def test_reset_read(self):
        buf = make_buffer(b"\x01\x02\x03")
        buf.read_bytes(3)
        assert buf.remaining == 0
        buf.reset_read()
        assert buf.remaining == 3
        assert buf.read_position == 0

    def test_clear(self):
        buf = make_buffer(b"\x01\x02\x03")
        buf.read_byte()
        buf.clear()
        assert buf.data == b""
        assert buf.read_position == 0
        assert buf.write_position == 0
