import pytest

from solocoder_py.framecodec import CrcCalculator
from solocoder_py.framecodec.exceptions import FrameConfigError


class TestCrcCalculator:
    def test_crc16_empty_bytes(self):
        crc = CrcCalculator.calculate(b"", 2)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_simple_data(self):
        data = b"123456789"
        crc = CrcCalculator.calculate(data, 2)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_crc16_consistency(self):
        data = b"Hello, World!"
        crc1 = CrcCalculator.calculate(data, 2)
        crc2 = CrcCalculator.calculate(data, 2)
        assert crc1 == crc2

    def test_crc16_different_data_different_crc(self):
        data1 = b"Hello"
        data2 = b"World"
        crc1 = CrcCalculator.calculate(data1, 2)
        crc2 = CrcCalculator.calculate(data2, 2)
        assert crc1 != crc2

    def test_crc32_empty_bytes(self):
        crc = CrcCalculator.calculate(b"", 4)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFFFFFF

    def test_crc32_simple_data(self):
        data = b"123456789"
        crc = CrcCalculator.calculate(data, 4)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFFFFFF

    def test_crc32_consistency(self):
        data = b"Hello, World!"
        crc1 = CrcCalculator.calculate(data, 4)
        crc2 = CrcCalculator.calculate(data, 4)
        assert crc1 == crc2

    def test_crc32_different_data_different_crc(self):
        data1 = b"Hello"
        data2 = b"World"
        crc1 = CrcCalculator.calculate(data1, 4)
        crc2 = CrcCalculator.calculate(data2, 4)
        assert crc1 != crc2

    def test_unsupported_crc_size_raises(self):
        with pytest.raises(FrameConfigError, match="Unsupported CRC size"):
            CrcCalculator.calculate(b"test", 3)

    def test_verify_correct_crc16(self):
        data = b"test data"
        crc = CrcCalculator.calculate(data, 2)
        assert CrcCalculator.verify(data, crc, 2) is True

    def test_verify_wrong_crc16(self):
        data = b"test data"
        assert CrcCalculator.verify(data, 0xDEAD, 2) is False

    def test_verify_correct_crc32(self):
        data = b"test data"
        crc = CrcCalculator.calculate(data, 4)
        assert CrcCalculator.verify(data, crc, 4) is True

    def test_verify_wrong_crc32(self):
        data = b"test data"
        assert CrcCalculator.verify(data, 0xDEADBEEF, 4) is False

    def test_max_value_crc16(self):
        assert CrcCalculator.max_value(2) == 0xFFFF

    def test_max_value_crc32(self):
        assert CrcCalculator.max_value(4) == 0xFFFFFFFF

    def test_max_value_unsupported_size(self):
        with pytest.raises(FrameConfigError):
            CrcCalculator.max_value(3)

    def test_crc16_table_caching(self):
        table1 = CrcCalculator._build_crc16_table()
        table2 = CrcCalculator._build_crc16_table()
        assert table1 is table2

    def test_crc32_table_caching(self):
        table1 = CrcCalculator._build_crc32_table()
        table2 = CrcCalculator._build_crc32_table()
        assert table1 is table2
