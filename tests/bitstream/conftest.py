import pytest

from solocoder_py.bitstream import BitReader, BitWriter


@pytest.fixture
def empty_writer():
    return BitWriter()


@pytest.fixture
def empty_reader():
    return BitReader(b"")


@pytest.fixture
def sample_data_8_bits():
    writer = BitWriter()
    writer.write_bits(0b10101010, 8)
    data = writer.to_bytes()
    return data, BitReader(data)


@pytest.fixture
def sample_data_mixed():
    writer = BitWriter()
    writer.write_bits(0b101, 3)
    writer.write_bits(0b110, 3)
    writer.write_bits(0b1111, 4)
    writer.write_bits(0b0010, 4)
    data = writer.to_bytes()
    return data, BitReader(data)
